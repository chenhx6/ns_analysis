#!/usr/bin/env python3
"""Create a local annotated delivery tag only for a prepared, verified commit tree."""
import argparse
import hashlib
import json
import os
import tempfile
import fcntl
from contextlib import contextmanager
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PENDING = ROOT / ".omx/delivery/pending.json"


def git_environment():
    routing = {'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
               'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_PREFIX'}
    return {key: value for key, value in os.environ.items() if key not in routing}


def git_command(*args):
    probe = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--absolute-git-dir'],
                           env=git_environment(), text=True, capture_output=True)
    if probe.returncode == 0:
        metadata = Path(probe.stdout.strip())
    else:
        metadata = ROOT / '.project-git'
        subprocess.run(['git', '--git-dir=' + str(metadata), 'rev-parse', '--git-dir'],
                       env=git_environment(), check=True, capture_output=True)
    return ['git', '--git-dir=' + str(metadata), '--work-tree=' + str(ROOT), *args]


def git(*args):
    return subprocess.check_output(git_command(*args), cwd=ROOT, env=git_environment(), text=True).strip()


def atomic_json(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def pending_lock():
    PENDING.parent.mkdir(parents=True, exist_ok=True)
    with (PENDING.parent / 'pending.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def evidence(path):
    absolute = (ROOT / path).resolve()
    absolute.relative_to(ROOT / "analysis")
    data = absolute.read_bytes()
    document = json.loads(data)
    checks = document.get("checks", [])
    if document.get("status") != "passed" or not checks or any(
        check.get("returncode") != 0 for check in checks
    ):
        raise ValueError("Delivery evidence must contain passing checks")
    return absolute.relative_to(ROOT).as_posix(), hashlib.sha256(data).hexdigest()


def tag_name(author, task, head):
    parts = [re.sub(r'[^\w-]+', '-', value).strip('-_') for value in (author, task)]
    if any(not value or len(value) > 40 for value in parts):
        raise ValueError('Use a short, meaningful author and task description for the tag')
    base = '-'.join(parts)
    name, number = base, 1
    while subprocess.run(git_command('rev-parse', '--verify', 'refs/tags/'+name),
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=git_environment()).returncode == 0:
        if git('cat-file', '-t', name) == 'tag' and git('rev-parse', name+'^{}') == head:
            return name
        number += 1
        name = base+'-'+str(number)
    subprocess.check_call(git_command('check-ref-format', 'refs/tags/'+name), env=git_environment())
    return name


def create_tag(head, task, result, basis, executor, verification):
    if any(not value.strip() or '\n' in value or '\r' in value for value in (task, result, basis, executor)):
        raise ValueError('Tag change, outcome, basis and executor must be nonempty single-line descriptions')
    author = git('show', '-s', '--format=%an', head)
    name = tag_name(author, task, head)
    message = '修改者：{}\n执行协作：{}\n基于：{}\n改动：{}\n成果：{}\n验证：{}\n'.format(
        author, executor, basis, task, result, verification)
    if subprocess.run(git_command('rev-parse', '--verify', 'refs/tags/'+name),
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=git_environment()).returncode == 0:
        if git('for-each-ref', '--format=%(contents)', 'refs/tags/'+name).strip() != message.strip():
            raise ValueError('Existing tag has a different description; use a distinct task title')
    else:
        git('tag', '-a', name, head, '-m', message)
    return name


def prepare(task, evidence_file, result, basis='用户任务与现有项目内容', executor='Codex', files=None):
    if not result.strip():
        raise ValueError('A real outcome description is required')
    path, digest = evidence(evidence_file)
    if git("diff", "--name-only", *(["--", *[":(literal)" + name for name in files]] if files is not None else [])):
        raise ValueError("Stage task changes before preparing delivery")
    indexed = subprocess.check_output(git_command('show', ':' + path), env=git_environment())
    if hashlib.sha256(indexed).hexdigest() != digest:
        raise ValueError('Staged evidence does not match the verified file')
    document = {"task": task, "tree": git("write-tree"), "evidence": path,
                "evidence_sha256": digest, 'result':result, 'basis':basis, 'executor':executor}
    if files is not None:
        document['files'] = sorted(files)
    with pending_lock():
        if PENDING.exists() and json.loads(PENDING.read_text()) != document:
            raise ValueError('Another outstanding delivery is already prepared')
        atomic_json(PENDING, document)
    print("Prepared verified task delivery for the staged tree")


def finalize():
    with pending_lock():
        _finalize()


def _finalize():
    if not PENDING.exists():
        return
    document = json.loads(PENDING.read_text())
    if git("rev-parse", "HEAD^{tree}") != document["tree"]:
        raise ValueError("Committed tree does not match the prepared task")
    scope = ["--", *[":(literal)" + name for name in document["files"]]] if "files" in document else []
    if git("diff", "--name-only", *scope) or git("diff", "--cached", "--name-only"):
        raise ValueError("Tracked task files changed after delivery was prepared")
    path, digest = evidence(document["evidence"])
    if digest != document["evidence_sha256"]:
        raise ValueError("Evidence changed after delivery was prepared")
    head = git("rev-parse", "HEAD")
    if git("show", "HEAD:" + path) != (ROOT / path).read_text().strip():
        raise ValueError("Committed evidence does not match the verified file")
    count = len(json.loads((ROOT/path).read_text())['checks'])
    tag = create_tag(head, document['task'], document['result'], document['basis'], document['executor'],
                     '{}项检查通过；记录：{}'.format(count, path))
    receipt = PENDING.parent/'tag_receipt.json'
    atomic_json(receipt, {'head':head, 'tag':tag})
    PENDING.unlink()
    print("Verified delivery tag: " + tag)


def main():
    global ROOT, PENDING
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Explicit repository workspace; does not grant filesystem authority")
    parser.add_argument("action", choices=["prepare", "finalize"])
    parser.add_argument("--task")
    parser.add_argument("--evidence")
    parser.add_argument('--result')
    parser.add_argument('--basis', default='用户任务与现有项目内容')
    parser.add_argument('--executor', default='Codex')
    args = parser.parse_args()
    if args.root is not None:
        if not args.root.is_absolute() or not args.root.is_dir():
            parser.error('--root must be an existing absolute repository directory')
        ROOT = args.root.resolve()
        PENDING = ROOT / '.omx/delivery/pending.json'
    if args.action == "prepare":
        if not args.task or not args.evidence or not args.result:
            parser.error('prepare requires --task, --evidence and --result')
        prepare(args.task, args.evidence, args.result, args.basis, args.executor)
    else:
        finalize()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print("Delivery tag deferred: " + str(error), file=sys.stderr)
        sys.exit(1)
