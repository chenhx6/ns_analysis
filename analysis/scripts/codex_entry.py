#!/usr/bin/env python3
"""Keep the normal codex command while selecting an isolated project employee."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid

import session_coordinator as coordinator
import codex_prompt

ROOT = Path(__file__).resolve().parents[2]
BEGIN = '# >>> chx isolated codex sessions >>>'
END = '# <<< chx isolated codex sessions <<<'
NON_AGENT = {'login', 'logout', 'mcp', 'completion', 'features', 'help', 'plugin',
             'agents', 'doctor', 'update', 'queue', 'archive', 'delete',
             'migrate-rollouts', 'unarchive'}
NON_LOCAL = {'app', 'app-server', 'exec-server', 'debug', 'cloud', 'cloud-tasks',
             'remote-control', 'mcp-server', 'apply', 'a', 'sandbox'}
SAFE_WORKER_CONFIG = {'model', 'model_reasoning_effort', 'model_reasoning_summary',
                      'model_verbosity', 'model_provider', 'preferred_auth_method'}
VALUE_OPTIONS = {'-m', '--model', '-p', '--profile', '-a', '--ask-for-approval', '-c', '--config',
                 '-i', '--image', '-o', '--output-last-message', '--color', '--output-schema',
                 '--local-provider', '--thread-source', '--cyber-access-program', '--remote-auth-token-env',
                 '-C', '--cd', '-s', '--sandbox', '--add-dir', '--remote', '--enable', '--disable'}


def split_arguments(args):
    """Remove only our selectors, retaining literal native arguments and boundaries."""
    selected = {'employee': None, 'task': None, 'scopes': []}
    native = []
    index = 0
    while index < len(args):
        value = args[index]
        if value == '--':
            native.extend(args[index:])
            break
        name, equal, attached = value.partition('=')
        if name in {'--chx-employee', '--chx-task', '--chx-scope'}:
            if equal:
                parameter = attached
            else:
                index += 1
                if index == len(args):
                    raise ValueError('Missing value for ' + name)
                parameter = args[index]
            if not parameter:
                raise ValueError('Empty value for ' + name)
            if name == '--chx-scope':
                selected['scopes'].append(parameter)
            else:
                key = name[6:]
                if selected[key] is not None:
                    raise ValueError('Duplicate selector: ' + name)
                selected[key] = parameter
        else:
            native.append(value)
        index += 1
    return selected, native


def validate_launch(args):
    option_value = False
    index = 0
    while index < len(args):
        value = args[index]
        if value == '--':
            break
        if option_value:
            option_value = False
            index += 1
            continue
        name, equal, attached = value.partition('=')
        if name in {'-C', '--cd', '-s', '--sandbox', '--add-dir', '--worktree',
                    '--remote', '--enable', '--disable', '--dangerously-bypass-hook-trust',
                    '--dangerously-bypass-approvals-and-sandbox', '--yolo', '--full-auto'}:
            raise ValueError('Managed launch selects its own cwd/write boundary; remove ' + name)
        if name in {'-c', '--config'}:
            if equal:
                parameter = attached
            else:
                index += 1
                if index == len(args):
                    raise ValueError('Missing config value')
                parameter = args[index]
            key = parameter.partition('=')[0].strip()
            if key not in SAFE_WORKER_CONFIG:
                raise ValueError('Managed launch does not accept permission/config override: ' + key)
        elif name in VALUE_OPTIONS:
            if name in {'-p', '--profile'}:
                raise ValueError('A named profile can change write permissions; use explicit model options here')
            option_value = not equal
        elif value.startswith('-C') or value.startswith('-s') and not value.startswith('--'):
            raise ValueError('Managed launch rejects compact cwd/sandbox overrides')
        elif value.startswith('-c') and name != '-c' and not value.startswith('--'):
            raise ValueError('Use separate --config for supported model overrides')
        elif value.startswith('-p') and name != '-p' and not value.startswith('--'):
            raise ValueError('Compact profiles can change write permissions; use explicit model options')
        index += 1


def positional_index(args):
    index = 0
    while index < len(args):
        value = args[index]
        if value == '--':
            return None  # What follows is a literal prompt, not a native subcommand.
        if not value.startswith('-'):
            return index
        name, equal, _ = value.partition('=')
        if name in VALUE_OPTIONS and not equal:
            index += 1
        index += 1
    return None


def first_positional(args):
    index = positional_index(args)
    return args[index] if index is not None else None


def resume_command(args):
    index = positional_index(args)
    if index is None:
        return False
    command = args[index]
    if command in {'exec', 'e'}:
        command = first_positional(args[index + 1:])
    return command in {'resume', 'fork'}


def output_paths(args):
    paths = []
    index = 0
    while index < len(args):
        value = args[index]
        if value == '--':
            break
        name, equal, attached = value.partition('=')
        if name in {'-o', '--output-last-message'}:
            if equal:
                path = attached
            else:
                index += 1
                if index == len(args):
                    raise ValueError('Missing CLI output path')
                path = args[index]
            paths.append(path)
        elif value.startswith('-o') and not value.startswith('--'):
            paths.append(value[2:])
        elif name in VALUE_OPTIONS and not equal:
            index += 1
        index += 1
    for value in paths:
        path = Path(value)
        if (not value or not path.parts or path.is_absolute() or '..' in path.parts or
                '\\' in value or path.parts[0] == '.git'):
            raise ValueError('CLI output must use a safe employee-relative path: ' + value)
    return paths


def save_backup(bashrc, original):
    """Keep private shell bytes on the same filesystem as the user's Bash config."""
    directory = Path(tempfile.mkdtemp(prefix='.chx-codex-backup-', dir=str(bashrc.parent)))
    if directory.stat().st_mode & 0o777 != 0o700:
        raise ValueError('Bash backup filesystem does not preserve private directory permissions')
    backup = directory / 'bashrc.original'
    with os.fdopen(os.open(str(backup), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as stream:
        stream.write(original)
    if backup.stat().st_mode & 0o777 != 0o600:
        raise ValueError('Bash backup filesystem does not preserve private file permissions')
    coordinator.atomic(ROOT / '.omx/coordination/shell-backup.json',
                       {'bashrc': str(bashrc), 'backup': str(backup), 'private_directory': str(directory)})
    return backup


def install_shell(bashrc, co=False):
    """Install one independent shell function, preserving the other launcher block."""
    begin = '# >>> chx co prompt sessions >>>' if co else BEGIN
    end = '# <<< chx co prompt sessions <<<' if co else END
    shell = 'co_shell.sh' if co else 'codex_shell.sh'
    bashrc = Path(bashrc).expanduser().absolute()
    if bashrc.is_symlink() or any(parent.is_symlink() for parent in bashrc.parents):
        raise ValueError('Bash configuration must not be a symlink')
    original = bashrc.read_bytes() if bashrc.exists() else b''
    block = (begin + '\n' + '. ' + shlex.quote(str(ROOT / 'analysis/scripts' / shell)) +
             '\n' + end + '\n').encode()
    if original.count(begin.encode()) != original.count(end.encode()) or original.count(begin.encode()) > 1:
        raise ValueError('Existing chx shell marker needs explicit repair; no automatic rewrite')
    if begin.encode() in original:
        start = original.index(begin.encode())
        stop = original.index(end.encode(), start) + len(end)
        while stop < len(original) and original[stop:stop + 1] == b'\n':
            stop += 1
        candidate = original[:start] + block + original[stop:]
    else:
        name = b'co' if co else b'codex'
        if re.search(rb'(?m)^\s*(alias\s+' + name + rb'\b|(?:function\s+)?' + name + rb'\s*\(\))', original):
            raise ValueError('Existing ' + name.decode() + ' customization found; preserve it and review before installing')
        candidate = original + (b'\n' if original and not original.endswith(b'\n') else b'') + b'\n' + block
    if candidate != original:
        save_backup(bashrc, original)
        temporary = bashrc.with_name('.' + bashrc.name + '.' + uuid.uuid4().hex + '.tmp')
        try:
            with os.fdopen(os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as stream:
                stream.write(candidate)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.chmod(stat.S_IMODE(bashrc.stat().st_mode) if bashrc.exists() else 0o644)
            subprocess.run(['bash', '-n', str(temporary)], check=True, capture_output=True)
            os.replace(str(temporary), str(bashrc))
        finally:
            if temporary.exists():
                temporary.unlink()
    return {'status': 'installed', 'bashrc': str(bashrc), 'project': str(ROOT),
            'source': str(ROOT / 'analysis/scripts' / shell)}


def route(args, executable, cwd=None, project_prompt=False):
    cwd = Path(cwd or Path.cwd()).resolve()
    binary = Path(executable).resolve()
    if not binary.is_file() or not os.access(str(binary), os.X_OK):
        raise ValueError('Original Codex executable is not available')
    selected, native = split_arguments(args)
    inside = cwd == ROOT or ROOT in cwd.parents
    option_args = native[:native.index('--')] if '--' in native else native
    readonly = any(value in {'-h', '--help', '-V', '--version'} for value in option_args)
    command = first_positional(native)
    non_agent = command in NON_AGENT
    if (inside and resume_command(native) and
            not any([selected['employee'], selected['task'], selected['scopes']])):
        # Native history is a core CLI feature; do not force old sessions into a new employee.
        return subprocess.run([str(binary), *native], cwd=cwd).returncode
    if not inside or readonly or non_agent:
        if any([selected['employee'], selected['task'], selected['scopes']]):
            raise ValueError('Employee selectors only apply to agent launches in this project')
        return subprocess.run([str(binary), *native], cwd=cwd).returncode
    validate_launch(native)
    outputs = output_paths(native)
    if command in NON_LOCAL:
        raise ValueError('This command is outside managed employee launch; use the original executable explicitly')
    if selected['employee']:
        employee = coordinator.identifier(selected['employee'])
        record = coordinator.read_state(ROOT)['employees'].get(employee)
        if record:
            if selected['task'] and selected['task'] != record['task']:
                raise ValueError('Existing employee belongs to another task; use assign explicitly')
            if selected['scopes'] and sorted(set(selected['scopes'])) != record['scopes']:
                raise ValueError('Existing employee scope differs; use assign explicitly')
            if record['status'] == 'creating':
                record = coordinator.create(ROOT, record['task'], employee, record['scopes'])
        else:
            if resume_command(native):
                raise ValueError('Resume/fork needs an already registered employee, not a newly created ID')
            task = selected['task'] or employee
            record = coordinator.create(ROOT, task, employee, selected['scopes'] or coordinator.DEFAULT_SCOPES)
    else:
        record = None
        for parent in [cwd, *cwd.parents]:
            if (parent / '.omx/employee.json').is_file():
                project, record = coordinator.member(parent)
                if project != ROOT:
                    raise ValueError('Employee belongs to another project')
                break
        if record and (selected['task'] or selected['scopes']):
            raise ValueError('Reassign an existing employee explicitly before starting')
        if not record:
            if resume_command(native):
                raise ValueError('Resume/fork requires --chx-employee <existing-id>; old root sessions are not automatically isolated')
            employee = 'cli-' + uuid.uuid4().hex[:16]
            record = coordinator.create(ROOT, selected['task'] or employee, employee,
                                        selected['scopes'] or coordinator.DEFAULT_SCOPES)
    print('chx employee: ' + record['employee'] + '\nworkspace: ' + record['workspace'], file=sys.stderr)
    workspace = Path(record['workspace'])
    for output in outputs:
        target = workspace / output
        if workspace not in target.resolve().parents or any(
                path.is_symlink() for path in [target, *target.parents] if path != workspace):
            raise ValueError('CLI output path escapes the employee workspace: ' + output)
    # Review subcommands have their own argument grammar, not an initial text prompt.
    position = positional_index(native)
    review = command == 'review' or (command in {'exec', 'e'} and
                                    first_positional(native[position + 1:]) == 'review')
    # Only new co sessions receive the profile; history keeps the original prompt.
    previous = os.environ.pop('CHX_CO_PROMPT_SHA256', None)
    try:
        if project_prompt and not resume_command(native) and not review:
            prefix, digest = codex_prompt.build(workspace)
            native = codex_prompt.inject(native, prefix, positional_index, VALUE_OPTIONS)
            os.environ['CHX_CO_PROMPT_SHA256'] = digest
        return coordinator.launch(ROOT, record['employee'], cli_args=native, executable=str(binary))
    finally:
        os.environ.pop('CHX_CO_PROMPT_SHA256', None)
        if previous is not None:
            os.environ['CHX_CO_PROMPT_SHA256'] = previous


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable')
    parser.add_argument('--install-shell', action='store_true')
    parser.add_argument('--install-co-shell', action='store_true')
    parser.add_argument('--project-prompt', action='store_true')
    parser.add_argument('--bashrc', default=str(Path.home() / '.bashrc'))
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.install_shell or args.install_co_shell:
        print(json.dumps(install_shell(args.bashrc, co=args.install_co_shell), ensure_ascii=False))
    else:
        native = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
        binary = args.executable or shutil.which('codex')
        if not binary:
            raise ValueError('Original Codex executable not found')
        raise SystemExit(route(native, binary, project_prompt=args.project_prompt))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
