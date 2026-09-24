"""Every stage writes its artifact to data/runs/{run_id}/. That folder IS the debugger."""
import json
import uuid
from pathlib import Path
from typing import Any, Optional

from config import settings


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def run_dir(run_id: str) -> Path:
    d = settings.runs_dir / run_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_json(run_id: str, name: str, payload: Any) -> Path:
    path = run_dir(run_id) / f"{name}.json"
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_json(run_id: str, name: str) -> Optional[dict]:
    path = run_dir(run_id) / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def exists(run_id: str, name: str) -> bool:
    return (run_dir(run_id) / f"{name}.json").exists()


def save_bytes(run_id: str, name: str, data: bytes) -> Path:
    path = run_dir(run_id) / name
    path.write_bytes(data)
    return path


def save_text(run_id: str, name: str, text: str) -> Path:
    path = run_dir(run_id) / name
    path.write_text(text, encoding="utf-8")
    return path
