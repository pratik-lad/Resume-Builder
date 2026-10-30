from __future__ import annotations

import hashlib
import json
import os
import queue
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
import zipfile
from pathlib import Path
from tkinter import BOTH, NORMAL, DISABLED, StringVar, Tk, messagebox, ttk


APP_NAME = "ResumeOptimizerCopy"
APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
APP_ROOT = APP_DIR / "app"
LOG_DIR = APP_DIR / "logs"
LOG_FILE = LOG_DIR / "launcher.log"
MODEL_NAME = "qwen3.5:4b"
MODEL_FILE = APP_DIR / "models" / "Qwen3.5-4B-Q4_K_M.gguf"
MODEL_SIZE = 2740937888
MODEL_SHA256 = "00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4"
MODEL_REVISION = "e87f176479d0855a907a41277aca2f8ee7a09523"
MODEL_URL = ("https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/resolve/"
             f"{MODEL_REVISION}/Qwen3.5-4B-Q4_K_M.gguf")
LLAMA_VERSION = "b11316"
LLAMA_PORT = 18081
LLAMA_LOCAL_URL = f"http://127.0.0.1:{LLAMA_PORT}"
LLAMA_DIR = APP_DIR / "runtime" / LLAMA_VERSION
LLAMA_ASSETS = {
    "cuda": [
        (f"llama-{LLAMA_VERSION}-bin-win-cuda-12.4-x64.zip",
         "9fb6171bb56b62babe440c1f0d2cc6f4a198dc056d5b861a2c33b00db0ac39eb", 263389298),
        ("cudart-llama-bin-win-cuda-12.4-x64.zip",
         "8c79a9b226de4b3cacfd1f83d24f962d0773be79f1e7b75c6af4ded7e32ae1d6", 391443627),
    ],
    "vulkan": [(f"llama-{LLAMA_VERSION}-bin-win-vulkan-x64.zip",
                "2d84b2b44ce88faf86e7d913d543c611d09901be28a937b890e59704e86d1c34", 33196401)],
    "cpu": [(f"llama-{LLAMA_VERSION}-bin-win-cpu-x64.zip",
             "809b187007d198f22f82284a79dc02cdb6c4e149df61441702b9fcf7ef966fe3", 19265507)],
}
WORKFLOW_ID = "K8mQ2vR7xN4pT9wZ"
N8N_VERSION = "2.39.6"
FORM_URL = "http://localhost:5679/form/resume-optimize-v2"
SETUP_URL = "http://localhost:5679/setup"
COMPOSE_FILES = ("docker-compose.yml", "docker-compose.launcher.yml")
DOCKER_INSTALL_URL = "https://docs.docker.com/desktop/setup/install/windows-install/"

class LauncherError(RuntimeError):
    pass


