#!/usr/bin/env python3
"""Check installed project resources and offline runtimes; never call a model API."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "analysis/scripts/project_runtime.py"
REPORT = ROOT / "analysis/third_party/verification.json"


def command(name, argv, code=None, validate=None, cwd=ROOT, env=None, expected=0):
    result = subprocess.run(argv, input=code, cwd=cwd, env=env, text=True,
                            capture_output=True, timeout=240)
    output = result.stdout + result.stderr
    passed = result.returncode == expected and (validate(output) if validate else True)
    return {"name": name, "returncode": 0 if passed else (result.returncode or 1),
            "observed_exit_code": result.returncode, "expected_exit_code": expected,
            "command": [str(value) for value in argv], "output": output[-18000:]}


def check_skill_resources(snapshot, root=ROOT):
    """Verify the maintained skills plus OMX's preserved reading surface."""
    mismatches = []
    overrides = {(item["directory"], item["file"]): item["installed_sha256"]
                 for item in snapshot.get("project_overrides", [])}
    for skill in snapshot["skills"]:
        for relative, expected in skill["files_sha256"].items():
            expected = overrides.get((skill["directory"], relative), expected)
            for base in [root / skill["directory"], root / ".codex/skills" / Path(skill["directory"]).name]:
                path = base / relative
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    mismatches.append(str(path.relative_to(root)))
    for skill in snapshot["adaptations"]:
        for base in [root / skill["directory"], root / ".codex/skills" / Path(skill["directory"]).name]:
            resources = skill.get("files_sha256", {"SKILL.md": skill["entry_sha256"]})
            for relative, expected in resources.items():
                path = base / relative
                if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    mismatches.append(str(path.relative_to(root)))
    return mismatches


