#!/usr/bin/env python3
"""Read-only audit of run/ROOT and time-offset candidate coverage."""
import csv
import json
import re
from collections import Counter
from pathlib import Path

import ROOT

ROOT.gROOT.SetBatch(True)
ROOT.TH1.AddDirectory(False)
PROJECT = Path(__file__).resolve().parents[2]
OUTPUT = PROJECT / "analysis/20261013-time-offset-readiness/verification.json"

run_log = list(csv.DictReader((PROJECT / "run_log/runs.csv").open(encoding="utf-8-sig", newline="")))
series = [row for row in run_log if 6015 <= int(row["run_id"]) <= 6079]
decode_files = sorted((PROJECT / "decode_data").glob("data_C2_*_wave.root"))
tree_counts = {}
for path in decode_files:
    match = re.search(r"data_C2_(\d+)_\d+_wave\.root$", path.name)
    if not match:
        raise ValueError(f"Unexpected decoded ROOT name: {path.name}")
    root_file = ROOT.TFile.Open(str(path), "READ")
    if not root_file or root_file.IsZombie():
        raise OSError(f"Cannot read ROOT metadata: {path}")
    tree = root_file.Get("tree")
    if not tree:
        raise ValueError(f"Missing tree: {path}")
    tree_counts[int(match.group(1))] = {
        "entries": int(tree.GetEntries()),
        "cycle": int(root_file.GetKey("tree").GetCycle()),
    }
    root_file.Close()

sources = list(csv.DictReader((PROJECT / "time_offset/final-candidates/sources.csv").open(newline="")))
groups = {}
for name in "ABC":
    coverage = json.loads((PROJECT / f"time_offset/final-candidates/group_{name}/coverage.json").read_text())
    rows = [row for row in sources if row["group"] == name]
    offset_rows = list(csv.DictReader((PROJECT / f"time_offset/final-candidates/group_{name}/offsets.csv").open(newline="")))
    training = [int(row["ge_run"]) for row in rows if row["phase"] == "training"]
    validation = [int(row["ge_run"]) for row in rows if row["phase"] == "validation"]
    groups[name] = {
        "training_runs": training,
        "validation_runs": validation,
        "calibrated_group_channel_rows": int(coverage["calibrated_count"]),
        "calibrated_by_crate_id": {
            cid: sum(row["cid"] == cid and row["status"] == "calibrated" for row in offset_rows)
            for cid in ("0", "1")
        },
        "observed_template_rows": int(coverage["observed_template_count"]),
        "uncalibrated_observed_rows": int(coverage["unknown_observed_count"]),
        "unobserved_template_rows": int(coverage["unobserved_count"]),
        "status": coverage["status"],
        "C_grid_slices": {
            str(row["ge_run"]): {
                "valid": int(row["valid_slice_count"]),
                "invalid": int(row["invalid_slice_count"]),
                "entry_range": [int(row["read_begin"]), int(row["read_end"])],
            }
            for row in rows
            if row["group"] == "C"
        },
    }

decoded_runs = set(tree_counts)
series_runs = {int(row["run_id"]) for row in series}
used_runs = {int(row["ge_run"]) for row in sources}
group_crates = {}
for name in "ABC":
    group_crates[name] = {
        crate: len((PROJECT / f"time_offset/final-candidates/group_{name}/crate{crate}.dat").read_text().splitlines())
        for crate in (0, 1)
    }

checks = [
    {"name": "run_log_series", "returncode": 0 if len(series) == 63 else 1,
     "runs": len(series), "end_status_counts": dict(Counter(row["end_status"] for row in series))},
    {"name": "decoded_ROOT_metadata", "returncode": 0 if len(tree_counts) == 14 and all(v["entries"] >= 12_000_000 for v in tree_counts.values()) else 1,
     "files": len(tree_counts), "tree_entries": tree_counts},
    {"name": "candidate_group_templates_and_validation", "returncode": 0 if len(used_runs) == 12 and all(v["status"] == "partial_usable" and set(v["validation_runs"]).issubset(decoded_runs) for v in groups.values()) else 1,
     "used_runs": sorted(used_runs), "decoded_but_unvalidated": sorted(decoded_runs - used_runs),
     "run_log_without_decoded_ROOT": sorted(series_runs - decoded_runs),
     "groups": groups, "crate_template_line_counts_including_header": group_crates},
]

result = {
    "status": "passed" if all(check["returncode"] == 0 for check in checks) else "failed",
    "checks": checks,
    "assessment": {
        "group_crates_exist_for_decoder_input": True,
        "all_planned_run_ids_and_channels_demonstrated_time_aligned": False,
        "reason": "Only 12 of 14 existing decoded ROOT runs enter v2 training/validation; 49 run_log IDs have no current decoded ROOT; each group retains uncalibrated/unobserved template rows.",
        "no_decoder_was_run": True,
    },
}
OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
if result["status"] != "passed":
    raise SystemExit(1)
print(json.dumps({"status": result["status"], "run_log_ids": len(series),
                  "decoded_ROOTs": len(tree_counts), "v2_used_runs": len(used_runs),
                  "decoded_but_unvalidated": sorted(decoded_runs - used_runs),
                  "run_log_without_ROOT": len(series_runs - decoded_runs)}, ensure_ascii=False))
