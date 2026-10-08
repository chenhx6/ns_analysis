#!/usr/bin/env python3
"""Real process/clone/push regression checks; all mutable fixtures live in /tmp."""
import json
import multiprocessing as mp
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import traceback
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE / 'analysis/scripts'))
import project_sync
import session_coordinator as coordinator

CTX = mp.get_context('fork')
CHECK = 'python3 analysis/check.py'


def git(root, *args):
    command = ['git', '-C', str(root)]
    if (root / '.project-git/HEAD').is_file():
        command = ['git', '--git-dir=' + str(root / '.project-git'), '--work-tree=' + str(root)]
    return subprocess.check_output(command + list(args), text=True,
                                   stderr=subprocess.PIPE).strip()


def fixture(base):
    root, remote = base / 'project', base / 'remote.git'
    root.mkdir()
    git(base, 'init', '--bare', str(remote))
    git(base, 'init', str(root))
    git(root, 'symbolic-ref', 'HEAD', 'refs/heads/main')
    git(remote, 'symbolic-ref', 'HEAD', 'refs/heads/main')
    git(root, 'config', 'user.name', 'Coordination fixture')
    git(root, 'config', 'user.email', 'fixture@example.invalid')
    git(root, 'remote', 'add', 'origin', str(remote))
    scripts = root / 'analysis/scripts'
    scripts.mkdir(parents=True)
    for name in ('project_git.sh', 'project_sync.py', 'task_delivery.py',
                 'check_git_content.py', 'session_coordinator.py'):
        shutil.copyfile(SOURCE / 'analysis/scripts' / name, scripts / name)
    shutil.copytree(SOURCE / '.githooks', root / '.githooks')
    shutil.copyfile(SOURCE / '.gitignore', root / '.gitignore')
    (root / '.codex').mkdir()
    (root / '.codex/hooks.json').write_text(json.dumps({'fixture_project': str(root)}))
    (root / 'analysis/shared.md').write_text('baseline\n')
    (root / 'analysis/check.py').write_text(
        "from pathlib import Path\n"
        "assert Path('analysis/shared.md').read_text().endswith('\\n')\n")
    git(root, 'add', '.')
    git(root, '-c', 'core.hooksPath=/dev/null', 'commit', '-m', 'Fixture baseline')
    git(root, '-c', 'core.hooksPath=/dev/null', 'push', '-u', 'origin', 'main')
    (root / '.git').rename(root / '.project-git')
    return root, remote


def rejected(action, behavior):
    try:
        action()
    except (ValueError, RuntimeError):
        return
    raise AssertionError('Expected rejection: ' + behavior)


def child(gate, queue, function, arguments):
    gate.wait()
    try:
        queue.put(('ok', function(*arguments)))
    except BaseException:
        queue.put(('error', traceback.format_exc()))


def parallel(*calls):
    gate, queue = CTX.Event(), CTX.Queue()
    processes = [CTX.Process(target=child, args=(gate, queue, fn, args)) for fn, args in calls]
    for process in processes:
        process.start()
    gate.set()
    try:
        results = [queue.get(timeout=120) for _ in processes]
        for process in processes:
            process.join(timeout=5)
            assert process.exitcode == 0, 'Child process failed or hung'
        assert all(status == 'ok' for status, _ in results), results
        return [value for _, value in results]
    finally:
        for process in processes:
            if process.is_alive():
                process.kill()
                process.join()
        queue.close()


def employee(root, name, task=None, scopes=None):
    return Path(coordinator.create(root, task or name, name, scopes or ['analysis/'])['workspace'])


def freeze(workspace, task, path, content):
    (workspace / path).parent.mkdir(parents=True, exist_ok=True)
    (workspace / path).write_text(content)
    evidence = 'analysis/' + task + '-evidence.json'
    subprocess.run(CHECK.split(), cwd=workspace, check=True, capture_output=True)
    (workspace / evidence).write_text(json.dumps({
        'status': 'passed', 'checks': [{'name': CHECK, 'returncode': 0}]}))
    receipt = coordinator.submit(workspace, task, 'Deliver ' + task, evidence,
                                 'Verified fixture change', checks=[CHECK])
    assert receipt['status'] == 'awaiting_collection', receipt
    assert (workspace / '.omx/outbox' / (receipt['id'] + '.json')).is_file()
    return receipt


