#!/usr/bin/env python3
"""Create a local annotated delivery tag only for a prepared, verified commit tree."""
import argparse
from datetime import datetime, timezone
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


def prepare(task, evidence_file):
    path, digest = evidence(evidence_file)
    if git("diff", "--name-only"):
        raise ValueError("Stage task changes before preparing delivery")
    if path not in git("diff", "--cached", "--name-only").splitlines():
        # Already committed evidence is also valid if its Git blob matches.
        subprocess.check_call(git_command("ls-files", "--error-unmatch", path), stdout=subprocess.DEVNULL)
    document = {"task": task, "tree": git("write-tree"), "evidence": path,
                "evidence_sha256": digest}
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
    slug = re.sub(r"[^a-z0-9._-]+", "-", document["task"].lower()).strip("-")[:48] or "task"
    stamp = datetime.fromtimestamp(int(git("show", "-s", "--format=%ct", head)), timezone.utc).strftime("%Y%m%d%H%M%S")
    tag = "t-%s-%s-%s" % (slug, stamp, head[:7])
    existing = subprocess.run(git_command("rev-parse", "--verify", "refs/tags/" + tag),
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    if existing:
        if git("cat-file", "-t", tag) != "tag" or git("rev-parse", tag + "^{}") != head:
            raise ValueError("Conflicting delivery tag")
    else:
        message = "任务交付：%s\n提交：%s\n验证：%s\n证据 SHA256：%s\n" % (document["task"], head, path, digest)
        git("tag", "-a", tag, head, "-m", message)
    PENDING.unlink()
    print("Verified delivery tag: " + tag)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "finalize"])
    parser.add_argument("--task")
    parser.add_argument("--evidence")
    args = parser.parse_args()
    if args.action == "prepare":
        if not args.task or not args.evidence:
            parser.error("prepare requires --task and --evidence")
        prepare(args.task, args.evidence)
    else:
        finalize()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print("Delivery tag deferred: " + str(error), file=sys.stderr)
        sys.exit(1)
