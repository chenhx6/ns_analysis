#!/usr/bin/env python3
"""Isolated employee checkouts and serialized, recoverable project integration."""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid

import project_sync
import task_delivery
from check_git_content import MAX_BYTES, DECODER_SOURCE_FILES, permitted

ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILES = {'.codex/hooks.json', '.codex/config.toml'}


def identifier(value):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', value):
        raise ValueError('Use an ASCII task/employee identifier (letters, numbers, - and _)')
    return value


def relative(value):
    path = PurePosixPath(value.rstrip('/'))
    if not value or path.is_absolute() or '..' in path.parts or '.' == str(path) or '\\' in value:
        raise ValueError('Unsafe project-relative path: ' + value)
    allowed = permitted(str(path))
    if value.endswith('/'):
        allowed = permitted(str(path) + '/scope.md') or any(
            name.startswith(str(path) + '/') for name in DECODER_SOURCE_FILES)
    if str(path) != value.rstrip('/') or not allowed or str(path) in CONFIG_FILES:
        raise ValueError('Path outside employee source scope: ' + value)
    return str(path) + ('/' if value.endswith('/') else '')


def covered(name, scopes):
    return any(name == scope or (scope.endswith('/') and name.startswith(scope)) for scope in scopes)


def overlaps(left, right):
    return (left.rstrip('/') == right.rstrip('/') or covered(left.rstrip('/'), [right])
            or covered(right.rstrip('/'), [left]))


def directory(project, create=True):
    project = Path(project).resolve()
    base = project / '.omx/coordination'
    for path in [project / '.omx', base, base / 'workspaces', base / 'integrations', base / 'receipts']:
        if path.is_symlink():
            raise ValueError('Coordination directories must not be symlinks')
        if create:
            path.mkdir(exist_ok=True)
    return base