def submit(workspace, task, path, content):
    receipt = freeze(workspace, task, path, content)
    project = Path(json.loads((workspace / '.omx/employee.json').read_text())['project'])
    outcomes = coordinator.collect(project, receipt['employee'])
    assert outcomes, 'Collector ignored the employee outbox'
    matching = [item for item in outcomes if item.get('submission', item.get('id')) == receipt['id']]
    assert len(matching) == 1, outcomes
    return matching[0]


def submission_id(root, employee_name):
    matches = [(key, value) for key, value in coordinator.read_state(root)['submissions'].items()
               if value['employee'] == employee_name]
    assert len(matches) == 1, matches
    return matches[0][0]


def hold_lock(path, ready):
    with coordinator.lock(path):
        ready.set()
        CTX.Event().wait()


def check_isolation(root, remote):
    parallel((coordinator.create, (root, 'first', 'alice', ['analysis/'])),
             (coordinator.create, (root, 'second', 'bob', ['analysis/'])))
    state = coordinator.read_state(root)
    alice = Path(state['employees']['alice']['workspace'])
    bob = Path(state['employees']['bob']['workspace'])
    (alice / 'analysis/shared.md').write_text('alice\n')
    (bob / 'analysis/shared.md').write_text('bob\n')
    assert (alice / 'analysis/shared.md').read_text() == 'alice\n'
    assert (bob / 'analysis/shared.md').read_text() == 'bob\n'
    assert git(remote, 'show', 'main:analysis/shared.md') == 'baseline'
    assert git(root, 'status', '--porcelain') == ''
    assert employee(root, 'alice', 'first') == alice
    assert (alice / 'analysis/shared.md').read_text() == 'alice\n', 'Resume overwrote employee edits'
    assert coordinator.stop_status({'hook_event_name': 'Stop', 'cwd': str(alice)}, alice)['decision'] == 'block'


def check_claims(root, remote):
    employee(root, 'owner', 'team', ['analysis/shared.md'])
    rejected(lambda: employee(root, 'competitor', 'team', ['analysis/']), 'overlapping team claim')
    coordinator.release(root, 'owner', ['analysis/shared.md'])
    employee(root, 'successor', 'team', ['analysis/shared.md'])
    assert 'successor' in coordinator.read_state(root)['employees']


def check_parallel_delivery(root, remote):
    a, b = employee(root, 'alice'), employee(root, 'bob')
    notebook = root / 'analysis/experiment_log/record_analysis.md'
    notebook.parent.mkdir(parents=True, exist_ok=True)
    notebook.write_text('Live user note\n')
    parallel((submit, (a, 'alice', 'analysis/a.md', 'A\n')),
             (submit, (b, 'bob', 'analysis/b.md', 'B\n')))
    assert git(remote, 'show', 'main:analysis/a.md') == 'A'
    assert git(remote, 'show', 'main:analysis/b.md') == 'B'
    sid = submission_id(root, 'alice')
    before = git(remote, 'rev-parse', 'main')
    coordinator.integrate(root, sid)
    assert git(remote, 'rev-parse', 'main') == before, 'Repeated delivery created another commit'
    assert coordinator.stop_status({'hook_event_name': 'Stop', 'cwd': str(a)}, a) == {}
    (a / 'analysis/a.md').write_text('new local work\n')
    rejected(lambda: coordinator.update(a), 'update of dirty workspace')
    assert (a / 'analysis/a.md').read_text() == 'new local work\n'
    assert coordinator.stop_status({'hook_event_name': 'Stop', 'cwd': str(a)}, a)['decision'] == 'block'
    assert notebook.read_text() == 'Live user note\n'
    (a / 'analysis/a.md').write_text('A\n')
    coordinator.update(a)
    assert (a / 'analysis/b.md').read_text() == 'B\n'
    assert coordinator.stop_status({'hook_event_name': 'Stop', 'cwd': str(a)}, a) == {}, \
        'Clean delivered employee became blocked after update'


def check_conflict(root, remote):
    a, b, c = [employee(root, name) for name in ('alice', 'bob', 'carol')]
    submit(a, 'alice', 'analysis/shared.md', 'alice\n')
    try:
        submit(b, 'bob', 'analysis/shared.md', 'bob\n')
    except (RuntimeError, ValueError):
        pass
    assert git(remote, 'show', 'main:analysis/shared.md') == 'alice'
    assert (b / 'analysis/shared.md').read_text() == 'bob\n'
    record = coordinator.read_state(root)['submissions'][submission_id(root, 'bob')]
    assert record['status'] == 'conflict', record
    candidates = [p for p in (root / '.omx/coordination').rglob('shared.md')
                  if p != b / 'analysis/shared.md' and '<<<<<<<' in p.read_text()]
    assert candidates, 'Conflict working tree was not preserved'
    submit(c, 'carol', 'analysis/c.md', 'unrelated\n')
    assert git(remote, 'show', 'main:analysis/c.md') == 'unrelated'
    assert git(remote, 'show', 'main:analysis/shared.md') == 'alice'




