from __future__ import annotations

import json
import os
import subprocess
import threading
import uuid

import psutil
from PySide6.QtCore import QObject, QTimer, Signal

from desktop.bootstrap import DATA, worker_command


class JobController(QObject):
    event = Signal(dict)
    received = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.active = None
        self.waiting = None
        self.session = None
        self.log = None
        self.owned_job = None
        self.received.connect(self._receive)
        self.monitor = QTimer(self)
        self.monitor.timeout.connect(self._monitor)
        self.monitor.start(250)
        self.peak_rss = 0
        self.lock = threading.Lock()
        self.sampling = False

    def submit(self, kind, payload, revision=0):
        job = {"job_id": uuid.uuid4().hex, "kind": kind, "payload": payload, "revision": revision}
        if self.active:
            if self.waiting:
                self.event.emit({"status": "error", "message": "One job is running and one is waiting. Wait or cancel first."})
                return None
            self.waiting = job
            self.event.emit({"status": "queued", "job_id": job["job_id"], "message": "One job is waiting."})
        else:
            self._start(job)
        return job["job_id"]

    def _spawn(self, session):
        log = (DATA / "logs/worker-stderr.log").open("ab")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        process = subprocess.Popen(worker_command(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=log, text=True, encoding="utf-8", bufsize=1,
                                        creationflags=flags, env=env)
        from desktop.windows_job import OwnedJob
        try:
            owned_job = OwnedJob(process)
        except Exception:
            process.kill()
            log.close()
            raise
        with self.lock:
            if session != self.session:
                owned_job.close()
                process.kill()
                log.close()
                return None
            self.process, self.owned_job, self.log = process, owned_job, log
        def reader():
            for line in process.stdout:
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                item["session"] = session
                self.received.emit(item)
            self.received.emit({"status": "exit", "session": session})
        threading.Thread(target=reader, daemon=True).start()
        return process

    def _start(self, job):
        self.active = job
        if not self.process or self.process.poll() is not None:
            if self.owned_job:
                self.owned_job.close()
            if self.log:
                self.log.close()
            self.process = None
            self.session = uuid.uuid4().hex
        session = self.session
        self.event.emit({"status": "started", "job_id": job["job_id"], "kind": job["kind"]})
        def send():
            try:
                process = self.process or self._spawn(session)
                if process and session == self.session:
                    process.stdin.write(json.dumps(job) + "\n")
                    process.stdin.flush()
            except Exception as error:
                self.received.emit({"status": "error", "job_id": job["job_id"],
                                    "session": session, "message": str(error)})
        # Both Windows executable startup and a full stdin pipe can block.
        # Keep those operations off the Qt event loop.
        threading.Thread(target=send, daemon=True).start()

    def _receive(self, item):
        if item.get("session") != self.session:
            return
        if item["status"] == "memory":
            self.peak_rss = max(self.peak_rss, item["rss"])
            if item["rss"] > 4 * 1024**3:
                self.cancel()
                self.event.emit({"status": "error", "message": "The app reached its 4 GB memory budget. Work was stopped; your draft is saved. Close other applications and try again."})
            return
        if item["status"] == "exit":
            if self.active:
                self.active = None
                self.event.emit({"status": "error", "message": "The background worker stopped. Your saved draft is available; try again."})
            self._advance()
            return
        if not self.active or item.get("job_id") != self.active["job_id"]:
            return
        item["revision"] = self.active["revision"]
        item["kind"] = self.active["kind"]
        item["section"] = self.active["payload"].get("section")
        self.event.emit(item)
        if item["status"] in {"complete", "error"}:
            self.active = None
            self._advance()

    def _advance(self):
        if self.waiting and not self.active:
            job, self.waiting = self.waiting, None
            self._start(job)

    def _monitor(self):
        if not self.process or self.sampling:
            return
        self.sampling = True
        process, session = self.process, self.session
        def sample():
            try:
                root = psutil.Process(process.pid)
                total = psutil.Process().memory_info().rss + root.memory_info().rss
                total += sum(p.memory_info().rss for p in root.children(recursive=True))
                self.received.emit({"status": "memory", "rss": total, "session": session})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            finally:
                self.sampling = False
        threading.Thread(target=sample, daemon=True).start()

    def cancel(self):
        # Acknowledge immediately; stop only this launcher's worker and children.
        with self.lock:
            process, self.process = self.process, None
            self.session = None
        self.active = self.waiting = None
        if process:
            if self.owned_job:
                self.owned_job.close()
                self.owned_job = None
            try:
                children = psutil.Process(process.pid).children(recursive=True)
                for child in reversed(children):
                    try:
                        child.kill()
                    except psutil.Error:
                        pass
                process.kill()
            except (psutil.Error, OSError):
                pass
            # Reaping and stream teardown do not block the UI.
            def reap():
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
                for stream in (process.stdin, process.stdout):
                    if stream:
                        stream.close()
            threading.Thread(target=reap, daemon=True).start()
        if self.log:
            self.log.close()
            self.log = None
        self.event.emit({"status": "cancelled", "message": "Cancelled. Your last saved draft is available."})

    def close(self):
        self.monitor.stop()
        self.cancel()
