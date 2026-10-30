# Two entry executables share one immutable runtime directory. The GUI has no
# console; the worker's console streams are redirected by CREATE_NO_WINDOW.
from pathlib import Path
import os
import json
project_edition = os.environ.get("RESUME_BUILD_PROJECT_EDITION") == "1"
gui_name = "ResumeOptimizerProjects" if project_edition else "ResumeOptimizerDesktop"
worker_name = "ResumeOptimizerProjectsWorker" if project_edition else "ResumeOptimizerWorker"
entry = "project_main.py" if project_edition else "main.py"
ROOT = Path(SPECPATH).parent
datas = [
    (str(ROOT / "api/resources"), "resources"),
    (str(ROOT / "api/prompts"), "prompts"),
    (str(ROOT / "api/docgen/master_resume_template.docx"), "docgen"),
]
assets = ROOT / "build/desktop-assets"
manifest = json.loads((assets / "manifest.json").read_text(encoding="utf-8"))
datas.append((str(assets / "manifest.json"), "desktop-assets"))
for item in manifest['files']:
    relative = Path(item['path'])
    datas.append((str(assets / relative), str(Path('desktop-assets') / relative.parent)))
for directory in ("desktop", "api"):
    for path in (ROOT / directory).rglob("*"):
        relative = path.relative_to(ROOT)
        if path.is_file() and not any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
            if path.suffix in {".py", ".json", ".txt", ".yaml", ".j2", ".docx", ".md", ".ps1", ".nsi", ".spec", ".lock"}:
                datas.append((str(path), str(Path("source") / relative.parent)))
a = Analysis([str(ROOT / "desktop" / entry)], pathex=[str(ROOT), str(ROOT / "api")],
             datas=datas, hiddenimports=["onnxruntime", "tokenizers"],
             excludes=["torch", "sentence_transformers", "transformers", "tkinter",
                       "pytest", "desktop.prepare_assets", "desktop.smoke", "desktop.validate_embeddings",
                       "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
                       "PySide6.QtQml", "PySide6.QtQuick"], noarchive=False)
pyz = PYZ(a.pure)
gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name=gui_name,
          console=False, debug=False, strip=False, upx=False)
worker = EXE(pyz, a.scripts, [], exclude_binaries=True, name=worker_name,
             console=True, debug=False, strip=False, upx=False)
coll = COLLECT(gui, worker, a.binaries, a.datas, strip=False, upx=False, name=gui_name)