def check_pushed_recovery(root, remote):
    workspace = employee(root, 'alice')
    with patch.object(coordinator, 'finish', side_effect=RuntimeError('injected receipt interruption')):
        result = submit(workspace, 'alice', 'analysis/a.md', 'A\n')
    assert result['status'] == 'needs_retry', result
    assert git(remote, 'show', 'main:analysis/a.md') == 'A'
    pushed = git(remote, 'rev-parse', 'main')
    restored = coordinator.integrate(root, submission_id(root, 'alice'))
    assert restored['status'] == 'pushed', restored
    assert git(remote, 'rev-parse', 'main') == pushed, 'Recovery duplicated a pushed commit'
    assert coordinator.stop_status({'hook_event_name': 'Stop', 'cwd': str(workspace)}, workspace) == {}


def check_merged_validation(root, remote):
    a, b = employee(root, 'alice'), employee(root, 'bob')
    checker = b / 'analysis/check.py'
    checker.write_text("from pathlib import Path\n"
                       "assert not Path('analysis/a.md').exists()\n")
    submit(a, 'alice', 'analysis/a.md', 'A\n')
    before = git(remote, 'rev-parse', 'main')
    result = submit(b, 'bob', 'analysis/b.md', 'B\n')
    assert result['status'] == 'needs_retry', result
    assert 'Validation failed' in result['error'], result
    assert git(remote, 'rev-parse', 'main') == before, 'Failing merged candidate was pushed'
    assert (b / 'analysis/b.md').read_text() == 'B\n'
    assert Path(result['recovery_workspace']).is_dir()


def check_boundaries(root, remote):
    for scope in ('../outside', '/tmp/outside', 'analysis/../README.md', 'analysis/credentials.json'):
        rejected(lambda scope=scope: employee(root, 'bad', scopes=[scope]), scope)
    workspace = employee(root, 'safe')
    original = git(remote, 'rev-parse', 'main')
    target = workspace / 'analysis/unsafe.md'
    target.symlink_to(root / 'analysis/shared.md')
    rejected(lambda: submit(workspace, 'safe', 'analysis/valid.md', 'valid\n'), 'symlink delivery')
    target.unlink()
    secret = workspace / 'analysis/credentials.json'
    secret.write_text('{"fixture": true}')
    git(workspace, 'add', '-f', str(secret))
    rejected(lambda: submit(workspace, 'safe', 'analysis/valid.md', 'valid\n'), 'credential delivery')
    git(workspace, 'reset', '--', str(secret))
    secret.unlink()
    with target.open('wb') as stream:
        stream.truncate(project_sync.MAX_BYTES + 1)
    rejected(lambda: submit(workspace, 'safe', 'analysis/valid.md', 'valid\n'), 'oversized delivery')
    assert git(remote, 'rev-parse', 'main') == original




def check_outbox_tampering(root, remote):
    workspace = employee(root, 'alice')
    (workspace / 'analysis/a.md').write_text('A\n')
    evidence = workspace / 'analysis/evidence.json'
    evidence.write_text(json.dumps({'status': 'passed', 'checks': [{'returncode': 0}]}))
    receipt = coordinator.submit(workspace, 'alice', 'Fixture', 'analysis/evidence.json',
                                 'Actual fixture validation', checks=[CHECK])
    path = workspace / '.omx/outbox' / (receipt['id'] + '.json')
    original = json.loads(path.read_text())
    original_head = git(remote, 'rev-parse', 'main')
    mutations = [dict(paths=[]), dict(base='0' * 40)]
    for change in mutations:
        forged = dict(original, **change)
        path.write_text(json.dumps(forged))
        rejected(lambda: coordinator.collect(root, 'alice'), 'forged outbox ' + str(list(change)))
        assert not coordinator.read_state(root)['submissions']
        assert git(remote, 'rev-parse', 'main') == original_head
    path.write_text(json.dumps(original))
    # The frozen Git diff, not the caller's path list, determines claim validation.
    with coordinator.transaction(root) as state:
        state['employees']['alice']['scopes'] = ['analysis/evidence.json']
    rejected(lambda: coordinator.collect(root, 'alice'), 'frozen edit outside current claim')
    assert git(remote, 'rev-parse', 'main') == original_head
    assert path.is_file(), 'Rejected outbox was discarded'


