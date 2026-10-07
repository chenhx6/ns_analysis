#!/usr/bin/env python3
"""Commit and push verified project changes; enforce delivery at native Stop."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from check_git_content import MAX_BYTES, permitted
import task_delivery

ROOT = Path(__file__).resolve().parents[2]
REMOTE = 'https://gitee.com/chx6/ns_analysis.git'


def git(*args, check=True):
    result = subprocess.run(['bash', str(ROOT/'analysis/scripts/project_git.sh'), *args],
                            cwd=ROOT, env=dict(os.environ, GIT_TERMINAL_PROMPT='0'),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if check and result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8', 'replace').strip())
    return result


def text(*args):
    return git(*args).stdout.decode('utf-8').strip()


def candidates():
    raw = git('ls-files', '-z', '--modified', '--deleted', '--others', '--exclude-standard').stdout
    paths = sorted(set(p.decode('utf-8', 'surrogateescape') for p in raw.split(b'\0') if p))
    for name in paths:
        path = ROOT/name
        if not permitted(name) or path.is_symlink():
            raise ValueError('File outside permitted delivery scope: ' + name)
        if path.exists():
            if ROOT not in path.resolve().parents or not path.is_file() or path.stat().st_size > MAX_BYTES:
                raise ValueError('Unsafe or oversized delivery file: ' + name)
    return paths


def sync(task, message, evidence, result=None, basis='用户任务与现有项目内容', executor='Codex'):
    if text('remote', 'get-url', '--push', '--all', 'origin').splitlines() != [REMOTE]:
        raise ValueError('origin push destination differs from the authorized project remote')
    if text('remote', 'get-url', '--all', 'origin').splitlines() != [REMOTE]:
        raise ValueError('origin fetch destination differs from the authorized project remote')
    branch = text('symbolic-ref', '--short', 'HEAD')
    task_delivery.evidence(evidence)
    git('fetch', 'origin')
    remote_ref = 'refs/remotes/origin/' + branch
    if git('rev-parse', '--verify', remote_ref, check=False).returncode == 0:
        if git('merge-base', '--is-ancestor', remote_ref, 'HEAD', check=False).returncode:
            raise ValueError('Remote history needs integration before delivery; refusing force push')
    paths = candidates()
    committed = False
    if paths:
        git('add', '--', *paths)
    staged = git('diff', '--cached', '--quiet', check=False)
    if staged.returncode not in (0, 1):
        raise RuntimeError('Unable to inspect staged changes: ' + staged.stderr.decode('utf-8', 'replace'))
    if staged.returncode == 1:
        # Preserve valid renderer spacing, CSV CRLF and user Markdown hard breaks.
        git('diff', '--cached', '--check', '--', '*.py', '*.sh', '*.js', '*.mjs', '*.json', '*.toml', '*.yaml', '*.yml')
        # Run the same object-level policy used by pre-commit, before tree preparation.
        policy_check = subprocess.run([sys.executable, str(ROOT/'analysis/scripts/check_git_content.py')],
                                cwd=ROOT, env=dict(os.environ, GIT_DIR=str(task_delivery.git_command()[1].split('=',1)[1]),
                                                  GIT_WORK_TREE=str(ROOT)), timeout=60)
        if policy_check.returncode:
            raise ValueError('Staged object validation failed')
        if not result:
            raise ValueError('Provide --result with the real achieved outcome for a readable delivery tag')
        task_delivery.prepare(task, evidence, result, basis, executor)
        commit_output = git('commit', '-m', message)
        print(commit_output.stdout.decode('utf-8'), end='')
        committed = True
        if task_delivery.PENDING.exists():
            raise ValueError('Post-commit delivery tag did not finalize; inspect the hook before pushing')
    head = text('rev-parse', 'HEAD')
    tag_receipt = task_delivery.PENDING.parent/'tag_receipt.json'
    delivery = json.loads(tag_receipt.read_text()) if tag_receipt.exists() else {}
    tags = [delivery['tag']] if delivery.get('head') == head else []
    if tags and (text('rev-parse', 'refs/tags/'+tags[0]+'^{}') != head
                 or text('cat-file', '-t', 'refs/tags/'+tags[0]) != 'tag'):
        raise ValueError('Delivery tag receipt does not match the current annotated tag')
    if committed and not tags:
        raise ValueError('Verified commit has no delivery tag; refusing incomplete delivery')
    git('push', '--set-upstream', 'origin', 'HEAD:refs/heads/' + branch,
        *['refs/tags/' + tag for tag in tags])
    remote_head = text('ls-remote', '--heads', 'origin', 'refs/heads/' + branch).split()
    if not remote_head or remote_head[0] != head:
        raise ValueError('Remote branch does not match local HEAD after push')
    if text('status', '--porcelain'):
        raise ValueError('Files changed during delivery; another verified sync is required')
    receipt = {'status': 'pushed', 'head': head, 'branch': branch, 'remote': REMOTE, 'tags': tags}
    path = ROOT/'.omx/delivery/sync_receipt.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(receipt, ensure_ascii=False))
    return receipt


def stop_status(payload):
    if payload.get('hook_event_name') != 'Stop':
        return {}
    cwd = Path(payload.get('cwd', str(ROOT))).resolve()
    if cwd != ROOT and ROOT not in cwd.parents:
        return {}
    try:
        dirty = bool(text('status', '--porcelain'))
        head = text('rev-parse', 'HEAD')
        upstream = git('rev-parse', '@{upstream}', check=False)
        unpushed = upstream.returncode != 0 or upstream.stdout.decode().strip() != head
        if not dirty and not unpushed:
            return {}
        reason = ('项目自动交付未完成：' + ('存在未提交文件；' if dirty else '')
                  + ('本地 HEAD 与上游引用不一致；' if unpushed else '')
                  + '按 task-tag 技能验证后运行 project_sync.py sync，完成 commit/push。'
                  + '网络、认证或宿主审批阻碍时如实报告，不声称同步成功。')
    except Exception as exc:
        reason = '项目自动交付检查失败：' + str(exc)
    # One continuation request; a real external blocker must remain reportable.
    return {} if payload.get('stop_hook_active') else {'decision': 'block', 'reason': reason}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    command = sub.add_parser('sync')
    command.add_argument('--task', required=True)
    command.add_argument('--message', required=True)
    command.add_argument('--evidence', required=True)
    command.add_argument('--result')
    command.add_argument('--basis', default='用户任务与现有项目内容')
    command.add_argument('--executor', default='Codex')
    sub.add_parser('hook')
    args = parser.parse_args()
    if args.action == 'hook':
        raw = sys.stdin.read(1024*1024+1)
        if len(raw) > 1024*1024:
            raise ValueError('Hook input exceeds 1 MiB')
        print(json.dumps(stop_status(json.loads(raw or '{}')), ensure_ascii=False))
    else:
        sync(args.task, args.message, args.evidence, args.result, args.basis, args.executor)


if __name__ == '__main__':
    main()
