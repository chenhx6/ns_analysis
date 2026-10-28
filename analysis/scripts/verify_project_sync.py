#!/usr/bin/env python3
"""Collect actual current delivery checks without overwriting historical baselines."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT/'analysis/project_maintenance/reports/automatic_git_sync_verification.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = []
    commands = [
        ('Isolated actual commit/push/tag and Stop/security regression', ['python3','analysis/scripts/test_project_sync.py']),
        ('Run log parsing and boundary regression', ['python3','run_log/test_run_log.py']),
        ('Independent CSV versus current raw logs', ['python3','run_log/test_run_log.py','--csv','run_log/runs.csv']),
        ('Diff whitespace validation', ['bash','analysis/scripts/project_git.sh','diff','--check']),
    ]
    for name, argv in commands:
        result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=60)
        checks.append({'name':name, 'command':argv, 'returncode':result.returncode,
                       'output':(result.stdout+result.stderr)[-12000:]})
    try:
        for path in (ROOT/'analysis/scripts').glob('*.py'):
            compile(path.read_text(), str(path), 'exec')
        lock = json.loads((ROOT/'analysis/third_party/sources.lock.json').read_text())
        for item in lock['adaptations']:
            for relative, digest in item.get('files_sha256', {'SKILL.md':item['entry_sha256']}).items():
                for base in [ROOT/item['directory'], ROOT/'.codex/skills'/Path(item['directory']).name]:
                    assert sha(base/relative) == digest, str(base/relative)
        assert not (ROOT/'analysis/code').exists()
        hook_config = json.loads((ROOT/'.codex/hooks.json').read_text())
        hook = next(item['command'] for group in hook_config['hooks']['Stop'] for item in group['hooks']
                    if 'session_coordinator.py' in item['command'])
        response = subprocess.run(shlex.split(hook), cwd=ROOT, input=json.dumps({'hook_event_name':'Stop','cwd':str(ROOT),'session_id':'verification-unregistered'}),
                                  text=True, capture_output=True, timeout=30)
        assert response.returncode == 0 and json.loads(response.stdout) == {}
        qa = json.loads((ROOT/'run_log/reports/figure_qa.json').read_text())
        for item in qa['reports']:
            # Historical audit paths remain evidence of the original execution.
            assert sha(ROOT/'run_log/figures'/Path(item['svg']).name) == item['sha256']
            assert item['auto_result'] == 'pass' and item['visual_review'] == 'passed'
        checks.append({'name':'Program syntax, skill mirrors/fingerprints, scripts-only layout, actual Stop CLI and unchanged reviewed SVGs', 'returncode':0})
    except Exception as exc:
        checks.append({'name':'Current delivery integration checks', 'returncode':1, 'output':str(exc)})
    baseline = json.loads((ROOT/'analysis/project_maintenance/reports/layout_baseline.json').read_text())
    record = ROOT/'analysis/00_experiment_log/record_analysis.md' if (ROOT/'analysis/00_experiment_log/record_analysis.md').exists() else ROOT/'analysis/experiment_log/record_analysis.md'
    output = {'status':'passed' if all(item['returncode']==0 for item in checks) else 'failed', 'checks':checks,
              'current_experiment_record_sha256':sha(record),
              'experiment_record_updated_after_migration':record.read_text()!=baseline['experiment_text'].replace('./analysis_figure/record_analysis/','./figures/'),
              'notes':['User additions to experiment record preserved; original migration baseline remains historical evidence.',
                       'Hook command tested directly; actual native hook loading/trust remains host responsibility.',
                       'Formal remote delivery is checked separately by project_sync.py.']}
    REPORT.write_text(json.dumps(output, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status':output['status'], 'checks':[(item['name'],item['returncode']) for item in checks], 'report':str(REPORT)},ensure_ascii=False))
    return 0 if output['status']=='passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