def check_employee_sandbox(root, remote):
    workspace, sibling = employee(root, 'alice'), employee(root, 'bob')
    targets = [str(root / 'analysis/shared.md'), str(sibling / 'analysis/shared.md')]
    checker = ("from pathlib import Path\n"
               "for target in " + repr(targets) + ":\n"
               "    try:\n        Path(target).write_text('intrusion')\n"
               "    except OSError:\n        pass\n"
               "    else:\n        raise AssertionError('Sandbox allowed foreign write')\n")
    (workspace / 'analysis/check.py').write_text(checker)
    script = ("import sys,json\nfrom pathlib import Path\n"
              "workspace=Path(sys.argv[1])\n"
              "sys.path.insert(0,str(workspace/'analysis/scripts'))\n"
              "import session_coordinator as c\n"
              + checker +
              "(workspace/'analysis/a.md').write_text('A\\n')\n"
              "(workspace/'analysis/evidence.json').write_text(json.dumps("
              "{'status':'passed','checks':[{'returncode':0}]}))\n"
              "result=c.submit(workspace,'alice','Fixture','analysis/evidence.json',"
              "'Sandbox validation',checks=['python3 analysis/check.py'])\n"
              "assert result['status']=='awaiting_collection', result\n")
    sandbox = shutil.which('bwrap')
    assert sandbox, 'Real sandbox test requires bubblewrap'
    command = [sandbox, '--ro-bind', '/', '/', '--bind', str(workspace), str(workspace),
               '--proc', '/proc', '--dev', '/dev', '--unshare-net', '--die-with-parent',
               '--chdir', str(workspace), '--', sys.executable, '-c', script, str(workspace)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / 'analysis/shared.md').read_text() == 'baseline\n'
    assert (sibling / 'analysis/shared.md').read_text() == 'baseline\n'
    receipts = coordinator.collect(root, 'alice')
    assert receipts[-1]['status'] == 'pushed', receipts
    assert git(remote, 'show', 'main:analysis/a.md') == 'A'
    assert (root / 'analysis/shared.md').read_text() == 'baseline\n'
    assert (sibling / 'analysis/shared.md').read_text() == 'baseline\n'



def check_session_registration(root, remote):
    with patch.object(coordinator, 'ROOT', root):
        payloads = [{'hook_event_name': 'SessionStart', 'cwd': str(root), 'session_id': name}
                    for name in ('native-session-a', 'native-session-b')]
        parallel(*[(coordinator.hook, (payload,)) for payload in payloads])
        state = coordinator.read_state(root)
        ids = [state['sessions'][payload['session_id']] for payload in payloads]
        assert ids[0] != ids[1]
        workspaces = [Path(state['employees'][name]['workspace']) for name in ids]
        assert workspaces[0] != workspaces[1]
        before = (workspaces[0] / '.codex/hooks.json').read_bytes()
        coordinator.hook(payloads[0])
        assert (workspaces[0] / '.codex/hooks.json').read_bytes() == before
        assert len(coordinator.read_state(root)['employees']) == 2
        assert json.loads(before)['fixture_project'] == str(workspaces[0])
        coordinator.assign(root, ids[0], 'team', ['analysis/first/'])
        rejected(lambda: coordinator.assign(root, ids[1], 'team', ['analysis/first/']),
                 'assigning overlapping shared task scopes')
        coordinator.assign(root, ids[1], 'team', ['analysis/second/'])
        state = coordinator.read_state(root)
        assert set(state['tasks']['team']['members']) == set(ids)
        notebook = root / 'analysis/experiment_log/record_analysis.md'
        notebook.parent.mkdir(parents=True)
        notebook.write_text('Live note\n')
        for payload in payloads:
            assert coordinator.hook(dict(payload, hook_event_name='Stop')) == {}
        (workspaces[0] / 'analysis/first').mkdir()
        (workspaces[0] / 'analysis/first/edit.md').write_text('work\n')
        assert coordinator.hook(dict(payloads[0], hook_event_name='Stop'))['decision'] == 'block'
        assert coordinator.hook(dict(payloads[1], hook_event_name='Stop')) == {}
        assert notebook.read_text() == 'Live note\n'


