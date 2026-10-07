#!/usr/bin/env python3
"""Create a local annotated delivery tag only for a prepared, verified commit tree."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PENDING = ROOT / ".omx/delivery/pending.json"


def git_command(*args):
    metadata = ROOT / (".git" if (ROOT / ".git/HEAD").is_file() else ".project-git")
    return [
        "git", "--git-dir=" + str(metadata), "--work-tree=" + str(ROOT), *args
    ]


def git(*args):
    return subprocess.check_output(git_command(*args), cwd=ROOT, text=True).strip()


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
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        if git('cat-file', '-t', name) == 'tag' and git('rev-parse', name+'^{}') == head:
            return name
        number += 1
        name = base+'-'+str(number)
    subprocess.check_call(git_command('check-ref-format', 'refs/tags/'+name))
    return name


def create_tag(head, task, result, basis, executor, verification):
    if any(not value.strip() or '\n' in value or '\r' in value for value in (task, result, basis, executor)):
        raise ValueError('Tag change, outcome, basis and executor must be nonempty single-line descriptions')
    author = git('show', '-s', '--format=%an', head)
    name = tag_name(author, task, head)
    message = '修改者：{}\n执行协作：{}\n基于：{}\n改动：{}\n成果：{}\n验证：{}\n'.format(
        author, executor, basis, task, result, verification)
    if subprocess.run(git_command('rev-parse', '--verify', 'refs/tags/'+name),
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        if git('for-each-ref', '--format=%(contents)', 'refs/tags/'+name).strip() != message.strip():
            raise ValueError('Existing tag has a different description; use a distinct task title')
    else:
        git('tag', '-a', name, head, '-m', message)
    return name


def prepare(task, evidence_file, result, basis='用户任务与现有项目内容', executor='Codex'):
    if not result.strip():
        raise ValueError('A real outcome description is required')
    path, digest = evidence(evidence_file)
    if git("diff", "--name-only"):
        raise ValueError("Stage task changes before preparing delivery")
    if path not in git("diff", "--cached", "--name-only").splitlines():
        # Already committed evidence is also valid if its Git blob matches.
        subprocess.check_call(git_command("ls-files", "--error-unmatch", path), stdout=subprocess.DEVNULL)
    document = {"task": task, "tree": git("write-tree"), "evidence": path,
                "evidence_sha256": digest, 'result':result, 'basis':basis, 'executor':executor}
    PENDING.parent.mkdir(parents=True, exist_ok=True)
    PENDING.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    print("Prepared verified task delivery for the staged tree")


def finalize():
    if not PENDING.exists():
        return
    document = json.loads(PENDING.read_text())
    if git("rev-parse", "HEAD^{tree}") != document["tree"]:
        raise ValueError("Committed tree does not match the prepared task")
    if git("diff", "--name-only") or git("diff", "--cached", "--name-only"):
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
    receipt.write_text(json.dumps({'head':head, 'tag':tag}, ensure_ascii=False, indent=2)+'\n')
    PENDING.unlink()
    print("Verified delivery tag: " + tag)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "finalize"])
    parser.add_argument("--task")
    parser.add_argument("--evidence")
    parser.add_argument('--result')
    parser.add_argument('--basis', default='用户任务与现有项目内容')
    parser.add_argument('--executor', default='Codex')
    args = parser.parse_args()
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