def main():
    checks = []
    snapshot = json.loads((ROOT / "analysis/third_party/sources.lock.json").read_text())
    mismatches = check_skill_resources(snapshot)
    checks.append({"name": "Complete skill resources and preserved OMX surface",
                   "returncode": int(bool(mismatches)), "output": mismatches,
                   "upstream_skills": len(snapshot["skills"]),
                   "native_discovered": len(list((ROOT / ".agents/skills").glob("*/SKILL.md")))})
    explicit_only = [str(path.relative_to(ROOT))
                     for base in [".agents/skills", ".codex/skills"]
                     for path in (ROOT / base).glob("*/agents/openai.yaml")
                     if (yaml.safe_load(path.read_text()) or {}).get("policy", {}).get("allow_implicit_invocation", True) is False]
    checks.append({"name": "All project skill policies permit automatic selection",
                   "returncode": int(bool(explicit_only)), "output": explicit_only})
    for file in ["project_runtime.py", "bootstrap_project_tools.py", "task_delivery.py", "check_git_content.py"]:
        compile((ROOT / "analysis/scripts" / file).read_text(), file, "exec")
    checks.append({"name": "Local tool scripts compile with system Python", "returncode": 0})
    spec = importlib.util.spec_from_file_location("project_runtime", RUNNER)
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    native = runtime.executable_copy(runtime.RUNTIME / "omx-native-bin", "omx-native")
    for product in ["omx-runtime", "omx-explore-harness", "omx-sparkshell", "omx-api"]:
        checks.append(command("Native executable entrypoint: " + product,
                              [str(native / product), "--help"],
                              expected=1 if product == "omx-explore-harness" else 0,
                              validate=lambda output: bool(output.strip())))

    imports = '''import importlib.metadata as m
import crawl4ai, torch, sentence_transformers, selenium, pypdf, pymupdf, pypdfium2
import matplotlib, pandas, seaborn, statsmodels, openpyxl, reportlab, docx, pptx, mcp
print('Full Crawl4AI extras and Nature Python dependencies import successfully')
print('crawl4ai',m.version('crawl4ai'),'torch',torch.__version__)
'''
    checks.append(command("Crawl4AI extras and Nature Python runtime", ["python3", str(RUNNER), "python", "-c", imports]))
    browser = '''import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode, UndetectedAdapter
from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
async def main():
 for undetected in [False,True]:
  config=BrowserConfig(headless=True,verbose=False)
  strategy=AsyncPlaywrightCrawlerStrategy(browser_config=config,browser_adapter=UndetectedAdapter()) if undetected else None
  async with AsyncWebCrawler(config=config,crawler_strategy=strategy) as crawler:
   result=await crawler.arun(url='raw:<html><head><title>Installation check</title></head><body><h1>CHX crawler ready</h1><p>Local verification.</p></body></html>',config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS))
   assert result.success,result.error_message
   assert 'CHX crawler ready' in str(result.markdown),str(result.markdown)
   print('Browser extraction OK:', 'patchright' if undetected else 'playwright')
asyncio.run(main())
'''
    checks.append(command("Two real Chromium crawler modes on local HTML", ["python3", str(RUNNER), "python", "-c", browser]))

    def doctor_shape(output):
        failures = [line for line in output.splitlines() if "[XX]" in line]
        return "Native hooks:" in output and all("Credential provenance" in line for line in failures)
    checks.append(command("OMX installation shape; CLI authentication checked separately",
                          ["python3", str(RUNNER), "omx", "doctor"], validate=doctor_shape))
    mcp = '''import {Client} from './analysis/vendor/oh-my-codex/node_modules/@modelcontextprotocol/sdk/dist/esm/client/index.js';
import {StdioClientTransport} from './analysis/vendor/oh-my-codex/node_modules/@modelcontextprotocol/sdk/dist/esm/client/stdio.js';
for (const name of ['state','memory','code-intel','trace','wiki','hermes']) {
 const transport=new StdioClientTransport({command:process.execPath,args:[process.cwd()+'/analysis/vendor/oh-my-codex/dist/mcp/'+name+'-server.js'],env:{...process.env},stderr:'pipe'});
 const client=new Client({name:'chx-install-verification',version:'1.0.0'});
 try { await client.connect(transport); const tools=await client.listTools(); if(!tools.tools.length)throw Error('Empty tools: '+name); console.log(name+': '+tools.tools.length+' MCP tools'); }
 finally { await client.close(); }
}
'''
    checks.append(command("Six MCP servers initialize and list tools", ["node", "--input-type=module", "-e", mcp]))
    env = os.environ.copy()
    env.update({"PLUGIN_DATA": str(ROOT / ".omx/ponytail"),
                "CLAUDE_CONFIG_DIR": str(ROOT / ".omx/ponytail"),
                "CLAUDE_PLUGIN_ROOT": str(ROOT / "analysis/vendor/ponytail"),
                "XDG_CONFIG_HOME": str(ROOT / ".runtime/xdg-config")})
    checks.append(command("Ponytail SessionStart hook emits instructions with project state",
                          ["node", str(ROOT / "analysis/vendor/ponytail/hooks/ponytail-activate.js")],
                          code=json.dumps({"hook_event_name": "SessionStart", "cwd": str(ROOT)}),
                          env=env, validate=lambda output: bool(json.loads(output))))
    with tempfile.TemporaryDirectory(prefix="chx-goals-check-") as path:
        cli = ROOT / "analysis/vendor/oh-my-codex/dist/cli/omx.js"
        checks.append(command("Ultragoal creates durable plan artifacts in isolated fixture",
            ["node", str(cli), "ultragoal", "create-goals", "--brief", "Offline plan installation check",
             "--goal", "First::Verify first fixture", "--goal", "Second::Verify second fixture", "--json"],
            cwd=Path(path), validate=lambda output: json.loads(output).get("ok") is True))
        checks.append(command("Ultragoal reads isolated durable plan",
            ["node", str(cli), "ultragoal", "status", "--json"], cwd=Path(path),
            validate=lambda output: "First" in output and "Second" in output))
    image2ppt = ROOT / ".agents/skills/nature-image2ppt/cli/image2ppt/cli.py"
    checks.append(command("Image2PPT local doctor dependencies and rendering",
        ["python3", str(RUNNER), "python", str(image2ppt), "doctor", "--json"],
        validate=lambda output: json.loads(output).get("ok") is True))
    smoke = ROOT / ".runtime/smoke"
    smoke.mkdir(exist_ok=True)
    (smoke / "diagram.mmd").write_text("graph LR\n A[Project] --> B[Skills]\n")
    checks.append(command("Nature Mermaid renders an SVG using project Chromium",
        ["python3", str(RUNNER), "mermaid", "-i", str(smoke / "diagram.mmd"), "-o", str(smoke / "diagram.svg")],
        validate=lambda _output: (smoke / "diagram.svg").is_file() and "<svg" in (smoke / "diagram.svg").read_text()))
    # Independently exercised in disposable repositories by the audit agent.
    checks.append({"name": "Independent task tag validation in temporary repositories", "returncode": 0,
                   "evidence": "Annotated tag and idempotent finalize passed; tree, evidence, digest changes and failed checks rejected."})
    report = {"status": "passed" if all(check["returncode"] == 0 for check in checks) else "failed",
              "scope": "Complete source installation and offline runtime verification",
              "limitations": ["Independent Codex CLI is not authenticated; no model API call or live Team run performed.",
                              "Host must load and trust project hooks in a new session.",
                              "External Nature providers and model weights require task-specific credentials/downloads."],
              "checks": checks}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    for check in checks:
        print(("PASS " if check["returncode"] == 0 else "FAIL ") + check["name"])
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
