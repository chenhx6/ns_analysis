"""Compose the co initial prompt from the selected employee's project files."""
import hashlib
import json
from pathlib import Path


def build(workspace):
    """Read the profile verbatim and list paths as JSON data, never shell code."""
    workspace = Path(workspace).resolve()
    raw = (workspace / 'analysis/scripts/agent-prompt.txt').read_bytes()
    profile = raw.decode('utf-8').rstrip()
    if not profile.strip():
        raise ValueError('co project profile is empty: ' + str(workspace / 'analysis/scripts/agent-prompt.txt'))
    skills = {}
    # Prefer the maintenance source when both native skill entry points exist.
    for directory in ('.agents/skills', '.codex/skills'):
        for path in sorted((workspace / directory).glob('*/SKILL.md')):
            skills.setdefault(path.parent.name, str(path))
    configs = [str(workspace / name) for name in
               ('AGENTS.md', '.codex/config.toml', '.codex/hooks.json')
               if (workspace / name).is_file()]
    context = {'workspace': str(workspace), 'skill_paths': list(skills.values()),
               'configuration_paths': configs,
               'native_skill_entry': str(workspace / '.codex/skills')}
    prefix = profile + '\n\n项目路径清单（JSON 数据，按任务读取）：\n'
    return prefix + json.dumps(context, ensure_ascii=False, indent=2), hashlib.sha256(raw).hexdigest()


def inject(args, prefix, positional_index, value_options):
    """Replace the initial prompt only; keep option values and literal -- intact."""
    args = list(args)
    start = positional_index(args)
    start = start + 1 if start is not None and args[start] in {'exec', 'e'} else 0
    index = start
    while index < len(args):
        value = args[index]
        if value == '--':
            index += 1
            break
        if value == '-' or not value.startswith('-'):
            break
        name, equal, _ = value.partition('=')
        index += 2 if name in value_options and not equal else 1
    if index < len(args):
        if args[index] == '-':
            raise ValueError('co prompt injection needs an explicit text prompt; use codex for stdin prompts')
        args[index] = prefix + '\n\n用户本次任务：\n' + args[index]
    else:
        if not args or args[-1] != '--':
            args.append('--')
        args.append(prefix)
    return args