def atomic(path, value):
    path = Path(path).absolute()
    if any(parent.is_symlink() for parent in [path, *path.parents]):
        raise ValueError('State/evidence paths must not contain symlinks: ' + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('Refusing symlink state file: ' + str(path))
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def lock(path, timeout=10):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(str(path), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    started = time.monotonic()
    try:
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() - started >= timeout:
                    raise RuntimeError('Coordination busy; work is retained. Retry: ' + str(path))
                time.sleep(0.05)
        yield
    finally:
        os.close(descriptor)  # Never unlink a live flock inode; process exit releases it.


def read_state(project):
    path = directory(project, create=False) / 'state.json'
    if path.is_symlink():
        raise ValueError('Unsafe coordination state')
    if not path.exists():
        return {'schema_version': 1, 'tasks': {}, 'employees': {}, 'submissions': {}, 'sessions': {}}
    state = json.loads(path.read_text(encoding='utf-8'))
    if state.get('schema_version') != 1:
        raise ValueError('Unsupported coordination schema')
    return state


@contextmanager
def transaction(project):
    with lock(directory(project) / 'registry.lock'):
        state = read_state(project)
        yield state
        # ponytail: JSON rewrites grow with employees; use SQLite if thousands update frequently.
        atomic(directory(project) / 'state.json', state)


def environment():
    env = dict(os.environ)
    for name in ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR', 'GIT_PREFIX',
                 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES']:
        env.pop(name, None)
    env.update(GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='/bin/false', SSH_ASKPASS='/bin/false')
    return env


def git(root, *args, check=True, input_data=None):
    root = Path(root).resolve()
    metadata = root / '.project-git'
    command = ['git', '-C', str(root)]
    if not (root / '.git/HEAD').is_file() and not (root / '.git').is_file():
        if not (metadata / 'HEAD').is_file():
            raise ValueError('No existing Git repository: ' + str(root))
        command = ['git', '--git-dir=' + str(metadata), '--work-tree=' + str(root)]
    result = subprocess.run(command + ['-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false'] + list(args),
                            cwd=root, env=environment(),
                            capture_output=True, input=input_data, timeout=60)
    if check and result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', 'replace').strip())
    return result


def text(root, *args):
    return git(root, *args).stdout.decode('utf-8').strip()


def names(result):
    return [value.decode('utf-8', 'surrogateescape') for value in result.stdout.split(b'\0') if value]


def clone(project, destination):
    project, destination = Path(project).resolve(), Path(destination)
    if destination.exists():
        raise ValueError('Workspace already exists; refusing to overwrite: ' + str(destination))
    if not destination.parent.exists():
        destination.parent.mkdir(parents=True)
    source = text(project, 'rev-parse', '--absolute-git-dir')
    result = subprocess.run(['git', 'clone', '--shared', '--quiet', source, str(destination)],
                            env=environment(), capture_output=True, timeout=120)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', 'replace').strip())
    git(destination, 'remote', 'set-url', 'origin', project_sync.REMOTE)
    for key in ['user.name', 'user.email', 'credential.helper']:
        value = git(project, 'config', '--get', key, check=False)
        if value.returncode == 0:
            git(destination, 'config', key, value.stdout.decode().strip())
    git(destination, 'config', 'core.hooksPath', str(destination / '.githooks'))
    git(destination, 'config', 'core.filemode', 'false')


def employee_config(project, workspace):
    """Instance local configuration; share installed code read-only, keep state local."""
    for name in CONFIG_FILES:
        path = workspace / name
        if path.is_file():
            original = git(workspace, 'show', 'HEAD:' + name).stdout.decode('utf-8')
            path.write_text(original.replace(str(project), str(workspace)))
            # Local launch configuration is generated, not an employee source edit.
            git(workspace, 'update-index', '--skip-worktree', '--', name)
    for name in ['analysis/vendor/oh-my-codex/dist', 'analysis/vendor/oh-my-codex/node_modules']:
        source, target = project / name, workspace / name
        if source.is_dir() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(source, target_is_directory=True)
    (workspace / '.runtime').mkdir(exist_ok=True)


def create(project, task, employee, scopes, title=''):
    project = Path(project).resolve()
    task, employee = identifier(task), identifier(employee)
    scopes = sorted({relative(scope) for scope in scopes})
    if not scopes:
        raise ValueError('Assign at least one explicit file/directory scope')
    if text(project, 'remote', 'get-url', 'origin') != project_sync.REMOTE:
        raise ValueError('Unexpected project remote')
    base = directory(project)
    workspace = base / 'workspaces' / employee
    with transaction(project) as state:
        old = state['employees'].get(employee)
        if old:
            if old['task'] != task or old['scopes'] != scopes:
                raise ValueError('Employee already assigned; use another ID or an explicit handoff')
            if old['status'] != 'creating':
                return old
        for member in state['employees'].values():
            if member['employee'] != employee and member['task'] == task and any(
                    overlaps(left, right) for left in scopes for right in member['scopes']):
                raise ValueError('Task scope already assigned to ' + member['employee'] + '; hand it off first')
        state['tasks'].setdefault(task, {'task': task, 'title': title or task, 'members': []})
        if employee not in state['tasks'][task]['members']:
            state['tasks'][task]['members'].append(employee)
        record = {'employee': employee, 'task': task, 'scopes': scopes, 'project': str(project),
                  'workspace': str(workspace), 'base': text(project, 'rev-parse', 'HEAD'),
                  'status': 'creating', 'delivered_head': None, 'submissions': []}
        state['employees'][employee] = record
    with lock(base / ('create-' + employee + '.lock')):
        if not workspace.exists():
            clone(project, workspace)
            git(workspace, 'checkout', '--quiet', '-b', 'employee/' + employee, record['base'])
        elif text(workspace, 'symbolic-ref', '--short', 'HEAD') != 'employee/' + employee:
            raise ValueError('Interrupted workspace differs from its registration; preserved for recovery')
        employee_config(project, workspace)
        atomic(workspace / '.omx/employee.json', dict(record, schema_version=1))
        with transaction(project) as state:
            state['employees'][employee]['status'] = 'active'
            record = state['employees'][employee]
    return record


def member(workspace):
    workspace = Path(workspace).resolve()
    if (workspace / '.omx').is_symlink() or (workspace / '.git').is_symlink():
        raise ValueError('Employee runtime/Git metadata must not be symlinks')
    marker = workspace / '.omx/employee.json'
    if marker.is_symlink() or not marker.is_file():
        raise ValueError('This is not a registered isolated employee workspace')
    payload = json.loads(marker.read_text())
    project = Path(payload['project']).resolve()
    employee = identifier(payload['employee'])
    expected = directory(project, create=False) / 'workspaces' / employee
    if workspace != expected or expected.is_symlink() or Path(payload['workspace']).resolve() != expected:
        raise ValueError('Employee workspace identity/path mismatch')
    record = read_state(project)['employees'].get(employee)
    if not record or Path(record['workspace']).resolve() != workspace:
        raise ValueError('Employee is not registered at this project')
    if text(workspace, 'rev-parse', '--show-toplevel') != str(workspace):
        raise ValueError('Employee repository is not physically isolated')
    return project, record


def release(project, employee, paths):
    employee = identifier(employee)
    paths = [relative(path) for path in paths]
    with transaction(project) as state:
        record = state['employees'][employee]
        for path in paths:
            if path not in record['scopes']:
                raise ValueError('Release must name an exact assigned scope')
        if text(Path(record['workspace']), 'status', '--porcelain'):
            raise ValueError('Commit/submit current edits before releasing their scope')
        if text(Path(record['workspace']), 'rev-parse', 'HEAD') not in {record['base'], record.get('delivered_head')}:
            raise ValueError('Collect employee commits before releasing their scope')
        record['scopes'] = [scope for scope in record['scopes'] if scope not in paths]
    return record


def checked_paths(workspace, record):
    changed = set(names(git(workspace, 'diff', '--no-renames', '--name-only', '-z', record['base'], 'HEAD')))
    changed.update(names(git(workspace, 'diff', '--no-renames', '--name-only', '-z')))
    changed.update(names(git(workspace, 'diff', '--cached', '--no-renames', '--name-only', '-z')))
    changed.update(names(git(workspace, 'ls-files', '--others', '--exclude-standard', '-z')))
    for name in sorted(changed):
        relative(name)
        if not covered(name, record['scopes']):
            raise ValueError('Employee edit outside assigned scope: ' + name)
        path = workspace / name
        cursor = path
        while cursor != workspace:
            if cursor.is_symlink():
                raise ValueError('Employee source paths must not contain symlinks: ' + name)
            cursor = cursor.parent
        if path.exists() and (not path.is_file() or path.stat().st_size > MAX_BYTES):
            raise ValueError('Unsafe or oversized employee file: ' + name)
    return sorted(changed)


def run_checks(workspace, checks):
    if not checks:
        raise ValueError('Provide --check with a repeatable validation command for the merged result')
    results = []
    for command in checks:
        args = shlex.split(command)
        if not args:
            raise ValueError('Validation command cannot be empty')
        sandbox = shutil.which('bwrap')
        if not sandbox:
            raise RuntimeError('Candidate validation sandbox unavailable; keep submission for a supported host')
        prefix = [sandbox, '--ro-bind', '/', '/', '--tmpfs', '/tmp']
        for name in ['.omx/integration.json', '.omx/employee.json']:
            marker = workspace / name
            if marker.is_file():
                anchor = Path(json.loads(marker.read_text())['project']).resolve()
                if str(anchor).startswith('/tmp/'):
                    prefix.extend(['--ro-bind', str(anchor), str(anchor)])
                break
        prefix += ['--bind', str(workspace), str(workspace)]
        for protected in ['.git', '.omx']:
            if (workspace / protected).exists():
                prefix += ['--ro-bind', str(workspace / protected), str(workspace / protected)]
        prefix += ['--proc', '/proc', '--dev', '/dev', '--unshare-all', '--new-session', '--die-with-parent',
                  '--chdir', str(workspace), '--']
        result = subprocess.run(prefix + args, cwd=workspace, env=environment(), capture_output=True, timeout=300)
        item = {'command': args, 'returncode': result.returncode,
                'output': (result.stdout + result.stderr).decode('utf-8', 'replace')[-8000:]}
        results.append(item)
        if result.returncode:
            raise RuntimeError('Validation failed: ' + command + '\n' + item['output'])
    return results


def submit(workspace, task, message, evidence, result, basis='用户任务与现有项目内容',
           executor='Codex', checks=None):
    workspace = Path(workspace).resolve()
    project, record = member(workspace)
    if not result or not task:
        raise ValueError('A task description and actual outcome are required')
    evidence = relative(evidence)
    with lock(workspace / '.omx/submission.lock'):
        state = read_state(project)
        for path in (workspace / '.omx/outbox').glob('*.json'):
            if path.is_symlink():
                raise ValueError('Outbox requests must not be symlinks')
            previous = json.loads(path.read_text())
            known = state['submissions'].get(previous['id'], {})
            repairing = (known.get('status') == 'conflict' and known.get('base') != record['base']
                         and record['status'] in {'resolving', 'delivered'})
            if known.get('status') != 'delivered' and not repairing:
                raise ValueError('An immutable submission is already pending; collect/integrate it before submitting again')
        checked_paths(workspace, record)
        if not checks or any(not shlex.split(command) for command in checks):
            raise ValueError('Provide repeatable --check commands for controller candidate validation')
        paths = checked_paths(workspace, record)
        if not covered(evidence, record['scopes']):
            raise ValueError('Evidence must belong to the assigned scope')
        saved = json.loads((workspace / evidence).read_text())
        if saved.get('status') != 'passed' or not saved.get('checks') or any(
                check.get('returncode') != 0 for check in saved['checks']):
            raise ValueError('Evidence does not contain passing actual checks')
        validation = saved['checks']  # Employee evidence is rechecked in the controller's real candidate sandbox.
        if paths:
            git(workspace, 'add', '--', *[':(literal)' + path for path in paths])
        wrapper = ['bash', str(workspace / 'analysis/scripts/project_git.sh')]
        subprocess.run(wrapper + ['diff', '--cached', '--check'], cwd=workspace,
                       env=environment(), check=True, capture_output=True)
        if git(workspace, 'diff', '--cached', '--quiet', check=False).returncode == 1:
            subprocess.run(wrapper + ['commit', '-m', message], cwd=workspace,
                           env=environment(), check=True, capture_output=True)
        head = text(workspace, 'rev-parse', 'HEAD')
        paths = names(git(workspace, 'diff', '--no-renames', '--name-only', '-z', record['base'], head))
        if not paths:
            raise ValueError('No employee changes to submit')
        submission = {'id': uuid.uuid4().hex, 'employee': record['employee'], 'task': record['task'],
                      'description': task, 'base': record['base'], 'head': head, 'paths': paths,
                      'workspace': str(workspace), 'evidence': evidence,
                      'evidence_sha256': hashlib.sha256((workspace / evidence).read_bytes()).hexdigest(),
                      'checks': list(checks), 'employee_validation': validation,
                      'message': message, 'result': result, 'basis': basis, 'executor': executor,
                      'status': 'submitted', 'attempts': []}
        atomic(workspace / '.omx/outbox' / (submission['id'] + '.json'), submission)
    return {'status': 'awaiting_collection', 'id': submission['id'], 'employee': record['employee'],
            'task': record['task'], 'head': head,
            'collect': 'python3 ' + str(project / 'analysis/scripts/session_coordinator.py') +
                       ' collect --employee ' + record['employee']}


def validate_submission(project, submission):
    state = read_state(project)
    employee = state['employees'][identifier(submission['employee'])]
    workspace = Path(employee['workspace'])
    member(workspace)
    identifier(submission['id'])
    if submission['task'] != employee['task'] or submission['workspace'] != str(workspace):
        raise ValueError('Outbox identity differs from controller registration')
    if submission['base'] != employee['base'] or not re.fullmatch(r'[a-f0-9]{40,64}', submission['head']):
        raise ValueError('Outbox baseline/OID differs from its registration')
    git(workspace, 'merge-base', '--is-ancestor', submission['base'], submission['head'])
    paths = names(git(workspace, 'diff', '--no-renames', '--name-only', '-z',
                      submission['base'], submission['head']))
    if sorted(paths) != sorted(submission['paths']):
        raise ValueError('Outbox path list differs from the frozen Git diff')
    for name in paths:
        relative(name)
        if not covered(name, employee['scopes']):
            raise ValueError('Frozen submission changes an unassigned path: ' + name)
    tree = git(workspace, 'ls-tree', '-r', '-z', submission['head']).stdout
    entries = []
    for entry in tree.split(b'\0'):
        if not entry:
            continue
        metadata, raw_path = entry.split(b'\t', 1)
        mode, kind, oid = metadata.split()
        name = raw_path.decode('utf-8', 'surrogateescape')
        if mode not in {b'100644', b'100755'} or kind != b'blob' or not permitted(name):
            raise ValueError('Unsafe submission tree entry: ' + name)
        entries.append((name, oid))
    objects = sorted({oid for _, oid in entries})
    sizes = git(workspace, 'cat-file', '--batch-check=%(objectname) %(objectsize)',
                input_data=b'\n'.join(objects) + b'\n').stdout
    sizes = {line.split()[0]: int(line.split()[1]) for line in sizes.splitlines()}
    for name, oid in entries:
        size = sizes[oid]
        if size > MAX_BYTES:
            raise ValueError('Oversized frozen submission blob: ' + name)
    evidence = relative(submission['evidence'])
    if not covered(evidence, employee['scopes']):
        raise ValueError('Submission evidence outside assigned scope')
    blob = git(workspace, 'show', submission['head'] + ':' + evidence).stdout
    if hashlib.sha256(blob).hexdigest() != submission['evidence_sha256']:
        raise ValueError('Immutable submission evidence differs')
    if not submission['checks']:
        raise ValueError('Submission must provide repeatable validation')
    return employee


def collect(project, employee=None):
    project = Path(project).resolve()
    state = read_state(project)
    members = [identifier(employee)] if employee else list(state['employees'])
    results = []
    for name in members:
        record = state['employees'][name]
        workspace = Path(record['workspace'])
        for path in sorted((workspace / '.omx/outbox').glob('*.json')):
            if path.is_symlink():
                raise ValueError('Outbox requests must not be symlinks')
            submission = json.loads(path.read_text())
            known = read_state(project)['submissions'].get(submission['id'])
            if known:
                immutable = ['id', 'employee', 'task', 'base', 'head', 'paths', 'evidence_sha256', 'checks']
                if any(known[key] != submission[key] for key in immutable):
                    raise ValueError('Existing submission ID has a different immutable request')
            else:
                if submission['employee'] != name or path.stem != submission['id']:
                    raise ValueError('Outbox employee/file identity mismatch')
                validate_submission(project, submission)
                with transaction(project) as current:
                    if submission['id'] not in current['submissions']:
                        item = {key: submission[key] for key in ['id', 'employee', 'task', 'description', 'base',
                                'head', 'paths', 'workspace', 'evidence', 'evidence_sha256', 'checks',
                                'employee_validation', 'message', 'result', 'basis', 'executor']}
                        item.update(status='submitted', attempts=[])
                        current['submissions'][item['id']] = item
                        worker = current['employees'][name]
                        worker['submissions'].append(item['id'])
                        worker['status'] = 'submitted'
            if known and known['status'] not in {'submitted', 'integrating'}:
                results.append(known.get('receipt', known))
            else:
                results.append(integrate(project, submission['id']))
    return results


@contextmanager
def repository_context(root):
    """Use existing verified delivery code in one isolated integration process."""
    old = project_sync.ROOT, task_delivery.ROOT, task_delivery.PENDING, project_sync.TRUSTED_INTEGRATION
    project_sync.ROOT = task_delivery.ROOT = root
    task_delivery.PENDING = root / '.omx/delivery/pending.json'
    project_sync.TRUSTED_INTEGRATION = True
    try:
        yield
    finally:
        project_sync.ROOT, task_delivery.ROOT, task_delivery.PENDING, project_sync.TRUSTED_INTEGRATION = old


def record_submission(project, submission_id, **updates):
    with transaction(project) as state:
        state['submissions'][submission_id].update(updates)
        return state['submissions'][submission_id]


def refresh(project, source, receipt):
    head = receipt['head']
    git(project, 'fetch', '--no-tags', str(source), head)
    for tag in receipt.get('tags', []):
        git(project, 'fetch', '--no-tags', str(source), 'refs/tags/' + tag + ':refs/tags/' + tag)
    old = text(project, 'rev-parse', 'HEAD')
    if git(project, 'merge-base', '--is-ancestor', old, head, check=False).returncode:
        return False
    if text(project, 'diff', '--cached', '--name-only'):
        return False
    result = git(project, '-c', 'merge.autoStash=false', 'merge', '--ff-only', head, check=False)
    return result.returncode == 0


def finish(project, submission, workspace, receipt):
    refreshed = refresh(project, workspace, receipt)
    receipt = dict(receipt, submission=submission['id'], employee=submission['employee'],
                   task=submission['task'], root_refresh_pending=not refreshed)
    employee_root = Path(submission['workspace'])
    employee_head = submission['head']
    try:
        with lock(employee_root / '.omx/submission.lock', timeout=0):
            if not text(employee_root, 'status', '--porcelain') and text(employee_root, 'rev-parse', 'HEAD') == employee_head:
                git(employee_root, 'fetch', '--no-tags', str(workspace), receipt['head'])
                merged = git(employee_root, 'merge', '--ff-only', receipt['head'], check=False)
                if merged.returncode == 0:
                    employee_head = receipt['head']
    except RuntimeError:
        pass  # Concurrent employee edits are retained; update can safely catch up later.
    with transaction(project) as state:
        item = state['submissions'][submission['id']]
        item.update(status='delivered', receipt=receipt)
        record = state['employees'][submission['employee']]
        record.update(status='delivered', delivered_head=employee_head)
        if employee_head == receipt['head']:
            record['base'] = employee_head
    atomic(directory(project) / 'receipts' / (submission['id'] + '.json'), receipt)
    atomic(employee_root / '.omx/receipts' / (submission['id'] + '.json'), receipt)
    return receipt


def recovered(project, submission):
    """Confirm an already pushed attempt before creating another integration commit."""
    for attempt in reversed(submission['attempts']):
        workspace = Path(attempt)
        path = workspace / '.omx/delivery/tag_receipt.json'
        if not path.is_file():
            continue
        receipt = json.loads(path.read_text())
        head, tag = receipt['head'], receipt['tag']
        git(workspace, 'fetch', 'origin')
        branch = text(workspace, 'symbolic-ref', '--short', 'HEAD')
        remote = 'refs/remotes/origin/' + branch
        if git(workspace, 'merge-base', '--is-ancestor', head, remote, check=False).returncode:
            continue
        result = text(workspace, 'ls-remote', 'origin', 'refs/tags/' + tag + '^{}').split()
        if result and result[0] == head:
            return finish(project, submission, workspace,
                          {'status': 'pushed', 'head': head, 'branch': branch,
                           'remote': project_sync.REMOTE, 'tags': [tag]})
    return None


def integrate(project, submission_id):
    project = Path(project).resolve()
    submission_id = identifier(submission_id)
    base = directory(project)
    try:
        with lock(base / 'integration.lock', timeout=10):
            submission = read_state(project)['submissions'][submission_id]
            if submission['status'] == 'delivered':
                return submission['receipt']
            receipt = recovered(project, submission) if submission['attempts'] else None
            if receipt:
                return receipt
            source = Path(submission['workspace'])
            employee = validate_submission(project, submission)
            workspace = base / 'integrations' / submission_id / uuid.uuid4().hex
            clone(project, workspace)
            atomic(workspace / '.omx/integration.json', {'project': str(project), 'submission': submission_id})
            submission['attempts'].append(str(workspace))
            record_submission(project, submission_id, status='integrating', attempts=submission['attempts'])
            try:
                git(workspace, 'fetch', 'origin')
                branch = text(workspace, 'symbolic-ref', '--short', 'HEAD')
                remote = 'refs/remotes/origin/' + branch
                if git(workspace, 'rev-parse', '--verify', remote, check=False).returncode == 0:
                    git(workspace, 'merge', '--ff-only', remote)
                git(workspace, 'fetch', '--no-tags', str(source), submission['head'])
                merge = git(workspace, 'merge', '--no-commit', '--no-ff', submission['head'], check=False)
                if merge.returncode:
                    conflict = names(git(workspace, 'diff', '--name-only', '--diff-filter=U', '-z'))
                    status = 'conflict' if conflict else 'integration_failed'
                    return record_submission(project, submission_id, status=status, conflict_paths=conflict,
                                             recovery_workspace=str(workspace),
                                             error=merge.stderr.decode('utf-8', 'replace')[-4000:])
                candidate = text(workspace, 'write-tree')
                merged_validation = run_checks(workspace, submission['checks'])
                # Validators may regenerate the task evidence; validate and commit that final result.
                dirty = set(names(git(workspace, 'diff', '--no-renames', '--name-only', '-z')))
                dirty.update(names(git(workspace, 'diff', '--cached', '--no-renames', '--name-only', '-z', candidate)))
                dirty.update(names(git(workspace, 'ls-files', '--others', '--exclude-standard', '-z')))
                for name in dirty:
                    if not covered(name, employee['scopes']):
                        raise ValueError('Merged validator modified an unassigned path: ' + name)
                atomic(workspace / submission['evidence'], {
                    'status': 'passed', 'checks': merged_validation, 'scope': 'Actual merged candidate validation',
                    'submission': submission_id, 'employee_head': submission['head'],
                    'employee_evidence_sha256': submission['evidence_sha256']})
                with repository_context(workspace):
                    receipt = project_sync.sync(submission['description'], submission['message'],
                                                submission['evidence'], submission['result'],
                                                submission['basis'], submission['executor'])
                record_submission(project, submission_id, merged_validation=merged_validation)
                return finish(project, submission, workspace, receipt)
            except Exception as exc:
                return record_submission(project, submission_id, status='needs_retry',
                                         recovery_workspace=str(workspace), error=str(exc)[-6000:])
    except RuntimeError as exc:
        if 'Coordination busy;' not in str(exc):
            raise
        return record_submission(project, submission_id, status='queued', error=str(exc))


def update(workspace):
    workspace = Path(workspace).resolve()
    project, record = member(workspace)
    with lock(workspace / '.omx/submission.lock'):
        if text(workspace, 'status', '--porcelain'):
            raise ValueError('Commit or preserve local edits before updating; no auto stash or reset')
        head = text(workspace, 'rev-parse', 'HEAD')
        if head not in {record['base'], record.get('delivered_head')}:
            raise ValueError('Submit/collect employee commits before updating the registered base')
        git(workspace, 'fetch', '--no-tags', text(project, 'rev-parse', '--absolute-git-dir'), 'HEAD')
        target = text(workspace, 'rev-parse', 'FETCH_HEAD')
        if git(workspace, 'merge-base', '--is-ancestor', head, target, check=False).returncode:
            raise ValueError('Employee history is not fully integrated; preserve it and resolve before update')
        git(workspace, 'merge', '--ff-only', target)
        with transaction(project) as state:
            worker = state['employees'][record['employee']]
            worker['base'] = text(workspace, 'rev-parse', 'HEAD')
            if worker['status'] == 'delivered':
                worker['delivered_head'] = worker['base']
    return {'status': 'updated', 'head': text(workspace, 'rev-parse', 'HEAD')}


def resolve(project, employee):
    """Bring current project history into a clean employee branch for explicit conflict repair."""
    project = Path(project).resolve()
    record = read_state(project)['employees'][identifier(employee)]
    workspace = Path(record['workspace'])
    member(workspace)
    with lock(directory(project) / 'integration.lock'), lock(workspace / '.omx/submission.lock'):
        if text(workspace, 'status', '--porcelain'):
            raise ValueError('Preserve/commit employee edits before starting conflict repair')
        git(project, 'fetch', 'origin')
        branch = text(project, 'symbolic-ref', '--short', 'HEAD')
        current = text(project, 'rev-parse', 'refs/remotes/origin/' + branch)
        git(workspace, 'fetch', '--no-tags', text(project, 'rev-parse', '--absolute-git-dir'), current)
        result = git(workspace, 'merge', '--no-commit', '--no-ff', current, check=False)
        conflicts = names(git(workspace, 'diff', '--name-only', '--diff-filter=U', '-z'))
        if result.returncode and not conflicts:
            raise RuntimeError(result.stderr.decode('utf-8', 'replace'))
        with transaction(project) as state:
            state['employees'][employee].update(base=current, status='resolving')
    return {'status': 'resolve_in_employee_workspace', 'workspace': str(workspace), 'conflict_paths': conflicts,
            'next': 'Resolve and commit this merge, rerun task validation, then submit a new immutable outbox'}


def assign(project, employee, task, scopes, title=''):
    """Give a clean automatically registered employee an explicit shared task."""
    project = Path(project).resolve()
    employee, task = identifier(employee), identifier(task)
    scopes = sorted({relative(path) for path in scopes})
    if not scopes:
        raise ValueError('Assign explicit task file scopes')
    with transaction(project) as state:
        record = state['employees'][employee]
        workspace = Path(record['workspace'])
        if text(workspace, 'status', '--porcelain') or text(workspace, 'rev-parse', 'HEAD') != record['base']:
            raise ValueError('Assignment requires a clean workspace at its registered base')
        if any(item['status'] != 'delivered' for item in state['submissions'].values()
               if item['employee'] == employee):
            raise ValueError('Resolve pending submissions before reassigning an employee')
        for other in state['employees'].values():
            if other['employee'] != employee and other['task'] == task and any(
                    overlaps(left, right) for left in scopes for right in other['scopes']):
                raise ValueError('Scope already assigned to ' + other['employee'])
        state['tasks'][record['task']]['members'].remove(employee)
        state['tasks'].setdefault(task, {'task': task, 'title': title or task, 'members': []})
        state['tasks'][task]['members'].append(employee)
        record.update(task=task, scopes=scopes, status='active')
        atomic(workspace / '.omx/employee.json', dict(record, schema_version=1))
        return record


def stop_status(payload, root):
    if payload.get('hook_event_name') != 'Stop' or payload.get('stop_hook_active'):
        return {}
    try:
        workspace = Path(root).resolve()
        project, record = member(workspace)
        dirty = bool(text(workspace, 'status', '--porcelain'))
        head = text(workspace, 'rev-parse', 'HEAD')
        if not dirty and record.get('delivered_head') == head:
            return {}
        if not dirty and head == record['base'] and not record['submissions']:
            return {}
        pending = [json.loads(path.read_text()) for path in (workspace / '.omx/outbox').glob('*.json')
                   if not path.is_symlink()]
        if not dirty and any(item.get('head') == head for item in pending):
            return {'systemMessage': '当前员工成果已冻结并等待控制端收集；无需重复提交。'
                    '在管理 session 执行 session_coordinator.py collect --employee ' + record['employee']}
        latest = read_state(project)['submissions'].get(record['submissions'][-1], {}) if record['submissions'] else {}
        if latest.get('status') in {'conflict', 'needs_retry', 'queued', 'integration_failed'}:
            return {'systemMessage': '员工成果已保留，需恢复整合：' + latest.get('status', '') +
                    '；python3 ' + str(project / 'analysis/scripts/session_coordinator.py') +
                    ' integrate --submission ' + latest['id']}
        return {'decision': 'block', 'reason': '当前员工任务尚未交付；仅处理本员工工作区：' + str(workspace) +
                '。按 task-tag 提交并提供可重复的 --check；不处理其他员工或主目录实时记录本。'}
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        return {'systemMessage': '员工交付状态核查失败，保留成果：' + str(exc)}


def hook(payload):
    cwd = Path(payload.get('cwd', str(ROOT))).resolve()
    event = payload.get('hook_event_name', 'SessionStart')
    session = payload.get('session_id')
    if cwd == ROOT and not (ROOT / '.omx/employee.json').is_file() and session:
        state = read_state(ROOT)
        bound = state['sessions'].get(session)
        if not bound and event == 'SessionStart':
            employee = 'session-' + hashlib.sha256(session.encode()).hexdigest()[:16]
            scopes = ['analysis/', 'AGENTS.md', 'README.md', '.gitignore', '.agents/skills/',
                      '.codex/skills/', '.codex/agents/', '.codex/prompts/', '.githooks/',
                      'decode_data/DecodeAndSortAll/']
            record = create(ROOT, employee, employee, scopes, title='新 session 独立任务（可通过 assign 细分）')
            with transaction(ROOT) as state:
                state['sessions'][session] = record['employee']
            bound = record['employee']
        if bound:
            cwd = Path(read_state(ROOT)['employees'][bound]['workspace'])
    workspace = cwd
    while workspace != workspace.parent and not (workspace / '.omx/employee.json').is_file():
        if workspace == ROOT:
            break
        workspace = workspace.parent
    if (workspace / '.omx/employee.json').is_file():
        project, record = member(workspace)
        if event == 'Stop':
            return stop_status(payload, workspace)
        context = ('本 session 是员工 ' + record['employee'] + '，共同任务 ' + record['task'] +
                   '。所有编辑/程序 cwd 必须位于独立工作区 ' + str(workspace) +
                   '；允许源码范围：' + ', '.join(record['scopes']) +
                   '。主项目 ' + str(project) + ' 仅作为只读输入与串行整合目标。'
                   '使用 project_sync.py sync --check 提交；禁止直接推送主分支。'
                   '此处只是工作区分配，宿主 cwd/沙箱仍以真实会话为准；所有工具显式使用该工作区路径。'
                   'CLI launch 提供窄写权限；App 新聊天须选该工作区以获得对应沙箱。')
    else:
        if event == 'Stop':
            return {}  # Control sessions do not own every dirty file in the project.
        context = ('本目录是 chx 项目的管理/整合目录。新员工任务先运行 python3 ' +
                   str(ROOT / 'analysis/scripts/session_coordinator.py') +
                   ' create --task <ascii-task> --employee <ascii-id> --scope <path>，'
                   '再使用 launch 或在返回的独立工作区新开 session。'
                   'SessionStart 不能替宿主迁移当前 cwd/沙箱；不要在主目录并发编辑任务文件。')
    return {'hookSpecificOutput': {'hookEventName': payload.get('hook_event_name', 'SessionStart'),
                                   'additionalContext': context}}


def launch(project, employee, prompt=None):
    employee = identifier(employee)
    record = read_state(project)['employees'][employee]
    workspace = Path(record['workspace'])
    member(workspace)
    binary = shutil.which('codex')
    if not binary:
        raise RuntimeError('Codex CLI is unavailable; open a new App session in ' + str(workspace))
    with lock(workspace / '.omx/launch.lock', timeout=0):
        args = [binary, '-C', str(workspace), '--sandbox', 'workspace-write']
        if prompt:
            args = [binary, 'exec', '-C', str(workspace), '--sandbox', 'workspace-write', prompt]
        process = subprocess.Popen(args, cwd=workspace, env=environment())
        last_error = None
        try:
            while process.poll() is None:
                try:
                    collect(project, employee)
                except (ValueError, RuntimeError) as exc:
                    if str(exc) != last_error:
                        print('员工成果保留，收集暂未完成：' + str(exc), file=sys.stderr)
                        last_error = str(exc)
                time.sleep(1)
            collect(project, employee)
            return process.returncode
        except BaseException:
            if process.poll() is None:
                process.terminate()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default=str(ROOT))
    commands = parser.add_subparsers(dest='command', required=True)
    create_cmd = commands.add_parser('create')
    create_cmd.add_argument('--task', required=True)
    create_cmd.add_argument('--employee', default='worker-' + uuid.uuid4().hex[:12])
    create_cmd.add_argument('--scope', action='append', required=True)
    create_cmd.add_argument('--title', default='')
    commands.add_parser('status')
    release_cmd = commands.add_parser('release')
    release_cmd.add_argument('--employee', required=True)
    release_cmd.add_argument('--path', action='append', required=True)
    assign_cmd = commands.add_parser('assign')
    assign_cmd.add_argument('--employee', required=True)
    assign_cmd.add_argument('--task', required=True)
    assign_cmd.add_argument('--scope', action='append', required=True)
    assign_cmd.add_argument('--title', default='')
    integrate_cmd = commands.add_parser('integrate')
    integrate_cmd.add_argument('--submission', required=True)
    collect_cmd = commands.add_parser('collect')
    collect_cmd.add_argument('--employee')
    resolve_cmd = commands.add_parser('resolve')
    resolve_cmd.add_argument('--employee', required=True)
    update_cmd = commands.add_parser('update')
    update_cmd.add_argument('--workspace', required=True)
    launch_cmd = commands.add_parser('launch')
    launch_cmd.add_argument('--employee', required=True)
    launch_cmd.add_argument('--prompt')
    commands.add_parser('hook')
    args = parser.parse_args()
    project = Path(args.project).resolve()
    if args.command == 'create':
        result = create(project, args.task, args.employee, args.scope, args.title)
    elif args.command == 'status':
        result = read_state(project)
    elif args.command == 'release':
        result = release(project, args.employee, args.path)
    elif args.command == 'assign':
        result = assign(project, args.employee, args.task, args.scope, args.title)
    elif args.command == 'integrate':
        result = integrate(project, args.submission)
    elif args.command == 'collect':
        result = collect(project, args.employee)
    elif args.command == 'resolve':
        result = resolve(project, args.employee)
    elif args.command == 'update':
        result = update(args.workspace)
    elif args.command == 'launch':
        raise SystemExit(launch(project, args.employee, args.prompt))
    else:
        result = hook(json.loads(sys.stdin.read(1024 * 1024) or '{}'))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
