"""Check that processing documents are deliverable while data stay local."""
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "analysis/scripts"))
from check_git_content import permitted


def check():
    """Keep Git ignore rules and the content gate aligned for processing outputs."""
    accepted = [
        "decisions/20261008-time-offset.md", "decisions/20261008-time-offset-method.md",
        "analysis/plans/process/20261008-time-offset.md",
        "time_offset/find_time_offset.cpp", "time_offset/plot_time_offset.py",
        "time_offset/report.md", "time_offset/offsets.csv", "time_offset/channel_map.csv",
        "time_offset/configs/group_01/crate0.dat", "time_offset/configs/group_01/crate1.dat",
        "time_offset/figures/group_01.svg", "time_offset/verification.json",
        "time_offset/time_offset/time_offset.cc", "time_offset/time_offset/time_offset.hh",
        "time_offset/time_offset/Makefile", "time_offset/time_offset/time_offset_6015.csv",
        "time_offset/time_offset/verification.json", "time_offset/time_offset/run.sh",
    ]
    rejected = [
        "plans/process/raw.root", "decisions/raw.csv", "time_offset/time_offset.root",
        "time_offset/raw.bin", "time_offset/large.npy", "time_offset/decodeandsort",
        "time_offset/tool.o", "time_offset/__pycache__/helper.py", "time_offset/auth.json",
        "time_offset/secrets.json", "time_offset/.env", "time_offset/key.pem",
        "decode_data/data_C2_6015_6015_wave.root", "Ge/6015/data.bin", "CsI/6015/data.bin",
        "time_offset/time_offset/time_offset", "time_offset/time_offset/time_offset_6015.root",
        "time_offset/time_offset/credentials.json", "timeOffset/sample/test.cc",
    ]
    for path in accepted + rejected:
        expected = path in accepted
        assert permitted(path) == expected, path
        command = ["git", "--git-dir=" + str(PROJECT / ".project-git"),
                   "--work-tree=" + str(PROJECT), "check-ignore", "--no-index",
                   "--verbose", "--non-matching", "-z", "--stdin"]
        result = subprocess.run(command, input=path.encode() + b"\0", cwd=PROJECT,
                                stdout=subprocess.PIPE, check=False)
        assert result.returncode in (0, 1), (path, result.returncode)
        # Git 2.25 also reports matching negation rules; inspect the final rule.
        pattern = result.stdout.split(b"\0")[2]
        ignored = bool(pattern) and not pattern.startswith(b"!")
        assert ignored != expected, (path, pattern)
    print("Processing path checks passed: {} allowed, {} excluded".format(len(accepted), len(rejected)))


if __name__ == "__main__":
    check()
