#!/usr/bin/env python3
"""Reproduce Git discovery failure and verify the existing project entry point."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
ENV = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
ENV.update(GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0', LC_ALL='C')
GIT = ['git', '--git-dir=' + str(ROOT / '.project-git'), '--work-tree=' + str(ROOT)]


def run(command):
    result = subprocess.run(command, cwd=ROOT, env=ENV, capture_output=True,
                            text=True, timeout=60)
    return {'command': command, 'returncode': result.returncode,
            'stdout': result.stdout.strip(), 'stderr': result.stderr.strip()}


def main():
    # Check wrapper prerequisites so its status invocation does not initialize/configure Git.
    assert (ROOT / '.project-git/HEAD').is_file(), 'Existing repository HEAD is missing'
    assert run(GIT + ['config', '--get', 'core.hooksPath'])['stdout'] == str(ROOT / '.githooks')
    assert run(GIT + ['remote', 'get-url', 'origin'])['stdout'] == 'https://gitee.com/chx6/ns_analysis.git'
    entries = sorted(path.name for path in (ROOT / '.git').iterdir())
    assert entries == [], 'The .git directory is no longer empty; reassess the diagnosis'
    plain = run(['git', 'status', '-sb'])
    assert plain['returncode'] == 128 and 'not a git repository' in plain['stderr']
    top = run(GIT + ['rev-parse', '--show-toplevel'])
    assert top['returncode'] == 0 and top['stdout'] == str(ROOT)
    status = run(['bash', 'analysis/scripts/project_git.sh', 'status', '-sb'])
    assert status['returncode'] == 0 and status['stdout'].startswith('## ')
    report = {
        'status': 'passed',
        'scope': 'Read-only Git diagnosis; only the verification report is generated',
        'cwd': str(ROOT),
        'environment': 'Git overrides removed; GIT_OPTIONAL_LOCKS=0; LC_ALL=C',
        'git_directory_entries': entries,
        'metadata_directory': str(ROOT / '.project-git'),
        'expected_failure': plain,
        'checks': [top, status],
        'conclusion': '普通 Git 找不到有效的 .git；已有项目入口显式选择 .project-git，能够读取仓库状态。',
        'historical_basis': 'analysis/project_maintenance/reports/project_setup.md:13 记录受保护的 .git 不可写，因而使用 .project-git；本次没有修改权限。',
    }
    output = Path(__file__).resolve().parent / 'reports/verification.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
