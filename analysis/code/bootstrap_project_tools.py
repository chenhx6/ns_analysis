#!/usr/bin/env python3
"""Restore project tools without global installs, symlinks or data-directory writes.

Run with the system Python: python3 analysis/code/bootstrap_project_tools.py.
Large executable files live in .runtime; /tmp supplies an executable filesystem.
OMX configuration is already versioned, so this script never runs omx setup.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / ".runtime"
VENDOR = ROOT / "analysis/vendor"
LOCK = ROOT / "analysis/third_party/sources.lock.json"
PYTHON_VERSION = "3.12.15"
UV_ASSET = "uv-x86_64-unknown-linux-gnu.tar.gz"


def stage(message):
    print("[bootstrap] " + message, flush=True)


def run(args, env, cwd=ROOT):
    stage("Running: " + " ".join(str(arg) for arg in args))
    subprocess.run([str(arg) for arg in args], cwd=str(cwd), env=env, check=True)


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def replace_runtime_tree(source, dest, ignore=None):
    """Replace only a known generated directory beneath this project's runtime."""
    if dest.is_symlink() or RUNTIME.resolve() not in dest.resolve().parents:
        raise RuntimeError("Unsafe runtime destination: " + str(dest))
    if dest.exists():
        shutil.rmtree(str(dest))
    dest.parent.mkdir(parents=True, exist_ok=True)
    # copyfile avoids propagating executable modes unsupported on the data disk.
    shutil.copytree(str(source), str(dest), symlinks=False,
                    copy_function=shutil.copyfile, ignore=ignore)


def local_environment():
    env = os.environ.copy()
    env.update({
        "XDG_CACHE_HOME": str(RUNTIME / "xdg-cache"),
        "XDG_CONFIG_HOME": str(RUNTIME / "xdg-config"),
        "CLAUDE_CONFIG_DIR": str(RUNTIME / "claude"),
        "CRAWL4_AI_BASE_DIRECTORY": str(RUNTIME / "crawl4ai"),
        "HF_HOME": str(RUNTIME / "huggingface"),
        "NLTK_DATA": str(RUNTIME / "nltk-data"),
        "PYTHONNOUSERSITE": "1",
        "PYTHONPYCACHEPREFIX": str(RUNTIME / "pycache"),
        "OMX_AUTO_UPDATE": "0",
    })
    return env


def restore_node(env, temp):
    stage("Restore OMX Node dependencies and compile TypeScript")
    if not shutil.which("node") or not shutil.which("npm"):
        raise RuntimeError("Node.js >=20 and npm must already be available")
    major = subprocess.check_output(
        ["node", "-p", "process.versions.node.split('.')[0]"], env=env,
        universal_newlines=True).strip()
    if int(major) < 20:
        raise RuntimeError("OMX requires Node.js >=20")
    omx = VENDOR / "oh-my-codex"
    run(["npm", "ci", "--ignore-scripts", "--no-bin-links", "--cache",
         RUNTIME / "npm-cache"], env, cwd=omx)
    compiler_package = omx / "node_modules/@typescript/typescript-linux-x64"
    compiler_copy = temp / "typescript-linux-x64"
    shutil.copytree(str(compiler_package), str(compiler_copy))
    compiler = compiler_copy / "lib/tsc"
    compiler.chmod(0o755)
    run([compiler, "-p", omx / "tsconfig.json"], env, cwd=omx)

    stage("Download and verify OMX's four native components")
    native_env = dict(env, OMX_NATIVE_CACHE_DIR=str(temp / "omx-native-cache"),
                      OMX_NATIVE_AUTO_FETCH="1")
    module = (omx / "dist/cli/native-assets.js").as_uri()
    js = """
const {hydrateNativeBinary} = await import(process.argv[1]);
for (const product of ['omx-runtime','omx-explore-harness','omx-sparkshell','omx-api']) {
  const path = await hydrateNativeBinary(product);
  if (!path) throw new Error('No verified native binary available for ' + product);
  console.log('CHX_NATIVE ' + JSON.stringify({product, path}));
}
"""
    output = subprocess.check_output(
        ["node", "--input-type=module", "-e", js, module], env=native_env,
        cwd=str(omx), universal_newlines=True)
    print(output, end="", flush=True)
    products = []
    for line in output.splitlines():
        if line.startswith("CHX_NATIVE "):
            item = json.loads(line[len("CHX_NATIVE "):])
            products.append(item)
    if len(products) != 4:
        raise RuntimeError("OMX native hydration did not return four binaries")
    dest = RUNTIME / "omx-native-bin"
    dest.mkdir(parents=True, exist_ok=True)
    for item in products:
        shutil.copyfile(item["path"], str(dest / item["product"]))

    manifests = ROOT / "analysis/third_party/nature-node"
    fixed_files = [manifests / name for name in ("package.json", "package-lock.json")]
    if any(path.exists() for path in fixed_files):
        if not all(path.is_file() for path in fixed_files):
            raise RuntimeError("Nature Node restoration needs both fixed manifests")
        stage("Restore locked Nature Mermaid/Puppeteer dependencies")
        nature = RUNTIME / "nature-node"
        if nature.is_symlink():
            raise RuntimeError("Unsafe Nature Node runtime destination")
        nature.mkdir(parents=True, exist_ok=True)
        for source in fixed_files:
            shutil.copyfile(str(source), str(nature / source.name))
        nature_env = dict(env, PUPPETEER_SKIP_DOWNLOAD="1")
        run(["npm", "ci", "--ignore-scripts", "--no-bin-links", "--cache",
             RUNTIME / "npm-cache"], nature_env, cwd=nature)


