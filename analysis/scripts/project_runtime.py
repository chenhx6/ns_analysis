#!/usr/bin/env python3
"""Launch project tools, using a private temporary execution copy on data disks."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / ".runtime"
INSTALL_ROOT = ROOT
employee_marker = ROOT / '.omx/employee.json'
if employee_marker.is_file():
    # Installed tools are shared read-only; caches and process cwd stay in the employee checkout.
    INSTALL_ROOT = Path(json.loads(employee_marker.read_text())['project']).resolve()
INSTALL_RUNTIME = INSTALL_ROOT / '.runtime'


def executable_copy(source, label):
    """Keep canonical installed files in the project; cache runnable copies in /tmp."""
    identity = hashlib.sha256(str(ROOT).encode()).hexdigest()[:16]
    base = Path(tempfile.gettempdir()) / ("chx-runtime-%s-%s" % (os.getuid(), identity))
    if base.exists() and (base.is_symlink() or base.stat().st_uid != os.getuid()):
        raise RuntimeError("Unsafe execution cache: " + str(base))
    base.mkdir(mode=0o700, exist_ok=True)
    dest = base / label
    stamp = str(source.stat().st_mtime_ns) + ":" + str(source)
    marker = dest / ".project-execution-copy"
    if not marker.is_file() or marker.read_text() != stamp:
        if dest.exists():
            if dest.is_symlink() or dest.stat().st_uid != os.getuid():
                raise RuntimeError("Unsafe execution directory: " + str(dest))
            shutil.rmtree(dest)
        shutil.copytree(source, dest, symlinks=False)
        for path in dest.rglob("*"):
            if path.is_file():
                path.chmod(0o700)
        marker.write_text(stamp)
    return dest


def python_environment():
    distributions = sorted((INSTALL_RUNTIME / "python").glob("cpython-*"))
    if not distributions:
        raise RuntimeError("Project Python is missing; see analysis/third_party/INSTALL.md")
    distribution = executable_copy(distributions[-1], "python")
    python = distribution / "bin/python3.12"
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(INSTALL_RUNTIME / "site-packages"),
        "PYTHONNOUSERSITE": "1",
        "CRAWL4_AI_BASE_DIRECTORY": str(RUNTIME / "crawl4ai"),
        "XDG_CACHE_HOME": str(RUNTIME / "xdg-cache"),
        "XDG_CONFIG_HOME": str(RUNTIME / "xdg-config"),
        "HF_HOME": str(RUNTIME / "huggingface"),
        "NLTK_DATA": str(RUNTIME / "nltk-data"),
        "PLAYWRIGHT_NODEJS_PATH": shutil.which("node") or "/usr/bin/node",
            "PYTHONPYCACHEPREFIX": str(RUNTIME / "pycache"),
            "PLAYWRIGHT_HOST_PLATFORM_OVERRIDE": "ubuntu22.04-x64",
    })
    if (INSTALL_RUNTIME / "browsers").is_dir():
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(executable_copy(INSTALL_RUNTIME / "browsers", "browsers"))
    if (INSTALL_RUNTIME / "libreoffice").is_dir():
        office = executable_copy(INSTALL_RUNTIME / "libreoffice", "libreoffice")
        launcher_dir = office / "project-bin"
        launcher_dir.mkdir(exist_ok=True)
        for name in ["soffice", "libreoffice"]:
            launcher = launcher_dir / name
            launcher.write_text('#!/bin/sh\nexec "' + str(office / "program/soffice") +
                                '" "-env:UserInstallation=' + (RUNTIME / "libreoffice-profile").as_uri() + '" "$@"\n')
            launcher.chmod(0o700)
        env["PATH"] = str(launcher_dir) + os.pathsep + env.get("PATH", "")
    return python, env


def main():
    if len(sys.argv) < 2:
        raise RuntimeError("Usage: python3 analysis/scripts/project_runtime.py python|omx|mermaid [args]")
    mode, args = sys.argv[1], sys.argv[2:]
    if mode == "python":
        python, env = python_environment()
        os.execve(str(python), [str(python), *args], env)
    if mode == "omx":
        env = os.environ.copy()
        env.update({
            "OMX_NATIVE_CACHE_DIR": str(RUNTIME / "omx-native"),
            "XDG_CACHE_HOME": str(RUNTIME / "xdg-cache"),
            "XDG_CONFIG_HOME": str(RUNTIME / "xdg-config"),
            "OMX_AUTO_UPDATE": "0",
        })
        for name in ['GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
                     'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_PREFIX']:
            env.pop(name, None)
        probe = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--git-dir'], env=env, capture_output=True)
        if probe.returncode:
            env["GIT_DIR"] = str(ROOT / ".project-git")
            env["GIT_WORK_TREE"] = str(ROOT)
        native = INSTALL_RUNTIME / "omx-native-bin"
        if native.is_dir():
            executable = executable_copy(native, "omx-native")
            for product, key in {
                "omx-runtime": "OMX_RUNTIME_BINARY",
                "omx-explore-harness": "OMX_EXPLORE_BIN",
                "omx-sparkshell": "OMX_SPARKSHELL_BIN",
                "omx-api": "OMX_API_BIN",
            }.items():
                if (executable / product).is_file():
                    env[key] = str(executable / product)
        cli = ROOT / "analysis/vendor/oh-my-codex/dist/cli/omx.js"
        if not cli.is_file():
            raise RuntimeError("OMX build is missing; see analysis/third_party/INSTALL.md")
        os.chdir(ROOT)
        os.execvpe("node", ["node", str(cli), *args], env)
    if mode == "mermaid":
        browsers = executable_copy(INSTALL_RUNTIME / "browsers", "browsers")
        chrome = sorted(browsers.glob("chromium-*/chrome-linux64/chrome"))
        if not chrome:
            raise RuntimeError("Project Chromium is missing")
        config = RUNTIME / "mermaid-puppeteer.json"
        config.write_text(json.dumps({"executablePath": str(chrome[-1]), "args": ["--no-sandbox"]}))
        cli = INSTALL_RUNTIME / "nature-node/node_modules/@mermaid-js/mermaid-cli/src/cli.js"
        env = os.environ.copy()
        env["PUPPETEER_CACHE_DIR"] = str(RUNTIME / "puppeteer")
        env["XDG_CACHE_HOME"] = str(RUNTIME / "xdg-cache")
        env["XDG_CONFIG_HOME"] = str(RUNTIME / "xdg-config")
        os.execvpe("node", ["node", str(cli), "-p", str(config), *args], env)
    raise RuntimeError("Unknown runtime: " + mode)


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
