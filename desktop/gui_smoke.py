"""Headless Qt integration test with the real worker and a 2,000-word JD."""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-exe")
    parser.add_argument("--no-model", action="store_true")
    parser.add_argument("--resume")
    parser.add_argument("--jd-file")
    parser.add_argument("--data-dir")
    args = parser.parse_args()
    for name in ("resume", "jd_file", "data_dir", "worker_exe"):
        if getattr(args, name):
            # Preserve a short Windows junction used to launch frozen DLLs.
            setattr(args, name, os.path.abspath(getattr(args, name)) if name == "worker_exe" else str(Path(getattr(args, name)).resolve()))
    target = Path(tempfile.mkdtemp(prefix="ResumeGuiSmoke-"))
    os.environ.update(QT_QPA_PLATFORM="offscreen", RESUME_DESKTOP_DATA=args.data_dir or str(target / "data"),
                      HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    from desktop.bootstrap import initialize
    initialize()
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtGui import QTextCursor, QFontDatabase, QFont
    from desktop.app import Window
    import desktop.controller as controller
    import fitz
    if args.worker_exe:
        controller.worker_command = lambda: [args.worker_exe, "--worker"]
    # Construct an actual three-page text PDF with source employment metadata.
    source = target / "Three page resume.pdf"
    pdf = fitz.open()
    for page_number in range(3):
        page = pdf.new_page()
        lines = (["Alex Example", "alex@example.test", "Professional Summary",
                  "Backend engineer delivering Python APIs.", "Technical Skills", "Python, FastAPI, Docker",
                  "Professional Experience"] if page_number == 0 else ["Professional Experience"])
        for block in range(5):
            lines.extend([f"Backend Engineer | Example Labs {page_number * 5 + block} | Jan 2022 - Dec 2024",
                          "- Developed Python APIs using FastAPI and integrated operational reporting.",
                          "- Added automated Docker deployment checks and documented recovery procedures."])
        if page_number == 2:
            lines.extend(["Education", "BSc Computer Science | Example College | 2021"])
        for row, text in enumerate(lines):
            page.insert_text((35, 40 + row * 21), text, fontsize=10)
    pdf.save(source)
    words = ["Requirements"]
    for index in range(100):
        words.extend(f"Develop module {index} using Python and FastAPI with Docker deployment automated tests operational reporting documentation and reliable incident recovery across product teams.".split())
    jd = " ".join(words[:2000])
    if args.resume:
        source = Path(args.resume)
    if args.jd_file:
        jd = Path(args.jd_file).read_text(encoding="utf-8")
    app = QApplication([])
    if os.name == "nt" and not QFontDatabase.families():
        QFontDatabase.addApplicationFont(str(Path(os.environ["WINDIR"]) / "Fonts/segoeui.ttf"))
        app.setFont(QFont("Segoe UI", 10))
    window = Window()
    window.resume.setText(str(source))
    window.jd.setPlainText(jd)
    result = {"resume_pages": None if args.resume else 3, "jd_words": len(jd.split()),
              "reference_8gb_laptop": False, "output_directory": str(target),
              "cache_profile": args.data_dir or "new isolated profile"}
    ticks = []
    last_tick = time.perf_counter()
    heartbeat = QTimer()
    heartbeat.setInterval(20)
    def tick():
        nonlocal last_tick
        now = time.perf_counter()
        ticks.append(now - last_tick)
        last_tick = now
    heartbeat.timeout.connect(tick)
    heartbeat.start()
    errors = []
    QMessageBox.warning = lambda *args: errors.append(str(args[-1]))
    started = time.perf_counter()
    def finish():
        heartbeat.stop()
        result["peak_gui_worker_tree_rss_bytes"] = window.controller.peak_rss
        result["max_event_loop_gap_seconds"] = round(max(ticks, default=0), 4)
        result["errors"] = errors
        window.close()
        app.quit()
    def event(item):
        if item["status"] == "progress":
            print(item.get("message", "Working"), flush=True)
        if item["status"] == "error":
            errors.append(item.get("message"))
            finish()
        if item["status"] != "complete":
            return
        if item["kind"] == "draft":
            (target / "generated-document.json").write_text(json.dumps(window.document, indent=2), encoding="utf-8")
            result["model_calls"] = window.document.get("model_calls", 0)
            result["draft_wall_seconds"] = round(time.perf_counter() - started, 3)
            row = next(i for i, section in enumerate(window.document["sections"]) if section["key"] == "summary")
            window.sections.setCurrentRow(row)
            start_edit = time.perf_counter()
            window.editor.moveCursor(QTextCursor.MoveOperation.End)
            window.editor.insertPlainText(" Edited in the desktop application.")
            result["edit_handler_seconds"] = round(time.perf_counter() - start_edit, 4)
            start_preview = time.perf_counter()
            window.autosave()
            window.refresh_preview()
            result["preview_autosave_seconds"] = round(time.perf_counter() - start_preview, 4)
            assert "Edited in the desktop" in window.preview.toPlainText()
            start_cancel = time.perf_counter()
            window.controller.cancel()
            result["cancel_ack_seconds"] = round(time.perf_counter() - start_cancel, 4)
            QTimer.singleShot(50, finish)
    window.controller.event.connect(event)
    if args.no_model:
        from desktop.edition import PROJECT_EDITION
        if PROJECT_EDITION:
            from desktop.project_generation import generate
            from desktop.test_project_quality import ProjectRuntime as FakeRuntime
        else:
            from desktop.generation import generate
            from desktop.test_generation import FakeRuntime
        document = generate({"resume": str(source), "jd": jd}, FakeRuntime(), lambda *args: None)
        def local_result():
            item = {"status": "complete", "kind": "draft", "result": document, "seconds": .01}
            window.job_event(item)
            event(item)
        result["model_used"] = False
        QTimer.singleShot(0, local_result)
    else:
        result["model_used"] = True
        QTimer.singleShot(0, window.generate_draft)
    QTimer.singleShot(1800000, lambda: (errors.append("GUI test timed out"), finish()))
    last_tick = time.perf_counter()
    started = time.perf_counter()
    app.exec()
    output = ROOT / "build/desktop-gui-smoke.json"
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
