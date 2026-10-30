# Run Resume Optimizer on a Windows laptop

## First setup

1. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/), start it, and complete any required Windows restart. The launcher opens this page if Docker is missing.
2. Copy `ResumeOptimizerLauncher.exe` to the laptop and double-click it. You do not need Git, Python, or Ollama on the target laptop.
3. Allow the first-run downloads: the pinned Qwen3.5 4B Q4_K_M GGUF (about 2.7 GB), a native `llama.cpp` runner, and the API/n8n Docker images. Keep at least 12 GB free. The launcher verifies download checksums and resumes an interrupted model download on the next launch.
4. When n8n opens its one-time owner setup, create the owner account, then click **Continue after setup** in the launcher. It imports and publishes the existing workflow and opens the resume form.

On later days, double-click `%LOCALAPPDATA%\ResumeOptimizerCopy\ResumeOptimizerLauncher.exe`. Use **Stop services** in the launcher when finished. Closing its window leaves the application running.

The form is `http://localhost:5679/form/resume-optimize-v2`. Generated files and logs live under `%LOCALAPPDATA%\ResumeOptimizerCopy`. The native server uses NVIDIA CUDA when available, Vulkan on other supported GPUs, and a CPU fallback. CPU fallback and partial GPU offload can be slow on a 4 GB laptop.

The model and runtime are downloaded once; later launches can run offline. The application still needs Docker Desktop because the API and n8n run in containers. The browser form retains its demo generation settings (`fictional_template=true`, `fabrication_mode=demo`, `allow_unverified=true`).

## Build the launcher

On a Windows development PC with Python 3.11 or newer and this repository checked out:

```powershell
.\launcher\build.ps1
```

Copy `dist\ResumeOptimizerLauncher.exe` to a USB drive or the target PC. The EXE contains project source and workflow files; it downloads the pinned model, native runner, and Docker images at first launch.

## Check and troubleshoot

| Symptom | Action |
| --- | --- |
| Docker is missing or not ready | Complete Docker Desktop setup, restart Windows if prompted, then rerun the launcher. |
| A model download was interrupted | Rerun the launcher; it resumes and checks SHA-256 before using the file. |
| Startup reports a GGUF server error | Read `%LOCALAPPDATA%\ResumeOptimizerCopy\logs\launcher.log`. The launcher tries CUDA, then Vulkan, then CPU. |
| The form is unavailable | Check Docker Desktop is running and inspect the launcher log. Complete n8n's one-time owner setup if it appears. |
| Generation is slow | Check whether the launcher reported CUDA, Vulkan, or CPU mode. A 4 GB GPU may offload only part of the Qwen3.5 4B model. |
| Port 8001, 5679, or 18081 is occupied | Close the application using that port, then rerun the launcher. |

The API health page is `http://localhost:8001/health`; it should report `"llm": "up"` and list `qwen3.5:4b`. The native model server is authenticated and is intended for local use by the API. The n8n editor stays at `http://localhost:5679` for the owner.
