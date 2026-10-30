from __future__ import annotations

import os
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "build" / "runtime-bundle.zip"


def include(path: Path) -> bool:
    if any(part in {".git", "__pycache__", ".pytest_cache", "tests"} for part in path.parts):
        return False
    if path.suffix in {".pyc", ".pyo"}:
        return False
    return True


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    roots = [ROOT / "api", ROOT / "n8n" / "workflows"]
    files = [ROOT / name for name in ("docker-compose.yml", "docker-compose.launcher.yml", ".env.example")]
    for source_root in roots:
        files.extend(path for path in source_root.rglob("*") if path.is_file() and include(path))
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(files):
            if path.is_file() and include(path.relative_to(ROOT)):
                archive.write(path, path.relative_to(ROOT).as_posix())
    print(f"Runtime bundle created: {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