def check_conflict_resolution(root, remote):
    a, b = employee(root, 'alice'), employee(root, 'bob')
    submit(a, 'alice', 'analysis/shared.md', 'alice\n')
    original = submit(b, 'bob', 'analysis/shared.md', 'bob\n')
    assert original['status'] == 'conflict', original
    frozen = copy_json(original)
    recovery = Path(original['recovery_workspace'])
    before = (recovery / 'analysis/shared.md').read_bytes()
    result = coordinator.resolve(root, 'bob')
    assert result['status'] == 'resolve_in_employee_workspace', result
    assert 'analysis/shared.md' in result['conflict_paths']
    (b / 'analysis/shared.md').write_text('alice and bob\n')
    git(b, 'add', '--', 'analysis/shared.md')
    subprocess.run(['bash', str(b / 'analysis/scripts/project_git.sh'),
                    'commit', '-m', 'Resolve both employee changes'], cwd=b, check=True,
                   capture_output=True)
    delivered = submit(b, 'bob', 'analysis/shared.md', 'alice and bob\n')
    assert delivered['status'] == 'pushed', delivered
    assert git(remote, 'show', 'main:analysis/shared.md') == 'alice and bob'
    assert coordinator.read_state(root)['submissions'][original['id']] == frozen
    assert (recovery / 'analysis/shared.md').read_bytes() == before
    assert coordinator.stop_status({'hook_event_name': 'Stop', 'cwd': str(b)}, b) == {}


def copy_json(value):
    return json.loads(json.dumps(value))



def check_candidate_metadata(root, remote):
    workspace = root / '.omx/coordination/integrations/metadata-fixture'
    coordinator.clone(root, workspace)
    marker = workspace / '.omx/integration.json'
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({'project': str(root)}))
    config = workspace / '.git/config'
    original = config.read_bytes(), marker.read_bytes()
    script = workspace / 'analysis/metadata_check.py'
    script.write_text(
        "from pathlib import Path\nimport errno\n"
        "for name, action in [('config', lambda: Path('.git/config').open('a')), "
        "('marker', lambda: Path('.omx/integration.json').unlink())]:\n"
        "    try:\n        action()\n"
        "    except OSError as exc:\n"
        "        assert exc.errno in (errno.EROFS, errno.EACCES, errno.EPERM), exc\n"
        "    else:\n        raise AssertionError('Metadata writable: ' + name)\n")
    checks = coordinator.run_checks(workspace, ['python3 analysis/metadata_check.py'])
    assert checks[0]['returncode'] == 0, checks
    assert (config.read_bytes(), marker.read_bytes()) == original


def check_clean_ahead_update(root, remote):
    workspace = employee(root, 'alice')
    base = coordinator.read_state(root)['employees']['alice']['base']
    path = workspace / 'analysis/uncollected.md'
    path.write_text('Uncollected work\n')
    git(workspace, 'add', '--', 'analysis/uncollected.md')
    subprocess.run(['bash', str(workspace / 'analysis/scripts/project_git.sh'),
                    'commit', '-m', 'Uncollected employee work'], cwd=workspace, check=True,
                   capture_output=True)
    head = git(workspace, 'rev-parse', 'HEAD')
    assert not git(workspace, 'status', '--porcelain')
    rejected(lambda: coordinator.update(workspace), 'clean ahead employee update')
    assert coordinator.read_state(root)['employees']['alice']['base'] == base
    assert git(workspace, 'rev-parse', 'HEAD') == head
    assert path.read_text() == 'Uncollected work\n'
    assert coordinator.stop_status({'hook_event_name': 'Stop', 'cwd': str(workspace)}, workspace)['decision'] == 'block'


def check_second_pending_submit(root, remote):
    workspace = employee(root, 'alice')
    first = freeze(workspace, 'alice', 'analysis/a.md', 'first\n')
    outbox = workspace / '.omx/outbox'
    original = {path.name: path.read_bytes() for path in outbox.glob('*.json')}
    remote_head = git(remote, 'rev-parse', 'main')
    rejected(lambda: freeze(workspace, 'alice', 'analysis/a.md', 'second\n'),
             'second unfinished submission')
    assert {path.name: path.read_bytes() for path in outbox.glob('*.json')} == original
    assert (workspace / 'analysis/a.md').read_text() == 'second\n'
    assert git(workspace, 'rev-parse', 'HEAD') == first['head']
    assert git(remote, 'rev-parse', 'main') == remote_head
    assert not coordinator.read_state(root)['submissions']


