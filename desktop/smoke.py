"""Real-worker benchmark, isolated data, source/demo draft and edited exports."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-exe")
    parser.add_argument("--exports-only", action="store_true")
    parser.add_argument("--resume")
    parser.add_argument("--jd-file")
    parser.add_argument("--data-dir")
    args = parser.parse_args()
    result = {"hardware": {"os": __import__("platform").platform(), "ram_bytes": psutil.virtual_memory().total,
                           "physical_cores": psutil.cpu_count(logical=False), "gpu_used": False},
              "reference_8gb_laptop": False, "results": []}
    directory = Path(tempfile.mkdtemp(prefix="Resume desktop smoke "))
    from docx import Document
    source = directory / "Source with spaces.docx"
    doc = Document()
    for text in ("Alex Example", "alex@example.test", "Professional Summary",
                 "Python developer building APIs.", "Technical Skills", "Python, FastAPI, Docker",
                 "Professional Experience", "Backend Developer | Example Labs | Jan 2022 - Dec 2024",
                 "- Built Python APIs with FastAPI.", "Education", "BSc Computer Science | Example College | 2021"):
        doc.add_paragraph(text)
    doc.save(source)
    env = os.environ.copy()
    env.update(RESUME_DESKTOP_DATA=args.data_dir or str(directory / "data"), PYTHONUNBUFFERED="1",
               HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", RESUME_DESKTOP_DEBUG="1")
    command = [args.worker_exe, "--worker"] if args.worker_exe else [sys.executable, str(ROOT / "desktop/main.py"), "--worker"]
    error_log = (directory / "worker-stderr.log").open("wb")
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=error_log,
                               text=True, encoding="utf-8", env=env,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    alive, peak = True, 0
    def measure():
        nonlocal peak
        while alive:
            try:
                parent = psutil.Process(process.pid)
                peak = max(peak, parent.memory_info().rss + sum(p.memory_info().rss for p in parent.children(recursive=True)))
            except psutil.Error:
                pass
            time.sleep(.1)
    threading.Thread(target=measure, daemon=True).start()
    count = 0
    def request(kind, payload):
        nonlocal count
        count += 1
        start = time.perf_counter()
        process.stdin.write(json.dumps({"job_id": str(count), "kind": kind, "payload": payload}) + "\n")
        process.stdin.flush()
        while True:
            line = process.stdout.readline()
            if not line:
                raise RuntimeError("Worker exited: " + (directory / "worker-stderr.log").read_text(errors="replace"))
            event = json.loads(line)
            if event["status"] == "progress":
                print(event.get("message", "Working"), flush=True)
            if event["status"] == "error":
                raise RuntimeError(event["message"])
            if event["status"] == "complete":
                seconds = round(time.perf_counter() - start, 3)
                result["results"].append({"kind": kind, "seconds": seconds})
                print(kind, seconds, flush=True)
                return event["result"]
    try:
        if args.exports_only:
            document = {"mode": "demo", "jd": "Develop Python APIs using FastAPI and Docker.",
                        "sections": [{"key": "header", "title": "Contact", "text": "Alex Example"},
                                     {"key": "summary", "title": "Summary", "text": "Python engineer delivering Docker APIs."}]}
        else:
            jd_text = Path(args.jd_file).read_text(encoding="utf-8") if args.jd_file else "Requirements\nDevelop Python APIs using FastAPI.\nDeploy using Docker."
            document = request("draft", {"resume": args.resume or str(source), "jd": jd_text, "mode": "demo"})
            (directory / "generated-document.json").write_text(json.dumps(document, indent=2), encoding="utf-8")
        document["sections"].append({"key": "other", "title": "Edited", "text": "EDITED EXPORT CHECK"})
        for kind in ("docx", "html"):
            artifact = request("export", {"document": document, "kind": kind, "destination": str(directory / ("resume." + kind))})
            path = Path(artifact["artifact"])
            assert path.stat().st_size > 100
            if kind == "html":
                assert "EDITED EXPORT CHECK" in path.read_text(encoding="utf-8")
        request("verify", {})
    finally:
        alive = False
        process.stdin.close()
        process.wait(timeout=10)
        error_log.close()
    result["worker_tree_peak_rss_bytes"] = peak
    result["full_generation_tested"] = not args.exports_only
    result["output_directory"] = str(directory)
    target = ROOT / "build/desktop-smoke.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
