#!/usr/bin/env python3
"""Exercise Bash routing and real subprocess cwd/argv without starting a model."""
import errno
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
                     'project_git.sh', 'task_delivery.py', 'check_git_content.py', 'project_runtime.py']:
            shutil.copyfile(SOURCE / 'analysis/scripts' / name, scripts / name)
        shutil.copytree(SOURCE / '.githooks', root / '.githooks')
        shutil.copyfile(SOURCE / '.gitignore', root / '.gitignore')
        (root / '.codex').mkdir()
        (root / '.codex/config.toml').write_text('args = ["' + str(root) + '/analysis/vendor/oh-my-codex/dist/mcp/state-server.js"]\n')
        (root / '.codex/hooks.json').write_text(json.dumps({'command': 'node ' + str(root) +
                                                        '/analysis/vendor/oh-my-codex/dist/scripts/codex-native-hook.js',
                                                        'state': str(root / '.omx/state')}))
        git(root, 'add', '.')
        git(root, 'commit', '-m', 'Fixture baseline')
        (root / '.git').rename(root / '.project-git')
        (root / 'analysis/vendor/oh-my-codex/dist').mkdir(parents=True)
        (root / 'analysis/vendor/oh-my-codex/node_modules').mkdir()
        (root / 'analysis/vendor/oh-my-codex/dist/cli').mkdir()
        (root / 'analysis/vendor/oh-my-codex/dist/cli/omx.js').write_text(
            "process.stdout.write(JSON.stringify({cwd:process.cwd(),entry:process.argv[1]}));\n")
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
            before_resume = coordinator.read_state(root)
            for args in [['resume'], ['resume', '--last'], ['fork', 'native-thread'],
                         ['--model', 'fixture', 'resume', '--last'], ['exec', 'resume', '--last'],
                         ['-C', str(outside), 'resume', '--last'],
                         ['--sandbox', 'read-only', 'resume', '--last'],
                         ['exec', '--thread-source', 'cli', 'resume', '--last']]:
                assert entry.route(args, str(executable), root) == 0
                assert json.loads(log.read_text()) == {'cwd': str(root), 'argv': args}
            assert coordinator.read_state(root) == before_resume
            checks.append({'name': 'Native resume/fork including valued global options retain exact argv/cwd without registration', 'returncode': 0})
            assert entry.route(['--', '--help'], str(executable), root) == 0
            literal_help = json.loads(log.read_text())
            assert literal_help['cwd'] != str(root) and literal_help['argv'][-2:] == ['--', '--help']
            launch_args = ['--model', 'fixture', '--config', 'model_reasoning_effort="high"', 'literal prompt']
            with patch.object(Path, 'symlink_to', side_effect=OSError(errno.ENOSYS, 'Function not implemented')):
                assert entry.route(launch_args, str(executable), root) == 0
            first = json.loads(log.read_text())
            first_workspace = Path(first['cwd'])
            assert str(root / 'analysis/vendor/oh-my-codex/dist') in (first_workspace / '.codex/config.toml').read_text()
            hooks = json.loads((first_workspace / '.codex/hooks.json').read_text())
            assert str(root / 'analysis/vendor/oh-my-codex/dist') in hooks['command']
            assert hooks['state'] == str(first_workspace / '.omx/state')
            assert not (first_workspace / 'analysis/vendor/oh-my-codex/dist').exists()
            checks.append({'name': 'ENOSYS symlink filesystem still launches with canonical static code and local state', 'returncode': 0})
            runtime = subprocess.run(['python3', str(first_workspace / 'analysis/scripts/project_runtime.py'),
                                      'omx', '--help'], cwd=first_workspace, env=env,
                                     capture_output=True, text=True, timeout=30)
            assert runtime.returncode == 0, runtime.stdout + runtime.stderr
            assert json.loads(runtime.stdout) == {'cwd': str(first_workspace),
                                                  'entry': str(root / 'analysis/vendor/oh-my-codex/dist/cli/omx.js')}
            checks.append({'name': 'Employee runtime launches canonical shared OMX entry with employee cwd and no dist link', 'returncode': 0})
            assert Path(first['cwd']) != root and first['argv'][-len(launch_args):] == launch_args
            assert first['argv'][:4] == ['-C', first['cwd'], '--sandbox', 'workspace-write']
            assert entry.route([], str(executable), root) == 0
            second = json.loads(log.read_text())
            assert first['cwd'] != second['cwd']
            checks.append({'name': 'Two normal codex launches create distinct physical workspaces and preserve options', 'returncode': 0})
            with patch.object(coordinator, 'employee_config', side_effect=OSError(errno.ENOSYS, 'Old startup failure')):
                try:
                    coordinator.create(root, 'interrupted', 'interrupted', ['analysis/'])
                except OSError as error:
                    assert error.errno == errno.ENOSYS
                else:
                    raise AssertionError('The interrupted-create fixture did not fail')
            old_base = coordinator.read_state(root)['employees']['interrupted']['base']
            (root / 'analysis/advanced.md').write_text('root advanced after interruption\n')
            coordinator.git(root, 'add', '--', 'analysis/advanced.md')
            coordinator.git(root, 'commit', '-m', 'Advance control fixture')
            assert coordinator.text(root, 'rev-parse', 'HEAD') != old_base
            assert entry.route(['--chx-employee', 'interrupted'], str(executable), root) == 0
            resumed = coordinator.read_state(root)['employees']['interrupted']
            assert resumed['status'] == 'active' and resumed['base'] == old_base
            assert coordinator.text(Path(resumed['workspace']), 'rev-parse', 'HEAD') == old_base
            checks.append({'name': 'Failed creating employee retries in place and preserves its original base after root advancement', 'returncode': 0})
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
                         ['-punknown'], ['--chx-employee', 'unknown', 'resume', '--last'],
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
            checks.append({'name': 'Managed write escapes, remote/profile overrides and unknown explicit employee resume are rejected', 'returncode': 0})
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
    print('PASS:', len(checks), 'real-process Bash/CLI routing checks, without model invocation')


if __name__ == '__main__':
    main()