def runtime_bundle_path() -> Path:
    """Find the embedded runtime bundle in a PyInstaller build or source checkout."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "runtime-bundle.zip"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent / "build" / "runtime-bundle.zip"


def workflow_ids(output: str) -> set[str]:
    return {line.strip() for line in output.splitlines() if line.strip()}


def needs_setup(imported_ids: set[str]) -> bool:
    return WORKFLOW_ID not in imported_ids


def install_local_launcher() -> Path | None:
    """Copy the one-file EXE off removable media for later launches."""
    if not getattr(sys, "frozen", False):
        return None
    target = APP_DIR / "ResumeOptimizerLauncher.exe"
    source = Path(sys.executable).resolve()
    if source == target.resolve():
        return None
    APP_DIR.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".new")
    shutil.copy2(source, temporary)
    os.replace(temporary, target)
    return target


def port_is_listening(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _find_executable(name: str, known_paths: list[Path]) -> Path | None:
    found = shutil.which(name)
    if found:
        return Path(found)
    for path in known_paths:
        if path.is_file():
            return path
    return None


def docker_executable() -> Path | None:
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    return _find_executable(
        "docker",
        [program_files / "Docker" / "Docker" / "resources" / "bin" / "docker.exe"],
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download_verified(url: str, target: Path, digest: str, size: int, notify) -> None:
    """Resume a first-run download and install only after size and SHA-256 match."""
    if target.is_file() and target.stat().st_size == size and sha256_file(target) == digest:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    offset = partial.stat().st_size if partial.exists() else 0
    if offset >= size:
        if offset == size and sha256_file(partial) == digest:
            os.replace(partial, target)
            return
        partial.unlink()
        offset = 0
    required = max(0, size - offset)
    if shutil.disk_usage(target.parent).free < required + 256 * 1024 * 1024:
        raise LauncherError(f"Not enough free disk space to download {target.name}.")
    headers = {"Range": f"bytes={offset}-"} if offset else {}
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            if offset and response.status != 206:
                offset = 0
            elif offset:
                content_range = response.headers.get("Content-Range", "")
                if not content_range.startswith(f"bytes {offset}-"):
                    raise LauncherError(f"The server returned an unexpected download range for {target.name}.")
            mode = "ab" if offset else "wb"
            with partial.open(mode) as output:
                received = offset
                next_report = 0
                while True:
                    block = response.read(4 * 1024 * 1024)
                    if not block:
                        break
                    output.write(block)
                    received += len(block)
                    percent = int(received * 100 / size)
                    if percent >= next_report:
                        notify(f"Downloading {target.name}: {percent}%")
                        next_report = percent + 10
    except (OSError, urllib.error.URLError) as error:
        raise LauncherError(f"Download paused for {target.name}: {error}. Run the launcher again to resume.") from error
    if partial.stat().st_size != size or sha256_file(partial) != digest:
        partial.unlink(missing_ok=True)
        raise LauncherError(f"Download integrity check failed for {target.name}. Run the launcher again.")
    os.replace(partial, target)


class Launcher:
    def __init__(self, notify, wait_for_setup: threading.Event):
        self.notify = notify
        self.wait_for_setup = wait_for_setup
        self.docker = docker_executable()
        self.llm_process: subprocess.Popen | None = None
        self.compose_env = os.environ.copy()
        self.compose_env["COMPOSE_PROJECT_NAME"] = "resume-optimizer-copy"
        self._log_lock = threading.Lock()
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.log = LOG_FILE.open("a", encoding="utf-8", errors="replace")

    def close(self):
        self.log.close()

    def _write_log(self, line: str):
        with self._log_lock:
            self.log.write(line.rstrip() + "\n")
            self.log.flush()

    def _run(self, args: list[str], *, cwd: Path | None = None, check: bool = True,
             env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
        command = [str(part) for part in args]
        self._write_log("$ " + subprocess.list2cmdline(command))
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.stdout:
            self._write_log(result.stdout)
        if check and result.returncode:
            text = result.stdout[-1800:].strip()
            raise LauncherError(text or f"Command failed with exit code {result.returncode}.")
        return result

    def install_runtime(self):
        bundle = runtime_bundle_path()
        if not bundle.is_file():
            raise LauncherError("The embedded project files are missing from the launcher.")
        digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
        marker = APP_ROOT / ".launcher-bundle.sha256"
        if marker.is_file() and marker.read_text(encoding="utf-8").strip() == digest:
            self._write_log(f"Runtime bundle already installed: {digest}")
            return False

        APP_ROOT.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(bundle) as archive:
            for info in archive.infolist():
                relative = Path(info.filename)
                if relative.is_absolute() or ".." in relative.parts:
                    raise LauncherError("The launcher contains an invalid project path.")
                if not info.is_dir() and relative.as_posix() == ".env":
                    continue
                target = APP_ROOT / relative
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(info) as source, target.open("wb") as dest:
                        shutil.copyfileobj(source, dest)
        env_path = APP_ROOT / ".env"
        if not env_path.exists():
            shutil.copy2(APP_ROOT / ".env.example", env_path)
        for relative in ("data/runs", "data/datasets", "data/eval", "data/evaluation", "data/cache", "data/jds"):
            (APP_ROOT / relative).mkdir(parents=True, exist_ok=True)
        marker.write_text(digest, encoding="utf-8")
        return True

    def _wait_http(self, url: str, timeout: int, label: str, accept_error: bool = False):
        deadline = time.monotonic() + timeout
        last_error = "not reachable yet"
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    if response.status < 500:
                        return response.status
            except urllib.error.HTTPError as error:
                if accept_error and error.code < 500:
                    return error.code
                last_error = f"HTTP {error.code}"
            except Exception as error:
                last_error = str(error)
            time.sleep(2)
        raise LauncherError(f"{label} did not become ready in time ({last_error}).")

    def _start_docker(self):
        if not self.docker:
            webbrowser.open(DOCKER_INSTALL_URL)
            raise LauncherError(
                "Docker Desktop was not found. Its official setup page is open. Install it, restart if requested, then run this launcher again."
            )
        self.notify("Starting Docker Desktop…")
        ready = self._run([self.docker, "info"], check=False)
        if ready.returncode == 0:
            return
        candidates = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Docker" / "Docker" / "Docker Desktop.exe",
            Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Docker" / "Docker" / "Docker Desktop.exe",
        ]
        desktop = next((path for path in candidates if path.is_file()), None)
        if desktop:
            subprocess.Popen([str(desktop)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            time.sleep(3)
            if self._run([self.docker, "info"], check=False).returncode == 0:
                return
        raise LauncherError("Docker Desktop did not start. Open Docker Desktop, wait until it says Running, then run the launcher again.")

    def _env_values(self) -> dict[str, str]:
        values = {}
        for line in (APP_ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
        return values

    def _ensure_llm_env(self) -> tuple[str, int]:
        path = APP_ROOT / ".env"
        values = self._env_values()
        additions = {}
        if not values.get("LLM_API_KEY"):
            additions["LLM_API_KEY"] = secrets.token_urlsafe(32)
        if not values.get("LLM_HOST"):
            additions["LLM_HOST"] = f"http://host.docker.internal:{LLAMA_PORT}"
        if not values.get("LLM_REVISION"):
            additions["LLM_REVISION"] = f"unsloth-qwen3.5-4b-q4_k_m-{MODEL_REVISION[:8]}"
        if additions:
            lines = path.read_text(encoding="utf-8").splitlines()
            replaced = set()
            for index, line in enumerate(lines):
                if "=" not in line or line.lstrip().startswith("#"):
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if key in additions and not value.strip():
                    lines[index] = f"{key}={additions[key]}"
                    replaced.add(key)
            lines.extend(f"{key}={value}" for key, value in additions.items() if key not in replaced)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            values.update(additions)
        context = int(values.get("NUM_CTX", "8192"))
        if context < 8192:
            raise LauncherError("NUM_CTX is below the current 8192-token project setting; restore that value in .env.")
        return values["LLM_API_KEY"], context

    def _install_backend(self, backend: str) -> Path:
        assets = LLAMA_ASSETS[backend]
        digest = ":".join(item[1] for item in assets)
        destination = LLAMA_DIR / backend
        executable = destination / "llama-server.exe"
        marker = destination / ".archive-sha256"
        if executable.is_file() and marker.is_file() and marker.read_text(encoding="utf-8").strip() == digest:
            return executable
        destination.mkdir(parents=True, exist_ok=True)
        for name, asset_digest, size in assets:
            archive_path = LLAMA_DIR / "downloads" / name
            url = f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_VERSION}/{name}"
            download_verified(url, archive_path, asset_digest, size, self.notify)
            with zipfile.ZipFile(archive_path) as archive:
                for info in archive.infolist():
                    relative = Path(info.filename)
                    if relative.is_absolute() or ".." in relative.parts:
                        raise LauncherError("The native runner archive contains an invalid path.")
                archive.extractall(destination)
        if not executable.is_file():
            raise LauncherError("The native runner archive did not contain llama-server.exe.")
        marker.write_text(digest, encoding="utf-8")
        return executable

    def _gpu_device(self, executable: Path) -> str | None:
        result = self._run([executable, "--list-devices"], check=False)
        if result.returncode:
            return None
        devices = re.findall(r"^\s*(Vulkan\d+):\s*(.+)$", result.stdout, re.MULTILINE)
        if not devices:
            return None
        return next((name for name, description in devices if "NVIDIA" in description.upper()),
                    devices[0][0])

    def _ensure_model(self):
        self.notify("Checking the Qwen3.5 4B GGUF model...")
        download_verified(MODEL_URL, MODEL_FILE, MODEL_SHA256, MODEL_SIZE, self.notify)

    def _start_llama(self, api_key: str, context: int):
        if port_is_listening(LLAMA_PORT):
            try:
                request = urllib.request.Request(f"{LLAMA_LOCAL_URL}/v1/models",
                                                 headers={"Authorization": f"Bearer {api_key}"})
                with urllib.request.urlopen(request, timeout=5) as response:
                    names = [item.get("id") for item in json.load(response).get("data", [])]
                if MODEL_NAME in names:
                    self.notify("Using the already running GGUF model server.")
                    return
            except Exception:
                pass
            raise LauncherError(f"Port {LLAMA_PORT} is occupied by another model server or application.")

        nvidia_exe = shutil.which("nvidia-smi")
        nvidia = self._run([nvidia_exe, "--query-gpu=name", "--format=csv,noheader"], check=False) if nvidia_exe else None
        choices = (["cuda"] if nvidia and nvidia.returncode == 0 and nvidia.stdout.strip() else []) + ["vulkan", "cpu"]
        for backend in choices:
            executable = self._install_backend(backend)
            gpu = self._gpu_device(executable) if backend == "vulkan" else ("NVIDIA CUDA" if backend == "cuda" else None)
            if backend == "vulkan" and not gpu:
                continue
            self.notify(f"Starting GGUF model on {gpu or 'CPU'}...")
            args = [str(executable), "--model", str(MODEL_FILE), "--alias", MODEL_NAME,
                    "--host", "0.0.0.0", "--port", str(LLAMA_PORT),
                    "--ctx-size", str(context), "--fit", "on", "--fit-ctx", str(context),
                    "--reasoning", "off", "--parallel", "1", "--no-webui"]
            if backend == "vulkan":
                args.extend(["--device", gpu, "--n-gpu-layers", "auto"])
            elif backend == "cuda":
                args.extend(["--n-gpu-layers", "auto"])
            else:
                args.extend(["--device", "none", "--n-gpu-layers", "0"])
            environment = os.environ.copy()
            environment["LLAMA_API_KEY"] = api_key
            self._write_log(f"Starting {backend} GGUF server; device={gpu or 'CPU'}, context={context}")
            self.llm_process = subprocess.Popen(args, cwd=str(executable.parent), env=environment,
                                                stdout=self.log, stderr=self.log,
                                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                if self.llm_process.poll() is not None:
                    break
                try:
                    with urllib.request.urlopen(f"{LLAMA_LOCAL_URL}/health", timeout=2) as response:
                        if json.load(response).get("status") == "ok":
                            (APP_DIR / "llama-server.pid").write_text(str(self.llm_process.pid), encoding="utf-8")
                            return
                except Exception:
                    time.sleep(2)
            if self.llm_process.poll() is None:
                self.llm_process.terminate()
                try:
                    self.llm_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.llm_process.kill()
                    self.llm_process.wait(timeout=10)
            self._write_log(f"The {backend} GGUF server did not start; trying the next backend.")
        raise LauncherError("The GGUF model server could not load the model on GPU or CPU. See launcher.log.")

    def _compose(self, *args: str, check: bool = True):
        return self._run(
            [self.docker, "compose", "-p", "resume-optimizer-copy", "-f", *COMPOSE_FILES, *args],
            cwd=APP_ROOT,
            check=check,
            env=self.compose_env,
        )

    def _assert_ports_available(self):
        for port, service in ((8001, "api"), (5679, "n8n")):
            if not port_is_listening(port):
                continue
            running = self._compose("ps", "--status", "running", "-q", service, check=False)
            if running.returncode == 0 and running.stdout.strip():
                continue
            raise LauncherError(
                f"Port {port} is already in use, so the {service} service cannot start. Close the app using port {port} and retry."
            )

    def _workflow_lists(self) -> tuple[set[str], set[str]]:
        all_result = self._compose("exec", "-T", "n8n", "n8n", "list:workflow", "--onlyId", check=False)
        if all_result.returncode:
            raise LauncherError("Could not check n8n workflows. See launcher.log for details.")
        active_result = self._compose("exec", "-T", "n8n", "n8n", "list:workflow", "--active=true", "--onlyId", check=False)
        active = workflow_ids(active_result.stdout) if active_result.returncode == 0 else set()
        return workflow_ids(all_result.stdout), active

    def _finish_workflow(self):
        self.notify("Checking the n8n workflow...")
        imported, active = self._workflow_lists()
        if needs_setup(imported):
            self.notify("Complete n8n's one-time setup in your browser, then choose Continue here.")
            webbrowser.open(SETUP_URL)
            self.wait_for_setup.wait()
            self.notify("Importing and publishing the resume workflow...")
            self._compose("exec", "-T", "n8n", "n8n", "import:workflow",
                          "--input=/workflows/resume-optimize.json")
            self._compose("exec", "-T", "n8n", "n8n", "publish:workflow", f"--id={WORKFLOW_ID}")
            self._compose("restart", "n8n")
        elif WORKFLOW_ID not in active:
            self.notify("Publishing the resume workflow...")
            self._compose("exec", "-T", "n8n", "n8n", "publish:workflow", f"--id={WORKFLOW_ID}")
            self._compose("restart", "n8n")

    def start(self):
        try:
            self.notify("Installing project files…")
            updated = self.install_runtime()
            self._start_docker()
            api_key, context = self._ensure_llm_env()
            self._ensure_model()
            self._start_llama(api_key, context)
            self._assert_ports_available()
            self.notify(f"Starting the API and n8n {N8N_VERSION}...")
            arguments = ("up", "--detach", "--build", "--remove-orphans") if updated else (
                "up", "--detach", "--remove-orphans")
            self._compose(*arguments)
            self._wait_http("http://127.0.0.1:8001/health", 900, "Resume Optimizer API")
            with urllib.request.urlopen("http://127.0.0.1:8001/health", timeout=10) as response:
                health = json.load(response)
            if health.get("llm") != "up" or MODEL_NAME not in health.get("models", []):
                raise LauncherError(f"The API cannot reach its GGUF model server: {health.get('error', health)}")
            self._wait_http("http://127.0.0.1:5679/", 180, "n8n", accept_error=True)
            self._finish_workflow()
            self._wait_http(FORM_URL, 180, "Resume Optimizer form")
            self.notify(("success", "Resume Optimizer is running."))
        except Exception as error:
            self._write_log(f"ERROR: {error}")
            self.notify(("error", str(error)))

    def stop(self):
        self._compose("stop")
        pid_file = APP_DIR / "llama-server.pid"
        if pid_file.is_file():
            try:
                pid = int(pid_file.read_text(encoding="utf-8").strip())
                listing = self._run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], check=False)
                if "llama-server.exe" in listing.stdout.lower():
                    self._run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False)
            finally:
                pid_file.unlink(missing_ok=True)


class LauncherWindow:
    def __init__(self):
        self.root = Tk()
        self.root.title("Resume Optimizer")
        self.root.geometry("500x205")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.events: queue.Queue = queue.Queue()
        self.setup_continue = threading.Event()
        self.status = StringVar(value="Starting…")
        frame = ttk.Frame(self.root, padding=22)
        frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="Resume Optimizer", font=("Segoe UI", 15, "bold")).pack(anchor="w")
        ttk.Label(frame, textvariable=self.status, wraplength=450).pack(anchor="w", pady=(12, 10))
        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=450)
        self.progress.pack(fill="x")
        self.actions = ttk.Frame(frame)
        self.actions.pack(anchor="e", pady=(16, 0))
        self.continue_button = ttk.Button(self.actions, text="Continue after setup", command=self.continue_setup, state=DISABLED)
        self.continue_button.pack(side="left", padx=(0, 8))
        self.form_button = ttk.Button(self.actions, text="Open resume form", command=lambda: webbrowser.open(FORM_URL), state=DISABLED)
        self.form_button.pack(side="left", padx=(0, 8))
        self.stop_button = ttk.Button(self.actions, text="Stop services", command=self.stop_services, state=DISABLED)
        self.stop_button.pack(side="left", padx=(0, 8))
        self.close_button = ttk.Button(self.actions, text="Close", command=self.close)
        self.close_button.pack(side="left")
        self.progress.start(12)
        self.worker = threading.Thread(target=self._work, daemon=True)
        self.worker.start()
        self.root.after(100, self._process_events)

    def _notify(self, value):
        self.events.put(value)

    def _work(self):
        try:
            launcher = Launcher(self._notify, self.setup_continue)
            try:
                launcher.start()
            finally:
                launcher.close()
        except Exception as error:
            self._notify(("error", str(error)))

    def continue_setup(self):
        self.continue_button.configure(state=DISABLED)
        self.setup_continue.set()

    def stop_services(self):
        self.stop_button.configure(state=DISABLED)
        self.status.set("Stopping the application...")
        threading.Thread(target=self._stop_work, daemon=True).start()

    def _stop_work(self):
        launcher = Launcher(self._notify, threading.Event())
        try:
            launcher.stop()
            self._notify(("stopped", "Resume Optimizer has stopped."))
        except Exception as error:
            self._notify(("error", str(error)))
        finally:
            launcher.close()

    def _process_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                if isinstance(event, tuple) and event[0] == "success":
                    self.progress.stop()
                    self.progress.configure(mode="determinate", value=100)
                    self.status.set(f"{event[1]} You can remove the USB drive; use {APP_DIR / 'ResumeOptimizerLauncher.exe'} next time.")
                    self.form_button.configure(state=NORMAL)
                    self.stop_button.configure(state=NORMAL)
                    webbrowser.open(FORM_URL)
                elif isinstance(event, tuple) and event[0] == "stopped":
                    self.status.set(event[1])
                    self.form_button.configure(state=DISABLED)
                elif isinstance(event, tuple) and event[0] == "error":
                    self.progress.stop()
                    self.progress.configure(mode="determinate", value=0)
                    self.status.set("Startup stopped. The error details are saved in the launcher log.")
                    messagebox.showerror("Resume Optimizer could not start", f"{event[1]}\n\nLog file:\n{LOG_FILE}", parent=self.root)
                elif event == "Complete n8n's one-time setup in your browser, then choose Continue here.":
                    self.status.set(event)
                    self.continue_button.configure(state=NORMAL)
                else:
                    self.status.set(str(event))
        except queue.Empty:
            pass
        self.root.after(100, self._process_events)

    def close(self):
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    if os.name != "nt":
        raise SystemExit("This launcher is built for Windows.")
    try:
        local_launcher = install_local_launcher()
        if local_launcher:
            subprocess.Popen([str(local_launcher)], cwd=str(local_launcher.parent),
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return
    except OSError:
        # If copying to the profile fails, still allow this run from the original EXE.
        pass
    LauncherWindow().run()


if __name__ == "__main__":
    main()
