"""Manage only this worker's llama.cpp process, with no external service reuse."""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import socket
import subprocess
import time

import httpx
import psutil

from desktop.bootstrap import ASSETS, DATA


def asset_check(relative):
    try:
        manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError("The offline installation manifest is missing or corrupt. Repair the installation.") from error
    item = next((item for item in manifest["files"] if item["path"] == relative), None)
    path = ASSETS / relative
    if item is None or not path.is_file() or path.stat().st_size != item["size"]:
        raise RuntimeError(f"Missing or incomplete offline asset: {relative}. Repair the installation.")
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != item["sha256"]:
        raise RuntimeError(f"Corrupt offline asset: {relative}. Repair the installation.")
    return path


def model_spec():
    """Read the installed selection; old installation manifests remain usable."""
    try:
        manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RuntimeError("The offline installation manifest is missing or corrupt. Repair the installation.") from error
    model = manifest.get("spec", {}).get("model", {})
    filename = model.get("filename", "Qwen3.5-2B-Q4_K_M.gguf")
    if not isinstance(filename, str) or not filename.endswith(".gguf") or any(c in filename for c in "/\\:"):
        raise RuntimeError("The offline model selection is invalid. Repair the installation.")
    return {**model, "filename": filename}


class Runtime:
    def __init__(self):
        self.process = None
        self.client = None
        self.last_used = 0.0
        self.log = None
        self.low_resource = False
        self.model_identity = "unstarted"
        self.model_info = {}
        self.sampling = {}
        self.before_submission = None
        self.request_metrics = []
        self._token_counts = {}

    def start(self, low_resource=False, progress=lambda *args: None):
        if self.process and self.process.poll() is None and self.low_resource == low_resource:
            self.last_used = time.monotonic()
            return
        self.stop()
        progress("model", "Checking offline model and available acceleration")
        executable = asset_check("runtime/llama-server.exe")
        selection = model_spec()
        model = asset_check("models/" + selection["filename"])
        self.model_identity = selection["filename"] + ":" + selection.get("sha256", "legacy")
        self.model_info = {**selection, "context_tokens": 4096, "output_tokens": 768, "backend": "llama.cpp-cpu"}
        self.sampling = {k: v for k, v in selection.get("sampling", {}).items()
                         if k in {"temperature", "top_p", "top_k", "min_p", "presence_penalty", "repeat_penalty"}}
        self.model_identity += ":" + hashlib.sha256(json.dumps(self.sampling, sort_keys=True).encode()).hexdigest()
        manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
        for item in manifest["files"]:
            if item["path"].startswith("runtime/") and item["path"] != "runtime/llama-server.exe":
                asset_check(item["path"])
        key = secrets.token_urlsafe(32)
        physical = psutil.cpu_count(logical=False) or 2
        threads = 1 if low_resource else max(1, min(4, physical - 1))
        self.low_resource = low_resource
        # Do not bind until executable/model verification has completed. A race
        # is handled by server failure, never by connecting to the occupying app.
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.log = (DATA / "logs/model.log").open("ab")
        args = [str(executable), "-m", str(model), "--alias", "desktop-qwen",
                "--host", "127.0.0.1", "--port", str(port), "--api-key", key,
                "-c", "4096", "-np", "1", "-t", str(threads), "-tb", str(threads),
                "-b", "256", "-ub", "64", "--cache-ram", "0",
                "-ngl", "0", "--no-webui", "-lv", "4"]
        if selection.get("disable_repacking", False):
            # Avoid simultaneous mapped and repacked weight copies on 8 GB PCs.
            args.append("--no-repack")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)
        candidates = [(executable, 0)]
        cuda = ASSETS / 'runtime-cuda/llama-server.exe'
        if cuda.exists() and not low_resource and os.environ.get('RESUME_MODEL_BACKEND', 'auto') != 'cpu':
            try:
                probe = subprocess.run(['nvidia-smi', '--query-gpu=memory.free', '--format=csv,noheader,nounits'],
                                       capture_output=True, text=True, timeout=5, creationflags=flags)
                free = max(int(v.strip()) for v in probe.stdout.splitlines())
                if probe.returncode == 0 and free >= 1024:
                    for item in manifest['files']:
                        if item['path'].startswith('runtime-cuda/'):
                            asset_check(item['path'])
                    cuda = asset_check('runtime-cuda/llama-server.exe')
                    # Model layer count is pinned in the selection; unknown
                    # architectures use a conservative partial-load attempt.
                    half = max(1, int(selection.get('layers', 32)) // 2)
                    candidates = ([(cuda, 999)] if free * 1024**2 > model.stat().st_size + 768*1024**2 else []) + [(cuda, half), (executable, 0)]
            except (OSError, ValueError, subprocess.SubprocessError):
                pass
        for runner, layers in candidates:
            launch = list(args)
            launch[0] = str(runner)
            launch[launch.index('-ngl') + 1] = str(layers)
            offset = self.log.tell()
            try:
                self.process = subprocess.Popen(launch, cwd=runner.parent, stdout=self.log, stderr=self.log,
                                                creationflags=flags)
            except OSError:
                progress('model', 'Runtime unavailable; trying the compatible fallback')
                continue
            self.client = httpx.Client(base_url=f"http://127.0.0.1:{port}",
                                       headers={"Authorization": f"Bearer {key}"}, timeout=180, trust_env=False)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    break
                try:
                    if self.client.get('/health', timeout=1).is_success and self._owns_listener(port):
                        self.last_used = time.monotonic()
                        with (DATA / 'logs/model.log').open('rb') as log:
                            log.seek(offset)
                            text = log.read().decode('utf-8', errors='replace')
                        actual = re.findall(r'offloaded (\d+)/(\d+) layers', text)
                        if layers and not (actual and int(actual[-1][0]) > 0):
                            break
                        self.model_info.update(backend='llama.cpp-cuda' if layers else 'llama.cpp-cpu',
                                               requested_gpu_layers=layers,
                                               offloaded_layers=int(actual[-1][0]) if actual else 0,
                                               runtime=manifest.get('spec',{}).get('cuda_runtime' if layers else 'runtime',{}))
                        progress('model', 'Model ready: ' + self.model_info['backend'])
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(.2)
            self.client.close()
            self.client = None
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=3)
            self.process = None
            progress('model', 'Trying the next compatible runtime configuration')
        self.stop()
        raise RuntimeError('The local model could not start with GPU or CPU fallback. Check logs/model.log.')

    def _owns_listener(self, port):
        try:
            return any(connection.status == psutil.CONN_LISTEN and connection.laddr.port == port
                       for connection in psutil.Process(self.process.pid).net_connections(kind="tcp"))
        except psutil.Error:
            return False

    def token_count(self, messages):
        key = json.dumps(messages, ensure_ascii=False, sort_keys=True)
        if key in self._token_counts:
            return self._token_counts[key]
        response = self.client.post("/apply-template", json={
            "messages": messages, "add_generation_prompt": True,
            "chat_template_kwargs": {"enable_thinking": False}})
        response.raise_for_status()
        prompt = response.json()["prompt"]
        response = self.client.post("/tokenize", json={"content": prompt, "add_special": True})
        response.raise_for_status()
        count = len(response.json()["tokens"])
        if len(self._token_counts) >= 128:
            self._token_counts.pop(next(iter(self._token_counts)))
        self._token_counts[key] = count
        return count

    def chat(self, messages, json_output=False, seed=42):
        count = self.token_count(messages)
        if count + 768 > 4096:
            raise ValueError("This request is too long for the model context. Shorten the job description and try again.")
        self.last_used = time.monotonic()
        for attempt in range(2):
            try:
                body = {
                    "model": "desktop-qwen", "messages": messages, "stream": False,
                    "max_tokens": 768, "temperature": .35 if json_output else .15, "seed": seed,
                    "reasoning_effort": "none", "chat_template_kwargs": {"enable_thinking": False}}
                body.update(self.sampling)
                if json_output:
                    body["response_format"] = {"type": "json_object"}
                    if isinstance(json_output, dict):
                        body["response_format"]["schema"] = json_output
                if self.before_submission:
                    self.before_submission()
                started = time.perf_counter()
                response = self.client.post("/v1/chat/completions", json=body)
                response.raise_for_status()
                data = response.json()
                if os.environ.get("RESUME_TRACE_MODEL") == "1":
                    trace = DATA / "logs" / ("request-" + str(time.time_ns()) + ".json")
                    trace.write_text(json.dumps({"messages": messages, "response": data}, indent=2), encoding="utf-8")
                self.request_metrics.append({'seconds': round(time.perf_counter()-started, 3),
                                             'input_tokens': count, 'usage': data.get('usage', {}),
                                             'finish_reason': data['choices'][0].get('finish_reason')})
                if data["choices"][0].get("finish_reason") == "length":
                    raise ValueError("Model output reached its limit. Return a shorter complete JSON response.")
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPError:
                if attempt:
                    raise RuntimeError("The local model request failed twice. Your draft was kept; try again.")
                time.sleep(.25)
            finally:
                self.last_used = time.monotonic()

    def idle(self):
        if self.process and time.monotonic() - self.last_used >= 300:
            self.stop()

    def stop(self):
        self._token_counts.clear()
        if self.client:
            self.client.close()
            self.client = None
        if self.process:
            process, self.process = self.process, None
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
        if self.log:
            self.log.close()
            self.log = None
