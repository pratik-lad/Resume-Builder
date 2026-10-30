"""Build-time only downloads. Installed application never invokes this module."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import sys
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ASSETS = ROOT / "build/desktop-assets"


def download_verified(url, target, digest, size, notify):
    def valid(path):
        if not path.is_file() or path.stat().st_size != size:
            return False
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest() == digest
    if valid(target):
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".part")
    if valid(temporary):
        os.replace(temporary, target)
        return
    offset = temporary.stat().st_size if temporary.exists() else 0
    if offset >= size:
        offset = 0
    if shutil.disk_usage(target.parent).free < size - offset + 256 * 1024**2:
        raise RuntimeError("Insufficient disk space to prepare offline models.")
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        if offset and response.status != 206:
            offset = 0
        if offset and not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
            raise RuntimeError("The download server returned an invalid resume offset.")
        with temporary.open("ab" if offset else "wb") as output:
            done, last = offset, -1
            while chunk := response.read(4 * 1024**2):
                output.write(chunk)
                done += len(chunk)
                if done // max(size // 10, 1) != last:
                    last = done // max(size // 10, 1)
                    notify(f"Downloading {target.name}: {min(100, done * 100 // size)}%")
    if not valid(temporary):
        raise RuntimeError(f"Asset hash/size verification failed: {target.name}. The partial download was preserved.")
    os.replace(temporary, target)


def write_if_changed(path, content):
    # Leave verified identical DLLs untouched, including a runtime currently
    # used by an isolated local generation check.
    if path.is_file() and path.read_bytes() == content:
        return
    path.write_bytes(content)


def main():
    spec = json.loads((ROOT / "desktop/assets.json").read_text())
    ASSETS.mkdir(parents=True, exist_ok=True)
    model = spec["model"]
    url = f"https://huggingface.co/{model['repository']}/resolve/{model['revision']}/{model['filename']}"
    download_verified(url, ASSETS / "models" / model["filename"], model["sha256"], model["size"], print)
    embedding = spec["embedding"]
    for item in embedding["files"]:
        url = f"https://huggingface.co/{embedding['repository']}/resolve/{embedding['revision']}/{item['name']}"
        download_verified(url, ASSETS / "embedding" / item["target"], item["sha256"], item["size"], print)
    runner = spec["runtime"]
    archive = ROOT / "build" / runner["filename"]
    url = f"https://github.com/ggml-org/llama.cpp/releases/download/{runner['version']}/{runner['filename']}"
    download_verified(url, archive, runner["sha256"], runner["size"], print)
    runtime = ASSETS / "runtime"
    runtime.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for item in bundle.infolist():
            if item.is_dir():
                continue
            # Discard archive directory paths, never follow a traversal entry.
            name = Path(item.filename).name
            write_if_changed(runtime / name, bundle.read(item))
    # App-local Microsoft CRT DLLs supplied by the Qt distribution allow the
    # native runner to load on a laptop without developer tools/redist setup.
    import PySide6
    qt_directory = Path(PySide6.__file__).parent
    for path in qt_directory.glob("*140*.dll"):
        write_if_changed(runtime / path.name, path.read_bytes())
    if spec.get("cuda_runtime"):
        cuda = ASSETS / "runtime-cuda"
        cuda.mkdir(exist_ok=True)
        if spec["cuda_runtime"].get("source_build") and not (cuda / "llama-server.exe").exists():
            import subprocess
            subprocess.run([sys.executable, str(ROOT / "desktop/build_cuda.py")], check=True)
        for item in ([] if spec["cuda_runtime"].get("source_build") else spec["cuda_runtime"]["archives"]):
            archive = ROOT / "build" / item["filename"]
            url = f"https://github.com/ggml-org/llama.cpp/releases/download/{spec['cuda_runtime']['version']}/{item['filename']}"
            download_verified(url, archive, item["sha256"], item["size"], print)
            with zipfile.ZipFile(archive) as bundle:
                for entry in bundle.infolist():
                    if not entry.is_dir():
                        write_if_changed(cuda / Path(entry.filename).name, bundle.read(entry))
        for path in qt_directory.glob("*140*.dll"):
            write_if_changed(cuda / path.name, path.read_bytes())
    licences = ASSETS / "licenses"
    licences.mkdir(exist_ok=True)
    sources = {
        "Selected-model-license.txt": model.get("license_url", "https://huggingface.co/Qwen/Qwen3.5-2B/resolve/15852e8c16360a2fea060d615a32b45270f8a8fc/LICENSE"),
        "BGE-MIT.txt": "https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/README.md",
        "BGE-code-MIT.txt": "https://raw.githubusercontent.com/FlagOpen/FlagEmbedding/fd1a2bdf69488ffebe0327999d4400d8c8058a0b/LICENSE",
        "llama-MIT.txt": "https://raw.githubusercontent.com/ggml-org/llama.cpp/b11316/LICENSE",
    }
    for name, url in sources.items():
        (licences / name).write_bytes(urllib.request.urlopen(url, timeout=60).read())
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        shutil.copyfile(python_license, licences / "Python-PSF.txt")
    nsis_license = ROOT / "build/nsis/nsis-3.13/COPYING"
    if nsis_license.exists():
        shutil.copyfile(nsis_license, licences / "NSIS.txt")
    nsisbi_license = ROOT / "build/nsisbi/nsisbi-3.12.3/COPYING"
    if nsisbi_license.exists():
        shutil.copyfile(nsisbi_license, licences / "NSISBI.txt")
    for dist in importlib.metadata.distributions():
        name = dist.metadata.get("Name", "unknown")
        notice = [f"{name} {dist.version}\n",
                  "\n".join(f"{key}: {value}" for key, value in dist.metadata.items())]
        for file in dist.files or []:
            if "license" in str(file).lower() or "copying" in str(file).lower():
                try:
                    notice.append(Path(dist.locate_file(file)).read_text(encoding="utf-8"))
                except (OSError, UnicodeError):
                    pass
        (licences / (name + ".txt")).write_text("\n".join(notice), encoding="utf-8")
    files = []
    for path in sorted(ASSETS.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            if path.parent == ASSETS / "models" and path.name != model["filename"]:
                # Retain previous weights on disk for rollback, but never ship
                # multiple models or partial downloads in the selected bundle.
                continue
            with path.open("rb") as stream:
                sha = hashlib.file_digest(stream, "sha256").hexdigest()
            files.append({"path": path.relative_to(ASSETS).as_posix(), "size": path.stat().st_size, "sha256": sha})
    (ASSETS / "manifest.json").write_text(json.dumps({"spec": spec, "files": files}, indent=2))
    print("Offline assets ready:", sum(item["size"] for item in files), "bytes")


if __name__ == "__main__":
    main()
