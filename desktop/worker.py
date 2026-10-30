"""NDJSON worker: one owned process, one request at a time, idle model unload."""
from __future__ import annotations

import json
import logging
import queue
import sys
import threading
import time
import traceback

from desktop.bootstrap import DATA, initialize


def run():
    initialize()
    logging.basicConfig(filename=DATA / "logs/worker.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    logging.info("Worker starting")
    import os
    if os.environ.get("RESUME_DESKTOP_DEBUG"):
        import faulthandler
        faulthandler.dump_traceback_later(15, file=sys.stderr)
    # Model helpers import the existing config; initialization must precede it.
    from desktop.runtime import Runtime
    # Initialize native DLLs before starting the blocking stdin-reader thread.
    # Windows CRT initialization can otherwise deadlock on its stdio lock.
    from desktop.draft import export
    from desktop.edition import PROJECT_EDITION
    if PROJECT_EDITION:
        from desktop.project_generation import generate
    else:
        from desktop.generation import generate
    import onnxruntime
    import tokenizers
    runtime = Runtime()
    requests = queue.Queue()
    def read():
        for line in sys.stdin:
            logging.info("Received worker request")
            requests.put(line)
        requests.put(None)
    threading.Thread(target=read, daemon=True).start()
    def emit(job, stage, status, **fields):
        print(json.dumps({"job_id": job, "stage": stage, "status": status, **fields}), flush=True)
    try:
        while True:
            try:
                line = requests.get(timeout=1)
            except queue.Empty:
                runtime.idle()
                continue
            if line is None:
                break
            job = None
            try:
                request = json.loads(line)
                job = request["job_id"]
                progress = lambda stage, message: emit(job, stage, "progress", message=message)
                started = time.perf_counter()
                kind, payload = request["kind"], request["payload"]
                if kind == "draft":
                    result = generate(payload, runtime, progress)
                elif kind == "export":
                    result = export(payload, progress)
                elif kind == "polish":
                    from desktop.polish import polish
                    result = polish(payload, runtime, progress)
                elif kind == "verify":
                    from desktop.runtime import asset_check
                    manifest = json.loads((__import__("desktop.bootstrap", fromlist=["ASSETS"]).ASSETS / "manifest.json").read_text())
                    for item in manifest["files"]:
                        progress("verify", item["path"])
                        asset_check(item["path"])
                    result = {"verified": len(manifest["files"])}
                else:
                    raise ValueError("Unknown worker job.")
                emit(job, kind, "complete", result=result, seconds=round(time.perf_counter() - started, 3))
            except Exception as error:
                logging.error("Job %s failed\n%s", job, traceback.format_exc())
                emit(job, "error", "error", message=str(error))
    finally:
        runtime.stop()
