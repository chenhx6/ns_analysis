#!/usr/bin/env python3
"""Capture, migrate and verify the approved project layout; never read raw data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "analysis/project_maintenance/reports"
BASELINE = REPORTS / "layout_baseline.json"
TOOLS = ["project_git.sh", "project_runtime.py", "check_git_content.py", "task_delivery.py",
         "bootstrap_project_tools.py", "verify_project_tools.py", "skill-routing-hook.mjs"]
RECORDS = ["redundancy_audit.md", "skills_cleanup.md", "skills_cleanup_verification.json",
           "decoder_files_preservation_verification.json"]
DECODER_FILES = ["Makefile", "UserDefine.hh", "crate.dat", "crate0.dat", "crate1.dat",
                 "crate2.dat", "crate3.dat", "decoder.cc", "decoder.hh", "main.cc",
                 "r2root.cc", "r2root.hh", "run.sh", "test.cc"]
SKILLS = ["chx-data-analysis", "crawl4ai", "go-on", "task-tag"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def command(argv, data=None):
    result = subprocess.run(argv, input=data, cwd=ROOT, text=True, capture_output=True, timeout=60)
    if result.returncode:
        raise RuntimeError(str(argv) + ": " + result.stderr)
    return result.stdout


def moves():
    pairs = [("analysis/code/" + name, "analysis/scripts/" + name) for name in TOOLS]
    pairs += [("analysis/records/" + name, "analysis/project_maintenance/reports/" + name)
              for name in RECORDS]
    pairs += [("analysis/project_setup.md", "analysis/project_maintenance/reports/project_setup.md"),
              ("analysis/record_analysis.md", "analysis/experiment_log/record_analysis.md")]
    pairs += [(str(path.relative_to(ROOT)), "analysis/experiment_log/figures/" + path.name)
              for path in sorted((ROOT / "analysis/analysis_figure/record_analysis").iterdir())]
    return pairs


def check_hook(base):
    hook = ROOT / base / "skill-routing-hook.mjs"
    for event in ["SessionStart", "UserPromptSubmit"]:
        output = command(["node", str(hook)], json.dumps({"hook_event_name": event, "cwd": str(ROOT)}))
        context = json.loads(output)["hookSpecificOutput"]["additionalContext"]
        assert "analysis/plans/" in context and "SVG" in context
    assert not command(["node", str(hook)], json.dumps({"hook_event_name": "Stop", "cwd": str(ROOT)}))
    assert not command(["node", str(hook)], json.dumps({"hook_event_name": "SessionStart", "cwd": "/tmp"}))


def capture():
    if BASELINE.exists():
        raise RuntimeError("Baseline already exists; refusing to replace migration evidence")
    pairs = moves()
    for old, new in pairs:
        assert (ROOT / old).is_file() and not (ROOT / old).is_symlink(), old
        assert not (ROOT / new).exists(), new
    check_hook("analysis/code")
    status = command(["bash", "analysis/code/project_git.sh", "status", "--short"])
    namespace = {}
    exec(compile((ROOT / "analysis/code/check_git_content.py").read_text(), "check_git_content.py", "exec"), namespace)
    permitted = namespace["permitted"]
    assert permitted("analysis/code/project_runtime.py")
    for path in ["decode_data/a.root", "analysis/a.bin", "analysis/secrets.json", "analysis/a.o"]:
        assert not permitted(path), path
    write_json(BASELINE, {
        "moves": [{"old": old, "new": new, "sha256": sha(ROOT / old)} for old, new in pairs],
        "decoder_sha256": {name: sha(ROOT / "decode_data/DecodeAndSortAll" / name) for name in DECODER_FILES},
        "config_sha256": sha(ROOT / ".codex/config.toml"),
        "experiment_text": (ROOT / "analysis/record_analysis.md").read_text(),
        "git_status_before": status,
        "checks": [{"name": "Pre-migration Git, hook event/project boundaries and file policy", "returncode": 0}],
    })
    print("Captured migration baseline and passing pre-migration checks")


def replace(path, old, new):
    value = path.read_text()
    if old in value:
        path.write_text(value.replace(old, new))


def update_lock():
    path = ROOT / "analysis/third_party/sources.lock.json"
    lock = json.loads(path.read_text())
    adaptations = {item["directory"]: item for item in lock["adaptations"]}
    for name in SKILLS + ["python-svg-qa"]:
        directory = ".agents/skills/" + name
        base = ROOT / directory
        if not (base / "SKILL.md").is_file():
            continue
        item = adaptations.get(directory)
        if item is None:
            item = {"directory": directory}
            lock["adaptations"].append(item)
        item["entry_sha256"] = sha(base / "SKILL.md")
        if name == "python-svg-qa":
            item.update({"source": "project", "files_sha256": {
                "SKILL.md": sha(base / "SKILL.md"), "scripts/audit_svg.py": sha(base / "scripts/audit_svg.py")},
                "basis": "Project Python/SVG conventions and installed Nature figure QA principles; locally authored helper"})
    write_json(path, lock)


def migrate():
    baseline = json.loads(BASELINE.read_text())
    for item in baseline["moves"]:
        assert sha(ROOT / item["old"]) == item["sha256"], item["old"]
        assert not (ROOT / item["new"]).exists(), item["new"]
    for item in baseline["moves"]:
        dest = ROOT / item["new"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        (ROOT / item["old"]).rename(dest)
    current = [ROOT / "analysis/scripts" / name for name in TOOLS]
    current += [ROOT / name for name in ["README.md", "analysis/third_party/INSTALL.md",
               "analysis/project_maintenance/reports/project_setup.md", ".codex/hooks.json",
               ".githooks/pre-commit", ".githooks/pre-push", ".githooks/post-commit"]]
    for path in current:
        replace(path, "analysis/code/", "analysis/scripts/")
    for name in SKILLS:
        for base in [".agents/skills", ".codex/skills"]:
            path = ROOT / base / name / "SKILL.md"
            replace(path, "analysis/code/DecodeAndSortAll/", "decode_data/DecodeAndSortAll/")
            replace(path, "analysis/code/", "analysis/scripts/")
            replace(path, "analysis/record_analysis.md", "analysis/experiment_log/record_analysis.md")
            if name == "crawl4ai":
                replace(path, "抓取脚本放入 `analysis/scripts/`，小型报告放入 `analysis/`", "抓取脚本放入 `analysis/<任务名>/`，小型报告放入该任务的 `reports/`")
    record = ROOT / "analysis/experiment_log/record_analysis.md"
    replace(record, "./analysis_figure/record_analysis/", "./figures/")
    replace(ROOT / "README.md", "analysis/record_analysis.md", "analysis/experiment_log/record_analysis.md")
    replace(ROOT / "analysis/third_party/INSTALL.md", "python analysis/scripts/<your-script>.py", "python analysis/<task>/<your-script>.py")
    policy = ROOT / "analysis/scripts/check_git_content.py"
    replace(policy, "        or path.startswith(\".agents/skills/\")", "        or path.startswith(\".agents/skills/\")\n        or path in DECODER_SOURCE_FILES")
    replace(policy, "SOURCE_ENV_EXAMPLES =", "DECODER_SOURCE_FILES = " + repr({"decode_data/DecodeAndSortAll/" + name for name in DECODER_FILES}) + "\nSOURCE_ENV_EXAMPLES =")
    replace(policy, "analysis/scripts/DecodeAndSortAll/decodeandsort", "decode_data/DecodeAndSortAll/decodeandsort")
    ignore = ROOT / ".gitignore"
    replace(ignore, "/analysis/code/DecodeAndSortAll/decodeandsort", "/decode_data/DecodeAndSortAll/decodeandsort")
    with ignore.open("a") as stream:
        stream.write("\n# 官方解码源码保留用户移动位置；同目录其他文件默认忽略。\n!/decode_data/\n/decode_data/*\n!/decode_data/DecodeAndSortAll/\n/decode_data/DecodeAndSortAll/*\n")
        for name in DECODER_FILES:
            stream.write("!/decode_data/DecodeAndSortAll/" + name + "\n")
    for folder in ["analysis/code", "analysis/records", "analysis/analysis_figure/record_analysis", "analysis/analysis_figure"]:
        path = ROOT / folder
        if path.exists() and not any(path.iterdir()):
            path.rmdir()
    update_lock()
    print("Migrated approved files and fixed active script, hook and skill references")


def install_skill():
    stage = ROOT / "analysis/project_maintenance/svg_skill_staging/python-svg-qa"
    for name in ["SKILL.md", "scripts/audit_svg.py"]:
        for base in [".agents/skills/python-svg-qa", ".codex/skills/python-svg-qa"]:
            target = ROOT / base / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(stage / name, target)
    update_lock()
    print("Installed matching project SVG skill entrypoints")


def verify():
    baseline = json.loads(BASELINE.read_text())
    checks = list(baseline["checks"])
    for item in baseline["moves"]:
        target = ROOT / item["new"]
        assert target.is_file() and not (ROOT / item["old"]).exists(), item
        if item["old"].startswith(("analysis/records/", "analysis/analysis_figure/")):
            assert sha(target) == item["sha256"], target
    assert (ROOT / "analysis/experiment_log/record_analysis.md").read_text() == baseline["experiment_text"].replace("./analysis_figure/record_analysis/", "./figures/")
    for name, digest in baseline["decoder_sha256"].items():
        assert sha(ROOT / "decode_data/DecodeAndSortAll" / name) == digest, name
    assert sha(ROOT / ".codex/config.toml") == baseline["config_sha256"]
    checks.append({"name": "Migrated files, historical evidence, source images, experiment content, decoder and user config preserved", "returncode": 0})
    check_hook("analysis/scripts")
    command(["bash", "analysis/scripts/project_git.sh", "status", "--short"])
    namespace = {}
    exec(compile((ROOT / "analysis/scripts/check_git_content.py").read_text(), "check_git_content.py", "exec"), namespace)
    visible_sources = set(command(["bash", "analysis/scripts/project_git.sh", "ls-files", "--cached", "--others", "--exclude-standard", "--", "decode_data/DecodeAndSortAll"]).splitlines())
    for name in DECODER_FILES:
        path = "decode_data/DecodeAndSortAll/" + name
        assert namespace["permitted"](path), path
        assert path in visible_sources, path
    for name in ["a.root", "a.bin", "a.o", "decodeandsort", "secrets.json", "other.cc"]:
        path = "decode_data/DecodeAndSortAll/" + name
        assert not namespace["permitted"](path), path
        proc = subprocess.run(["bash", "analysis/scripts/project_git.sh", "check-ignore", "-q", "--no-index", path], cwd=ROOT)
        assert proc.returncode == 0, path
    for path in (ROOT / "analysis/scripts").glob("*.py"):
        compile(path.read_text(), str(path), "exec")
    command(["bash", "-n", "analysis/scripts/project_git.sh"])
    command(["node", "--check", "analysis/scripts/skill-routing-hook.mjs"])
    for path in (ROOT / ".githooks").iterdir():
        command(["sh", "-n", str(path)])
    checks.append({"name": "Post-migration Git, hook boundaries, source allowlist, data exclusions and program syntax", "returncode": 0})
    lock = json.loads((ROOT / "analysis/third_party/sources.lock.json").read_text())
    for item in lock['adaptations']:
        for relative, digest in item.get('files_sha256', {'SKILL.md': item['entry_sha256']}).items():
            for base in [ROOT/item['directory'], ROOT/'.codex/skills'/Path(item['directory']).name]:
                assert sha(base/relative) == digest, str(base/relative)
    context = json.loads(command(['node', 'analysis/scripts/skill-routing-hook.mjs'], json.dumps({'hook_event_name': 'UserPromptSubmit', 'cwd': str(ROOT)})))['hookSpecificOutput']['additionalContext']
    assert 'python-svg-qa' in context and '无需额外用户确认' in context
    checks.append({'name': 'Skill mirrors and source-lock fingerprints; SVG automatic routing and safe autonomy injection', 'returncode': 0})
    self_test_path = REPORTS/'svg_qa_self_test.json'
    if self_test_path.exists():
        test = json.loads(self_test_path.read_text())
        assert test['self_test'] == 'pass' and len(test['cases']) == 4
        assert all(item['actual'] == item['expected'] for item in test['cases'])
        checks.append({'name': 'Actual Chromium SVG self-test covers clear, overlap, clipping and not-auditable cases; output boundary assertions passed', 'returncode': 0})
    qa_path = ROOT/'run_log/reports/figure_qa.json'
    if qa_path.exists():
        qa = json.loads(qa_path.read_text())
        assert qa['status'] == 'passed' and qa['reports']
        for item in qa['reports']:
            # Map the preserved historical audit to the user's new location.
            assert sha(ROOT/'run_log/figures'/Path(item['svg']).name) == item['sha256']
            assert item['auto_result'] == 'pass' and item['visual_review'] == 'passed'
        checks.append({'name': 'Final SVGs match actual automated and completed visual review fingerprints', 'returncode': 0})
    report = {"status": "passed", "checks": checks, "limitations": ["No commit, push, installation restore or model API call performed"]}
    write_json(REPORTS / "layout_svg_qa_verification.json", report)
    print("Layout verification: PASS (%d checks)" % len(checks))


def cleanup_stage():
    stage = ROOT/'analysis/project_maintenance/svg_skill_staging/python-svg-qa'
    for name in ['SKILL.md', 'scripts/audit_svg.py']:
        path = stage/name
        assert sha(path) == sha(ROOT/'.agents/skills/python-svg-qa'/name)
        path.unlink()
    for path in [stage/'scripts', stage, stage.parent]:
        path.rmdir()
    print('Removed only the matching generated skill staging files')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["capture", "migrate", "install-skill", "verify", "cleanup-stage"])
    args = parser.parse_args()
    {"capture": capture, "migrate": migrate, "install-skill": install_skill, "verify": verify, "cleanup-stage": cleanup_stage}[args.action]()


if __name__ == "__main__":
    main()