def check_root_sync_scope(root, remote):
    sample = root / 'analysis/shared.md'
    sample.write_text('Concurrent root edit\n')
    before = git(remote, 'rev-parse', 'main')
    with patch.object(project_sync, 'ROOT', root), \
            patch.object(project_sync, 'git', side_effect=AssertionError('Git called before scope rejection')):
        rejected(lambda: project_sync.sync('fixture', 'fixture', 'analysis/missing-evidence.json',
                                           result='fixture', files=None), 'unscoped root delivery')
    assert git(remote, 'rev-parse', 'main') == before
    assert sample.read_text() == 'Concurrent root edit\n'



def check_evidence_parent_symlink(root, remote):
    workspace = employee(root, 'alice')
    folder = workspace / 'analysis/evidence'
    folder.mkdir()
    evidence = folder / 'state.json'
    evidence.write_text(json.dumps({'status': 'passed', 'checks': [{'returncode': 0}]}))
    checker = workspace / 'analysis/check.py'
    checker.write_text(
        "from pathlib import Path\n"
        "folder=Path('analysis/evidence')\n"
        "(folder/'state.json').unlink()\n"
        "folder.rmdir()\n"
        "folder.symlink_to(" + repr(str(root / '.omx/coordination')) + ", target_is_directory=True)\n")
    with coordinator.transaction(root) as state:
        state['fixture_sentinel'] = 'Control state must survive candidate validation'
    before = coordinator.read_state(root)
    remote_head = git(remote, 'rev-parse', 'main')
    frozen = coordinator.submit(workspace, 'alice', 'Fixture symlink rejection',
                                'analysis/evidence/state.json', 'Candidate rejection', checks=[CHECK])
    receipt = coordinator.collect(root, 'alice')[-1]
    assert receipt['status'] == 'needs_retry', receipt
    assert 'symlink' in receipt['error'].lower(), receipt
    after = coordinator.read_state(root)
    assert after['schema_version'] == before['schema_version']
    assert after['fixture_sentinel'] == before['fixture_sentinel']
    assert after['tasks'] == before['tasks'] and after['sessions'] == before['sessions']
    for key in ('workspace', 'base', 'scopes', 'task'):
        assert after['employees']['alice'][key] == before['employees']['alice'][key]
    assert set(after['submissions']) == {frozen['id']}
    assert git(remote, 'rev-parse', 'main') == remote_head
    candidate = Path(receipt['recovery_workspace'])
    assert candidate.is_dir() and (candidate / 'analysis/evidence').is_symlink()
    assert evidence.is_file() and not folder.is_symlink(), 'Frozen employee evidence was altered'


def check_workspace_escape(root, remote):
    outside = root.parent / 'outside'
    outside.mkdir()
    coordination = root / '.omx/coordination'
    coordination.mkdir(parents=True)
    (coordination / 'workspaces').symlink_to(outside, target_is_directory=True)
    rejected(lambda: employee(root, 'escape'), 'workspace parent symlink escape')
    assert not list(outside.iterdir()), 'Workspace creation wrote outside project'


def check_lock(root, remote):
    path, ready = root / '.omx/coordination/test.lock', CTX.Event()
    process = CTX.Process(target=hold_lock, args=(path, ready))
    process.start()
    try:
        assert ready.wait(10), 'Child did not acquire lock'
        rejected(lambda: acquire(path, 0.1), 'simultaneous lock holder')
        process.kill()
        process.join(10)
        acquire(path, 1)
    finally:
        if process.is_alive():
            process.kill()
            process.join()


def acquire(path, timeout):
    with coordinator.lock(path, timeout=timeout):
        pass


def check():
    for test in (check_isolation, check_claims, check_parallel_delivery,
                 check_conflict, check_pushed_recovery, check_merged_validation, check_boundaries, check_workspace_escape, check_outbox_tampering, check_employee_sandbox,
                 check_session_registration, check_conflict_resolution, check_candidate_metadata,
                 check_clean_ahead_update, check_second_pending_submit, check_root_sync_scope, check_evidence_parent_symlink, check_lock):
        with tempfile.TemporaryDirectory(prefix='chx-coordination-') as temporary:
            root, remote = fixture(Path(temporary))
            with patch.object(project_sync, 'REMOTE', str(remote)):
                test(root, remote)
        print('PASS:', test.__name__, flush=True)


if __name__ == '__main__':
    check()