def prepare_uv(env, temp):
    snapshot = json.loads(LOCK.read_text())
    uv_lock = snapshot.get("bootstrap_uv")
    if uv_lock is None:
        for section in ("runtime", "runtimes"):
            uv_lock = snapshot.get(section, {}).get("bootstrap_uv")
            if uv_lock is not None:
                break
    uv_lock = uv_lock or {}
    version = str(uv_lock.get("version", "")).lstrip("v")
    url = uv_lock.get("url") or (
        "https://github.com/astral-sh/uv/releases/" +
        ("download/" + version if version else "latest/download") + "/" + UV_ASSET)
    archive = RUNTIME / "bootstrap/uv.tar.gz"
    if not archive.is_file():
        stage("Download official uv release: " + url)
        downloaded = temp / "uv.tar.gz"
        with urllib.request.urlopen(url, timeout=120) as response:
            with downloaded.open("wb") as stream:
                shutil.copyfileobj(response, stream)
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(downloaded), str(archive))
    checksum = digest(archive)
    expected = uv_lock.get("sha256")
    if expected and checksum != expected:
        raise RuntimeError("uv archive SHA256 differs from sources.lock.json")
    uv = temp / "uv"
    with tarfile.open(str(archive), "r:gz") as package:
        members = [member for member in package.getmembers()
                   if member.isfile() and member.name.endswith("/uv")]
        if len(members) != 1:
            raise RuntimeError("Official uv archive must contain one uv executable")
        with package.extractfile(members[0]) as source, uv.open("wb") as dest:
            shutil.copyfileobj(source, dest)
    uv.chmod(0o755)
    actual = subprocess.check_output([str(uv), "--version"], env=env,
                                     universal_newlines=True).strip()
    if version and actual.split()[1] != version:
        raise RuntimeError("uv version differs from sources.lock.json: " + actual)
    receipt = {"url": url, "sha256": checksum, "version": actual.split()[1],
               "archive": str(archive.relative_to(ROOT))}
    (archive.parent / "uv.source.json").write_text(
        json.dumps(receipt, indent=2) + "\n")
    stage("Verified uv source: " + json.dumps(receipt))
    return uv


def restore_python(env, temp):
    requirements = ROOT / "analysis/third_party/python.requirements.lock"
    if not requirements.is_file():
        raise RuntimeError("Missing locked requirements: " + str(requirements))
    uv = prepare_uv(env, temp)
    install_dir = temp / "python-install"
    py_env = dict(env, UV_PYTHON_INSTALL_DIR=str(install_dir),
                  UV_CACHE_DIR=str(temp / "uv-cache"),
                  UV_PYTHON_BIN_DIR=str(temp / "uv-bin"))
    stage("Install private CPython " + PYTHON_VERSION)
    run([uv, "python", "install", "--no-bin", PYTHON_VERSION], py_env)
    distributions = sorted(install_dir.glob("cpython-" + PYTHON_VERSION + "-*"))
    if len(distributions) != 1:
        raise RuntimeError("Expected one downloaded CPython distribution")
    distribution = distributions[0]
    python = distribution / "bin/python3.12"

    def ignore_terminfo(directory, names):
        return ["terminfo"] if Path(directory).name == "share" else []

    replace_runtime_tree(distribution, RUNTIME / "python" / distribution.name,
                         ignore=ignore_terminfo)
    stage("Install locked Python packages into project site-packages")
    target = RUNTIME / "site-packages"
    if target.is_symlink():
        raise RuntimeError("Unsafe site-packages destination")
    if target.exists():
        shutil.rmtree(str(target))
    run([uv, "pip", "install", "--python", python, "--target", target,
         "--link-mode", "copy", "-r", requirements, "--extra-index-url",
         "https://download.pytorch.org/whl/cpu", "--index-strategy",
         "unsafe-best-match"], py_env)
    stage("Install Playwright and Patchright Chromium into private cache")
    browser_dir = temp / "browsers"
    browser_env = dict(py_env, PYTHONPATH=str(target),
                       PLAYWRIGHT_NODEJS_PATH=shutil.which("node") or "/usr/bin/node",
                       PLAYWRIGHT_HOST_PLATFORM_OVERRIDE="ubuntu22.04-x64",
                       PLAYWRIGHT_BROWSERS_PATH=str(browser_dir))
    for module in ("playwright", "patchright"):
        run([python, "-m", module, "install", "chromium"], browser_env)
    replace_runtime_tree(browser_dir, RUNTIME / "browsers")


