#!/usr/bin/env python3
"""Check current session isolation boundaries in a disposable local repository."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'analysis/scripts'))
import project_sync
import task_delivery


def main():
    checks = []
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null',
               GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
    with tempfile.TemporaryDirectory(prefix='chx-session-audit-') as temporary:
        root = Path(temporary)

        def git(*args, check=True):
            result = subprocess.run(['git', '-C', str(root), '-c', 'core.hooksPath=/dev/null', *args],
                                    env=env, capture_output=True, timeout=15)
            if check:
                result.check_returncode()
            return result

        git('init', '--quiet')
        git('symbolic-ref', 'HEAD', 'refs/heads/main')
        git('config', 'user.name', 'Concurrency fixture')
        git('config', 'user.email', 'fixture@example.invalid')
        (root / 'analysis').mkdir()
        (root / 'analysis/baseline.md').write_text('baseline\n')
        git('add', '--', 'analysis/baseline.md')
        git('commit', '--quiet', '-m', 'Create isolated baseline')
        git('remote', 'add', 'origin', str(root / 'unused-remote.git'))
        git('update-ref', 'refs/remotes/origin/main', 'HEAD')
        git('config', 'branch.main.remote', 'origin')
        git('config', 'branch.main.merge', 'refs/heads/main')
        with patch.object(project_sync, 'ROOT', root), patch.object(project_sync, 'git', git), \
                patch.object(task_delivery, 'ROOT', root), \
                patch.object(task_delivery, 'PENDING', root / '.omx/delivery/pending.json'), \
                patch.object(task_delivery, 'git', lambda *args: git(*args).stdout.decode().strip()):
            assert project_sync.stop_status({'hook_event_name': 'Stop', 'cwd': str(root)}) == {}
            for session in ['session_a', 'session_b']:
                directory = root / 'analysis' / session
                directory.mkdir()
                (directory / 'owned.md').write_text(session + '\n')
                (directory / 'evidence.json').write_text(json.dumps({
                    'status': 'passed', 'checks': [{'name': 'isolated fixture', 'returncode': 0}]}))
            candidates = project_sync.candidates()
            assert 'analysis/session_a/owned.md' in candidates
            assert 'analysis/session_b/owned.md' in candidates
            checks.append({'name': 'Production candidates collects both sessions in a shared worktree',
                           'returncode': 0, 'observed_candidates': candidates})
            results = [project_sync.stop_status({'hook_event_name': 'Stop', 'cwd': str(root),
                                                'session_id': session})
                       for session in ['session_a', 'session_b']]
            assert results[0] == results[1] and results[0]['decision'] == 'block'
            checks.append({'name': 'Production Stop decision does not distinguish session_id',
                           'returncode': 0, 'decision': 'block for both sessions'})
            assert project_sync.stop_status({'hook_event_name': 'Stop', 'cwd': str(root),
                                             'stop_hook_active': True}) == {}
            checks.append({'name': 'Production Stop suppresses a repeated active hook invocation',
                           'returncode': 0})
            git('add', '--', 'analysis')
            with contextlib.redirect_stdout(io.StringIO()):
                task_delivery.prepare('session_a', 'analysis/session_a/evidence.json', 'fixture A')
                before = json.loads(task_delivery.PENDING.read_text())
                task_delivery.prepare('session_b', 'analysis/session_b/evidence.json', 'fixture B')
                after = json.loads(task_delivery.PENDING.read_text())
            assert before['task'] == 'session_a' and after['task'] == 'session_b'
            checks.append({'name': 'Second production prepare overwrites the shared pending receipt',
                           'returncode': 0, 'before': before['task'], 'after': after['task']})
    sources = ['analysis/scripts/project_sync.py', 'analysis/scripts/task_delivery.py',
               'analysis/scripts/project_git.sh', '.codex/hooks.json']
    report = {'status': 'passed', 'checks': checks,
              'command': 'python3 analysis/session_concurrency/audit.py',
              'method': 'Actual production functions with only repository/Git adapters redirected to /tmp',
              'limit': 'Passing checks confirm isolation gaps; production synchronization was not executed or fixed',
              'sources_sha256': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                 for name in sources}}
    output = Path(__file__).resolve().parent / 'reports/verification.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('PASS: four isolated checks confirm current session coordination boundaries')


if __name__ == '__main__':
    main()
