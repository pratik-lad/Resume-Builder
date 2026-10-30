from __future__ import annotations

import os
import sys
from pathlib import Path

from desktop.edition import APP_ID, WORKER_EXE, ENTRYPOINT

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
ASSETS = ROOT / "desktop-assets" if getattr(sys, "frozen", False) else ROOT / "build" / "desktop-assets"
DATA = Path(os.environ.get("RESUME_DESKTOP_DATA", str(Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_ID)))


def initialize():
    # Configure paths before importing the existing API modules. Never read a
    # development .env or write user data beside the installed executable.
    DATA.mkdir(parents=True, exist_ok=True)
    os.chdir(DATA)
    sys.path.insert(0, str(ROOT / "api"))
    for name, directory in (("RUNS_DIR", "runs"), ("CACHE_DIR", "cache"),
                            ("DATASETS_DIR", "datasets"), ("EVALUATION_DIR", "evaluation")):
        os.environ[name] = str(DATA / directory)
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                      TOKENIZERS_PARALLELISM="false", OMP_NUM_THREADS="1",
                      OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1",
                      EMBED_ENABLED="false", NUM_CTX="4096", CTX_SIZE="8192")
    for directory in ("drafts", "logs", "artifacts"):
        (DATA / directory).mkdir(exist_ok=True)


def worker_command():
    if getattr(sys, "frozen", False):
        return [str(Path(sys.executable).with_name(WORKER_EXE)), "--worker"]
    return [sys.executable, str(ROOT / "desktop" / ENTRYPOINT), "--worker"]
