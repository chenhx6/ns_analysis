#!/usr/bin/env python3
"""Inspect hook definitions and time their read-only Git prerequisites."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
REPORT = Path(__file__).parent / "reports" / "verification.json"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcript", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads((ROOT / ".codex/hooks.json").read_text())
    hooks = []
    for event, groups in config["hooks"].items():
        for group_index, group in enumerate(groups):
            for handler_index, handler in enumerate(group["hooks"]):
                words = shlex.split(handler["command"])
                executable = next(word for word in words if "=" not in word)
                scripts = [word for word in words if word.endswith((".js", ".mjs", ".py"))]
                hooks.append({
                    "event": event, "group": group_index, "handler": handler_index,
                    "timeout_seconds": handler.get("timeout"), "executable": executable,
                    "interpreter_available": shutil.which(executable) is not None,
                    "scripts": [{"path": path, "exists": Path(path).is_file()} for path in scripts],
                })
    assert hooks and all(hook["interpreter_available"] for hook in hooks)
    assert all(script["exists"] for hook in hooks for script in hook["scripts"])
    checks = [{"name": "Registered hook interpreters and entrypoints exist", "returncode": 0}]
    commands = [
        ["status", "--porcelain"], ["rev-parse", "HEAD"], ["rev-parse", "@{upstream}"],
    ]
    git_prefix = ["git", "--git-dir=" + str(ROOT / ".project-git"), "--work-tree=" + str(ROOT)]
    timings = []
    for arguments in commands:
        start = time.monotonic()
        result = subprocess.run(git_prefix + arguments, cwd=ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=60)
        elapsed = time.monotonic() - start
        assert result.returncode == 0, "Read-only Git prerequisite failed: " + " ".join(arguments)
        timings.append({"arguments": arguments, "seconds": round(elapsed, 3),
                        "returncode": result.returncode})
    checks.append({"name": "Read-only Git prerequisites completed", "returncode": 0})
    greeting = False
    last_output = None
    interval = None
    with args.transcript.open() as source:
        for line_number, line in enumerate(source, 1):
            record = json.loads(line)
            payload = record.get("payload", {})
            if record.get("type") == "response_item" and payload.get("role") == "user":
                greeting = any(part.get("text", "").strip() == "hi" for part in payload.get("content", []))
            if not greeting:
                continue
            if record.get("type") == "event_msg" and payload.get("type") == "token_count":
                last_output = {"timestamp": record["timestamp"], "line": line_number}
            if payload.get("type") == "task_complete" and last_output:
                end = datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
                start = datetime.fromisoformat(last_output["timestamp"].replace("Z", "+00:00"))
                interval = {"source": str(args.transcript), "last_token_count": last_output,
                            "task_complete": {"timestamp": record["timestamp"], "line": line_number},
                            "seconds": round((end - start).total_seconds(), 3)}
                break
    assert interval is not None, "Greeting completion interval is missing from the input transcript"
    checks.append({"name": "Greeting completion delay extracted from actual transcript", "returncode": 0})
    report = {
        "status": "passed", "scope": "Diagnostic collection only; hook success is not certified",
        "checks": checks, "hooks": hooks, "git_timings": timings, "greeting_completion_interval": interval,
        "limits": ["No hook replay or trust/configuration change", "Timing is a current probe, not historical stderr"],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"hooks": len(hooks), "git_timings": timings, "greeting_completion_interval": interval}, ensure_ascii=False))


if __name__ == "__main__":
    main()
