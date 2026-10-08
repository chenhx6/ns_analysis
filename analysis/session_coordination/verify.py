#!/usr/bin/env python3
"""Verify final coordination integration and collect the actual completed regressions."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REPORTS = Path(__file__).resolve().parent / 'reports'
sys.path.insert(0, str(ROOT / 'analysis/scripts'))
import install_project_sync


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    checks = []
    regression = json.loads((REPORTS / 'concurrency_checks.json').read_text())
    assert regression['status'] == 'passed'
    assert regression['checks'] and all(item['returncode'] == 0 for item in regression['checks'])
    for name, digest in regression['sources_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed tested source: ' + name
    checks.extend(regression['checks'])
    # Existing delivery tests exercise the final trusted wrapper/policy/tag code as well.
    argv = ['python3', 'analysis/scripts/test_project_sync.py']
    result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True, timeout=120)
    checks.append({'name': 'Existing actual Git delivery, lock, explicit-file and trusted-hook regression',
                   'command': argv, 'returncode': result.returncode,
                   'output': (result.stdout + result.stderr)[-16000:]})
    assert result.returncode == 0, checks[-1]['output']
    for name in ['session_coordinator.py', 'project_sync.py', 'task_delivery.py',
                 'project_runtime.py', 'install_project_sync.py', 'verify_project_sync.py']:
        path = ROOT / 'analysis/scripts' / name
        compile(path.read_text(), str(path), 'exec')
    compile((ROOT / 'analysis/session_coordination/test_coordination.py').read_text(), 'test_coordination.py', 'exec')
    lock = json.loads((ROOT / 'analysis/third_party/sources.lock.json').read_text())
    adaptation = next(item for item in lock['adaptations'] if item['directory'] == '.agents/skills/task-tag')
    for base in ['.agents/skills/task-tag', '.codex/skills/task-tag']:
        path = ROOT / base / 'SKILL.md'
        assert path.read_text() == install_project_sync.SKILL
        assert sha(path) == adaptation['entry_sha256']
    config = json.loads((ROOT / '.codex/hooks.json').read_text())
    for event in ['SessionStart', 'Stop']:
        commands = [item['command'] for group in config['hooks'][event] for item in group['hooks']
                    if 'session_coordinator.py' in item['command']]
        assert len(commands) == 1, (event, commands)
        payload = {'hook_event_name': event, 'cwd': str(ROOT)}
        # No session ID: check the control response without allocating a production employee.
        response = subprocess.run(shlex.split(commands[0]), cwd=ROOT, input=json.dumps(payload),
                                  text=True, capture_output=True, timeout=30)
        assert response.returncode == 0, response.stderr
        output = json.loads(response.stdout)
        if event == 'Stop':
            assert output == {}
        else:
            assert 'additionalContext' in output['hookSpecificOutput']
    checks.append({'name': 'Source syntax, tested source fingerprints, installed skill mirrors and direct lifecycle hook JSON',
                   'returncode': 0, 'limit': 'Direct invocation does not prove host trust/loading or change a live session cwd'})
    sources = json.loads((REPORTS / 'sources.json').read_text())
    successful = [item for item in sources['sources'] if item.get('success')]
    assert len(successful) == 4 and all(item.get('final_url') for item in successful)
    checks.append({'name': 'Four actual official fetched pages retain final URLs and failed-search limits', 'returncode': 0})
    files = [name for name in regression['sources_sha256']]
    files += ['analysis/scripts/install_project_sync.py', '.codex/hooks.json',
              '.agents/skills/task-tag/SKILL.md', '.codex/skills/task-tag/SKILL.md']
    report = {'status': 'passed', 'checks': checks,
              'sources_sha256': {name: sha(ROOT / name) for name in sorted(set(files))},
              'limits': ['Managed isolated checkouts and approved candidate sandbox were tested; arbitrary root-editor writes are not blocked.',
                         'Native hook trust/loading and paid Codex model/login invocation were not claimed as tested.',
                         'Live notebook edits were excluded from this feature delivery; no experimental facts reviewed.']}
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'checks': [item['name'] for item in checks]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