def restore_libreoffice(env, temp):
    office = json.loads(LOCK.read_text()).get("libreoffice")
    if not office:
        return
    if not shutil.which("dpkg-deb"):
        raise RuntimeError("LibreOffice unpacking requires dpkg-deb")
    version, url, expected = office["version"], office["url"], office["sha256"]
    if not expected or not url.startswith(
            "https://download.documentfoundation.org/libreoffice/"):
        raise RuntimeError("LibreOffice needs a pinned official source and SHA256")
    archive = RUNTIME / "bootstrap/libreoffice.tar.gz"
    if not archive.is_file():
        stage("Download official LibreOffice release: " + url)
        downloaded = temp / "libreoffice.tar.gz"
        with urllib.request.urlopen(url, timeout=120) as response:
            with downloaded.open("wb") as stream:
                shutil.copyfileobj(response, stream)
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(downloaded), str(archive))
    if digest(archive) != expected:
        raise RuntimeError("LibreOffice archive SHA256 differs from sources.lock.json")
    stage("Unpack verified LibreOffice " + version + " without package installation")
    extracted = temp / "libreoffice-archive"
    extracted.mkdir()
    with tarfile.open(str(archive), "r:gz") as package:
        members = package.getmembers()
        # Validate the entire archive before writing; reject links and devices.
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError("Unsafe LibreOffice archive path: " + member.name)
            if not (member.isdir() or member.isfile()):
                raise RuntimeError("Unsupported LibreOffice archive member: " + member.name)
            target = (extracted / path).resolve()
            if target != extracted and extracted not in target.parents:
                raise RuntimeError("LibreOffice archive path escapes extraction root")
        for member in members:
            target = extracted / member.name
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with package.extractfile(member) as source, target.open("wb") as dest:
                    shutil.copyfileobj(source, dest)
    debs = sorted(extracted.rglob("*.deb"))
    if not debs:
        raise RuntimeError("LibreOffice archive contains no Debian packages")
    unpacked = temp / "libreoffice-unpacked"
    unpacked.mkdir()
    for deb in debs:
        run(["dpkg-deb", "-x", deb, unpacked], env)
    source = unpacked / "opt" / ("libreoffice" + ".".join(version.split(".")[:2]))
    if not (source / "program/soffice").is_file():
        raise RuntimeError("Unpacked LibreOffice does not contain program/soffice")
    replace_runtime_tree(source, RUNTIME / "libreoffice")
    stage("LibreOffice restored inside .runtime/libreoffice")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group()
    options.add_argument("--node-only", action="store_true")
    options.add_argument("--python-only", action="store_true")
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() not in ("x86_64", "amd64"):
        raise RuntimeError("This locked bootstrap targets Linux x86_64 GNU")
    if RUNTIME.is_symlink():
        raise RuntimeError("The project's .runtime must not be a symlink")
    RUNTIME.mkdir(exist_ok=True)
    env = local_environment()
    # Force /tmp because the project's data filesystem cannot run binaries.
    with tempfile.TemporaryDirectory(prefix="chx-bootstrap-", dir="/tmp") as work:
        temp = Path(work)
        if not args.python_only:
            restore_node(env, temp)
        if not args.node_only:
            restore_python(env, temp)
            restore_libreoffice(env, temp)
    stage("Restore complete. Launch tools through analysis/code/project_runtime.py")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print("[bootstrap] Failed: " + str(error), file=sys.stderr)
        sys.exit(1)
