# G004 bounded adversarial QA

Status: final scoped QA complete; 27 commands, 48 assertions, 24 engineering and 73 numerical checks passed. See report.md and verification.json. Parent authorized employee freeze after final schema rerun; awaiting collection after submission.

Authority: main process plan and delegated G004 QA; writes confined to this directory and temporary synthetic fixtures. No real event inputs or holdouts are opened. Implementation checkout is read-only.

Run `python3 analysis/20261008-time-offset-qa/qa.py --source <implementation-checkout> --cc-sha256 <hash> --hh-sha256 <hash>`.

| Scenario | Intent / model | Setup and command | Expected signal | Actual / evidence | Cleanup |
|---|---|---|---|---|---|
| baseline | ordinary user | compile; --self-test; --verify-artifacts | compile and numerical checks pass | passed; verification.json | temporary directory removed |
| malformed CLI/input | accidental corruption | missing/duplicate flags, invalid ROOT, malformed manifest | nonzero exit; no false completion | passed; report.md / verification.json | same |
| malformed ledger | damaged prior state | bad row before valid consumed row, truncated line | verifier and validation reject before consumption | passed; report.md / verification.json | restore bytes |
| linked report | mistaken output alias | symlink/hardlink completion.json to sentinel | rejection and sentinel unchanged | passed; report.md / verification.json | same |
| partial output/retry | interrupted prior operation | existing partial validation output; repeated synthetic holdout | reject overwrite/reuse | passed; report.md / verification.json | same |
| stale/tampered result | edited candidate/state | modify frozen digest and offsets CSV | reject; restored fixture passes | passed; report.md / verification.json | restore bytes |
| fake success | misleading metadata | synthetic calibrated fixture and fake completion text | strict mission fails with nonzero status | passed; report.md / verification.json | same |
| scientific algorithm | slow drift/double peaks | source self-tests with chronology and distinct physical candidates | named regression evidence; no real data | passed; report.md / verification.json | same |

Each subprocess has a finite timeout. JSON records exact argv, exit, output, source hashes and assertion outcomes. Existing self-test C++ generates scientific synthetic fixtures; Python only orchestrates. No fits or scientific statistics are implemented in Python. Final success requires all assertions and stable source hashes. Production fixes are handed to implementation owner; this lane never changes production code. Workflow state is owned by parent.

Final follow-up: rerun all probes at cc efff88f30da1362969a3f70222572af9ad4a23e50829a340938557c72b1f9941; require 73 numerical tests and independently parse failed-mission JSON containing quote, backslash, tab, CR and LF. Retain prior ccc6 result as verification-ccc6.json.
