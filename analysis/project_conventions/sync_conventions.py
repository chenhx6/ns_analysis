#!/usr/bin/env python3
"""Deliver this task in an isolated clone, preserving concurrent working edits."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
FILES = [
    "AGENTS.md", "README.md", "analysis/plans/_template.md",
    "analysis/plans/2026-10-08-hook-failure-diagnosis.md",
    "analysis/plans/2026-10-08-experiment-log-sync.md",
    "analysis/plans/2026-10-08-english-names-live-notebook.md",
    "analysis/project_conventions/verify_conventions.py",
    "analysis/project_conventions/sync_conventions.py",
    "analysis/project_conventions/reports/verification.json",
]
OLD_PLAN = "analysis/plans/2026-10-08-hook失败排查.md"


def main():
    primary = ["bash", str(ROOT / "analysis/scripts/project_git.sh")]
    clone = ROOT / ".omx/delivery/conventions-clone"
    assert not clone.is_symlink(), "Delivery clone must not be a symlink"
    clone.parent.mkdir(parents=True, exist_ok=True)
    if not clone.exists():
        subprocess.run(["git", "clone", "--no-hardlinks", "--quiet", str(ROOT / ".project-git"), str(clone)], check=True)
    assert (clone / ".git/HEAD").is_file(), "Delivery clone has no Git metadata"
    git = ["git", "-C", str(clone)]
    subprocess.run(git + ["remote", "set-url", "origin", "https://gitee.com/chx6/ns_analysis.git"], check=True)
    subprocess.run(git + ["fetch", "origin"], check=True)
    subprocess.run(git + ["merge", "--ff-only", "origin/main"], check=True)
    for key in ["user.name", "user.email", "credential.helper"]:
        value = subprocess.check_output(primary + ["config", "--get", key], cwd=ROOT, text=True).strip()
        subprocess.run(git + ["config", key, value], check=True)
    for name in FILES:
        source, destination = ROOT / name, clone / name
        assert source.is_file() and not source.is_symlink(), name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    old = clone / OLD_PLAN
    if old.exists():
        old.unlink()
    subprocess.run([
        sys.executable, str(clone / "analysis/scripts/project_sync.py"), "sync",
        "--task", "命名与记录约定", "--message", "Record English path names and preserve the live notebook",
        "--result", "记下英文文件目录命名和用户实时记录本约定，迁移本会话计划英文路径，移除多余专项审查文件",
        "--basis", "用户明确要求英文命名，并说明record_analysis.md由本人实时编辑、无需过于关注",
        "--evidence", "analysis/project_conventions/reports/verification.json",
    ], cwd=clone, check=True, env=dict(os.environ, GIT_TERMINAL_PROMPT="0",
                                     GIT_ASKPASS="/bin/false", SSH_ASKPASS="/bin/false"))
    receipt = clone / ".omx/delivery/sync_receipt.json"
    destination = ROOT / ".omx/delivery/conventions_sync_receipt.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(receipt, destination)
    subprocess.run(primary + ["fetch", "origin"], cwd=ROOT, check=True)
    tracked_old = subprocess.run(primary + ["ls-files", "--error-unmatch", OLD_PLAN], cwd=ROOT,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    subprocess.run(primary + ["add", "--", *FILES, *([OLD_PLAN] if tracked_old else [])], cwd=ROOT, check=True)
    subprocess.run(primary + ["merge", "--ff-only", "origin/main"], cwd=ROOT, check=True)
    print("Task delivery pushed and fast-forwarded; concurrent notebook edits preserved")


if __name__ == "__main__":
    main()
