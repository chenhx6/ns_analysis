#!/usr/bin/env python3
"""Record CLI entry regressions and refresh the actual changed-launcher evidence."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'reports'


def run(command, name):
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=300)
    return {'name': name, 'command': command, 'returncode': result.returncode,
            'output': (result.stdout + result.stderr)[-22000:]}


def main():
    checks = []
    paths = ['analysis/scripts/codex_entry.py', 'analysis/scripts/codex_shell.sh',
             'analysis/scripts/session_coordinator.py', 'analysis/wsl_codex_entry/test_entry.py',
             'analysis/wsl_codex_entry/verify.py']
    before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths}
    checks.append(run(['python3', 'analysis/wsl_codex_entry/test_entry.py'], 'Real Bash/CLI subprocess routing'))
    checks.append(run(['python3', 'analysis/session_coordination/test_coordination.py'],
                      'Full 18-group process/Git/bubblewrap regression with the changed launcher'))
    if all(check['returncode'] == 0 for check in checks):
        path = ROOT / 'analysis/session_coordination/reports/concurrency_checks.json'
        original = json.loads(path.read_text())
        record = dict(checks[-1], groups=original['checks'][0]['groups'],
                      host_boundary='Real approved namespace execution; restricted outer tools may block it')
        actual = {'status': 'passed', 'checks': [record],
                  'sources_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                     for name in original['sources_sha256']}}
        path.write_text(json.dumps(actual, ensure_ascii=False, indent=2) + '\n')
        checks.append(run(['python3', 'analysis/session_coordination/verify.py'],
                          'Existing delivery regression, source fingerprints and installed lifecycle integration'))
    after = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in paths}
    if before != after:
        checks.append({'name': 'Tested sources must remain unchanged throughout validation', 'returncode': 1})
    report = {'status': 'passed' if all(check['returncode'] == 0 for check in checks) else 'failed',
              'checks': checks,
              'sources_sha256': after,
              'limits': ['Fake CLI verifies actual cwd/argv dispatch without model login or paid invocation.',
                         'Employee boundary uses original CLI workspace-write; shell functions do not grant permissions.',
                         'Personal Bash integration is installed and checked separately with real host permission.']}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'checks': [(check['name'], check['returncode']) for check in checks]},
                     ensure_ascii=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
