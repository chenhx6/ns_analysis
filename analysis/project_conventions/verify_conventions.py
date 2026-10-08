#!/usr/bin/env python3
"""Check the requested naming and live-notebook conventions."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    for name in ["AGENTS.md", "README.md", "analysis/plans/_template.md"]:
        content = (ROOT / name).read_text()
        assert "ASCII" in content and "YYYY-MM-DD-short-task-name.md" in content, name
    for name in ["AGENTS.md", "README.md"]:
        content = (ROOT / name).read_text()
        assert "analysis/experiment_log/record_analysis.md" in content and "实时" in content, name
    plans = ["2026-10-08-hook-failure-diagnosis.md", "2026-10-08-experiment-log-sync.md",
             "2026-10-08-english-names-live-notebook.md"]
    for name in plans:
        name.encode("ascii")
        assert (ROOT / "analysis/plans" / name).is_file(), name
    for name in ["2026-10-08-hook失败排查.md", "2026-10-08-实验记录同步.md"]:
        assert not (ROOT / "analysis/plans" / name).exists(), name
    for name in ["verify_record.py", "reports/sync_verification.json", "reports/pending_record.diff"]:
        assert not (ROOT / "analysis/experiment_log" / name).exists(), name
    report = {"status": "passed", "checks": [
        {"name": "English naming convention in rules, README and template", "returncode": 0},
        {"name": "User-authored live notebook convention recorded", "returncode": 0},
        {"name": "This session's plans use English filenames", "returncode": 0},
        {"name": "Unnecessary notebook review files removed", "returncode": 0},
    ]}
    output = Path(__file__).resolve().parent / "reports/verification.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("PASS: English paths, persisted conventions and scoped cleanup")


if __name__ == "__main__":
    main()
