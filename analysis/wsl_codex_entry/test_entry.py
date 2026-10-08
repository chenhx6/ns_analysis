#!/usr/bin/env python3
"""Exercise Bash routing and real subprocess cwd/argv without starting a model."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE / 'analysis/scripts'))
import codex_entry as entry
import project_sync
import session_coordinator as coordinator


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), '-c', 'core.hooksPath=/dev/null', *args],
                                   stderr=subprocess.PIPE, text=True).strip()


def rejected(call):
    try:
        call()
    except (ValueError, RuntimeError):
        return
    raise AssertionError('An unsafe or invalid launch was accepted')


def main():
    checks = []
    with tempfile.TemporaryDirectory(prefix='chx-wsl-entry-') as temporary:
        base = Path(temporary)
        root, remote, outside = base / 'project', base / 'remote.git', base / 'outside'
        root.mkdir()
        outside.mkdir()
        git(base, 'init', '--bare', str(remote))
        git(base, 'init', str(root))
        git(root, 'symbolic-ref', 'HEAD', 'refs/heads/main')
        git(root, 'config', 'user.name', 'Entry fixture')
        git(root, 'config', 'user.email', 'fixture@example.invalid')
        git(root, 'remote', 'add', 'origin', str(remote))
        scripts = root / 'analysis/scripts'
        scripts.mkdir(parents=True)
        for name in ['codex_entry.py', 'codex_shell.sh', 'session_coordinator.py', 'project_sync.py',
                     'project_git.sh', 'task_delivery.py', 'check_git_content.py']:
            shutil.copyfile(SOURCE / 'analysis/scripts' / name, scripts / name)
        shutil.copytree(SOURCE / '.githooks', root / '.githooks')
        shutil.copyfile(SOURCE / '.gitignore', root / '.gitignore')
        git(root, 'add', '.')
        git(root, 'commit', '-m', 'Fixture baseline')
        (root / '.git').rename(root / '.project-git')
        executable = base / 'codex'
        log = base / 'cli.json'
        executable.write_text('#!' + sys.executable + '\nimport json,os,sys\n'
                              "from pathlib import Path\n"
                              "Path(os.environ['CHX_ENTRY_TEST_LOG']).write_text(json.dumps("
                              "{'cwd':os.getcwd(),'argv':sys.argv[1:]}))\n")
        executable.chmod(0o700)
        env = dict(os.environ, CHX_ENTRY_TEST_LOG=str(log))
        with patch.object(entry, 'ROOT', root), patch.object(project_sync, 'REMOTE', str(remote)), \
                patch.dict(os.environ, env):
            args = ['--model', 'fixture', 'prompt with spaces; $(never-executed)']
            assert entry.route(args, str(executable), outside) == 0
            assert json.loads(log.read_text()) == {'cwd': str(outside), 'argv': args}
            assert not coordinator.read_state(root)['employees']
            checks.append({'name': 'Other projects preserve exact argv and cwd without employee registration', 'returncode': 0})
            for args in [['--help'], ['--version'], ['login'], ['mcp', 'list']]:
                assert entry.route(args, str(executable), root) == 0
                assert json.loads(log.read_text())['argv'] == args
            assert not coordinator.read_state(root)['employees']
            checks.append({'name': 'Read-only help/version and explicit CLI management do not allocate workers', 'returncode': 0})
            assert entry.route(['--', '--help'], str(executable), root) == 0
            literal_help = json.loads(log.read_text())
            assert literal_help['cwd'] != str(root) and literal_help['argv'][-2:] == ['--', '--help']
            launch_args = ['--model', 'fixture', '--config', 'model_reasoning_effort="high"', 'literal prompt']
            assert entry.route(launch_args, str(executable), root) == 0
            first = json.loads(log.read_text())
            assert Path(first['cwd']) != root and first['argv'][-len(launch_args):] == launch_args
            assert first['argv'][:4] == ['-C', first['cwd'], '--sandbox', 'workspace-write']
            assert entry.route([], str(executable), root) == 0
            second = json.loads(log.read_text())
            assert first['cwd'] != second['cwd']
            checks.append({'name': 'Two normal codex launches create distinct physical workspaces and preserve options', 'returncode': 0})
            assert entry.route(['--chx-task', 'team', '--chx-employee', 'one', '--chx-scope', 'analysis/a/'],
                               str(executable), root) == 0
            one = coordinator.read_state(root)['employees']['one']
            assert entry.route(['--chx-task=team', '--chx-employee=two', '--chx-scope=analysis/b/'],
                               str(executable), root) == 0
            assert coordinator.read_state(root)['tasks']['team']['members'] == ['one', 'two']
            assert entry.route(['--chx-employee', 'one', 'resume', '--last'], str(executable), root) == 0
            assert json.loads(log.read_text())['cwd'] == one['workspace']
            assert entry.route(['--chx-employee', 'one', '--model', 'fixture', 'resume', '--last'],
                               str(executable), root) == 0
            assert entry.route(['--chx-employee', 'one', 'exec', 'resume', '--last'], str(executable), root) == 0
            assert entry.route(['--chx-employee', 'one', 'exec', '-o', 'analysis/answer.txt', 'prompt'],
                               str(executable), root) == 0
            assert entry.route([], str(executable), Path(one['workspace'])) == 0
            assert json.loads(log.read_text())['cwd'] == one['workspace']
            checks.append({'name': 'Explicit teammates and registered resume reuse the correct employee workspace', 'returncode': 0})
            for args in [['--sandbox', 'danger-full-access'], ['--add-dir', str(root)], ['--cd', str(root)],
                         ['-C' + str(root)], ['--yolo'], ['--remote', 'daemon'],
                         ['--dangerously-bypass-hook-trust'], ['--enable', 'feature'],
                         ['--config', 'sandbox_mode="danger-full-access"'], ['--profile', 'unknown'],
                         ['-punknown'], ['--model', 'fixture', 'resume', '--last'],
                         ['resume', '--last'], ['--chx-employee', 'unknown', 'resume', '--last'],
                         ['exec', 'resume', '--last'], ['e', 'fork', 'thread-id'],
                         ['exec', '--thread-source', 'cli', 'resume', '--last'],
                         ['--remote-auth-token-env', 'TOKEN', 'resume', '--last'],
                         ['--oss', '--local-provider', 'ollama', 'resume', '--last'],
                         ['exec', '-o', str(root / 'overwrite.md'), 'prompt'],
                         ['exec', '--output-last-message=../../overwrite.md', 'prompt'],
                         ['exec', '-o../../overwrite.md', 'prompt'],
                         ['exec', '-o', '.git/config', 'prompt'],
                         ['exec', '-o', '.', 'prompt'],
                         ['app'], ['app-server'], ['exec-server'], ['debug', 'app-server'],
                         ['cloud', 'exec', 'remote task'], ['cloud-tasks'], ['remote-control'], ['mcp-server']]:
                rejected(lambda args=args: entry.route(args, str(executable), root))
            (Path(one['workspace']) / 'analysis/outside').symlink_to(root, target_is_directory=True)
            rejected(lambda: entry.route(['--chx-employee', 'one', 'exec', '-o',
                                          'analysis/outside/overwrite.md', 'prompt'], str(executable), root))
            (Path(one['workspace']) / 'analysis/outside').unlink()
            checks.append({'name': 'Write-boundary escapes, remote/profile overrides and unbound resume are rejected', 'returncode': 0})
            with coordinator.lock(Path(one['workspace']) / '.omx/launch.lock'):
                rejected(lambda: entry.route(['--chx-employee', 'one'], str(executable), root))
            checks.append({'name': 'A second managed launcher cannot acquire an employee already running', 'returncode': 0})
            bashrc = base / '.bashrc'
            original = '# untouched setting\nexport CHX_FIXTURE_VALUE=1\n'
            bashrc.write_text(original)
            bashrc.chmod(0o600)
            entry.install_shell(bashrc)
            installed = bashrc.read_bytes()
            entry.install_shell(bashrc)
            assert bashrc.read_bytes() == installed and installed.startswith(original.encode())
            assert installed.count(entry.BEGIN.encode()) == 1
            assert bashrc.stat().st_mode & 0o777 == 0o600
            backup = json.loads((root / '.omx/coordination/shell-backup.json').read_text())
            assert Path(backup['backup']).stat().st_mode & 0o777 == 0o600
            assert Path(backup['private_directory']).stat().st_mode & 0o777 == 0o700
            assert Path(backup['backup']).read_text() == original
            subprocess.run(['bash', '-n', str(bashrc)], check=True)
            subprocess.run(['bash', '-n', str(scripts / 'codex_shell.sh')], check=True)
            checks.append({'name': 'Bash installation preserves existing bytes and is idempotent and syntactically valid', 'returncode': 0})
            # Run the actual source function in a new shell, resolving the fake binary through PATH.
            shell = subprocess.run(['bash', '--noprofile', '--norc', '-c',
                                    '. "$1"; codex --version', 'bash', str(scripts / 'codex_shell.sh')],
                                   cwd=root, env=dict(env, PATH=str(base) + ':' + env['PATH']),
                                   capture_output=True, text=True, timeout=30)
            assert shell.returncode == 0, shell.stdout + shell.stderr
            assert json.loads(log.read_text())['argv'] == ['--version']
            checks.append({'name': 'Sourced codex Bash function invokes the original executable without recursion', 'returncode': 0})
            bashrc.write_text('codex() { printf existing; }\n')
            rejected(lambda: entry.install_shell(bashrc))
            assert bashrc.read_text() == 'codex() { printf existing; }\n'
            compiled = compile((SOURCE / 'analysis/scripts/codex_entry.py').read_text(), 'codex_entry.py', 'exec')
            assert compiled
    paths = ['analysis/scripts/codex_entry.py', 'analysis/scripts/codex_shell.sh',
             'analysis/scripts/session_coordinator.py', 'analysis/wsl_codex_entry/test_entry.py']
    report = {'status': 'passed', 'checks': checks,
              'command': 'python3 analysis/wsl_codex_entry/test_entry.py',
              'sources_sha256': {name: hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() for name in paths},
              'limit': 'The fake CLI proves real process cwd/argv routing; native model calls/login were not executed'}
    output = Path(__file__).resolve().parent / 'reports/entry_checks.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('PASS: eight real-process Bash/CLI routing checks, without model invocation')


if __name__ == '__main__':
    main()
