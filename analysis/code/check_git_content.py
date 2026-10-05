#!/usr/bin/env python3
"""Check Git objects without reading the large, untracked local datasets."""
import subprocess
import sys
from pathlib import PurePosixPath

MAX_BYTES = 25 * 1024 * 1024
ROOT_FILES = {"AGENTS.md", "README.md", ".gitignore", ".omx/setup-scope.json", ".omx/hud-config.json"}
DATA_SUFFIXES = {
    ".root", ".bin", ".h5", ".hdf5", ".npy", ".npz", ".parquet",
    ".arrow", ".zip", ".tar", ".gz", ".7z",
}
BUILD_SUFFIXES = {".pyc", ".o", ".so", ".a", ".exe"}
SOURCE_SUFFIXES = {".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".md", ".go", ".rs", ".sh"}
SOURCE_ENV_EXAMPLES = {"analysis/vendor/ponytail/.env.example"}
LOCAL_DIRS = {
    "__pycache__", ".pytest_cache", ".ipynb_checkpoints", ".venv", "venv",
    "node_modules", "build", "sessions", "logs",
}


def git(*args):
    return subprocess.check_output(["git", *args])


def permitted(path):
    p = PurePosixPath(path)
    allowed = (
        path in ROOT_FILES or p.parts[0] in {"analysis", ".githooks", ".codex"}
        or path.startswith(".agents/skills/")
    )
    name = p.name.lower()
    private = (
        name == ".env" or (name.startswith(".env.") and path not in SOURCE_ENV_EXAMPLES)
        or name.startswith("config.local.")
        or (name.startswith(("credentials", "secrets")) and p.suffix.lower() not in SOURCE_SUFFIXES)
        or name in {"auth.json", "history.jsonl"} or ".sqlite" in name
        or p.suffix.lower() in {".pem", ".key"}
    )
    generated = (
        p.suffix.lower() in DATA_SUFFIXES | BUILD_SUFFIXES
        or any(part in LOCAL_DIRS for part in p.parts)
        or path == "analysis/code/DecodeAndSortAll/decodeandsort" or name.endswith("~")
    )
    return allowed and not private and not generated


def index_entries():
    for record in git("ls-files", "--stage", "-z").split(b"\0"):
        if record:
            metadata, path = record.split(b"\t", 1)
            mode, oid, stage = metadata.split()
            if stage != b"0":
                raise ValueError("索引仍有未解决的冲突")
            yield mode, oid, path.decode("utf-8", "surrogateescape")


def push_entries():
    commits = set()
    for line in sys.stdin:
        _local_ref, local_oid, _remote_ref, remote_oid = line.split()
        if set(local_oid) == {"0"}:
            continue
        args = ["rev-list", local_oid]
        if set(remote_oid) != {"0"}:
            # An unknown remote object needs fetching before history can be checked.
            git("cat-file", "-e", remote_oid + "^{commit}")
            args.append("^" + remote_oid)
        commits.update(git(*args).decode().splitlines())
    for commit in sorted(commits):
        for record in git("ls-tree", "-r", "-z", commit).split(b"\0"):
            if record:
                metadata, path = record.split(b"\t", 1)
                mode, _kind, oid = metadata.split()
                yield mode, oid, path.decode("utf-8", "surrogateescape")


def main():
    entries = set(push_entries() if "--push" in sys.argv else index_entries())
    errors = []
    object_ids = sorted({oid for _, oid, _ in entries})
    sizes = {}
    if object_ids:
        output = subprocess.check_output(
            ["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
            input=b"\n".join(object_ids) + b"\n",
        )
        for line in output.splitlines():
            oid, kind, size = line.split()
            if kind == b"blob":
                sizes[oid] = int(size)
    for mode, oid, path in sorted(entries):
        if mode not in {b"100644", b"100755"}:
            errors.append(f"不允许符号链接、子模块等条目：{path}")
        elif not permitted(path):
            errors.append(f"不属于同步范围或为数据/本地文件：{path}")
        elif sizes.get(oid, MAX_BYTES + 1) > MAX_BYTES:
            errors.append(f"文件超过 25 MiB 或对象不可读：{path}")
    if errors:
        print("Git 内容检查未通过：", file=sys.stderr)
        for message in sorted(set(errors)):
            print("- " + message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f"Git 内容检查失败，请检查索引并获取远端历史：{exc}", file=sys.stderr)
        sys.exit(1)
