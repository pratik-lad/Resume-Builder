from __future__ import annotations

import json
import os
import uuid
from pathlib import Path


def atomic_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def load_draft(path):
    saved = load_json(path)
    if not isinstance(saved, dict):
        return None
    document = saved.get("document")
    if not isinstance(document, dict) or document.get("mode") not in {"source", "demo"}:
        return None
    if not isinstance(document.get("jd"), str) or not isinstance(document.get("sections"), list):
        return None
    if not all(isinstance(section, dict) and all(isinstance(section.get(key), str)
               for key in ("key", "title", "text")) for section in document["sections"]):
        return None
    from desktop.edition import PROJECT_EDITION
    if PROJECT_EDITION != (document.get("edition") == "projects"):
        return None
    from desktop.project_document import sanitize
    saved["document"] = sanitize(document)
    return saved
