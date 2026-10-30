# Windows one-click launcher

Build from the repository on Windows with Python 3.11 or newer:

```powershell
.\launcher\build.ps1
```

Copy `dist\ResumeOptimizerLauncher.exe` to another Windows laptop. The target needs Docker Desktop installed once and internet for the first model, native runner, and Docker image downloads. It does not need Git, Python, or Ollama. The EXE copies itself and the project to `%LOCALAPPDATA%\ResumeOptimizer`, verifies its downloads, starts the GGUF server plus API/n8n services, prepares the existing workflow, and opens the form. The n8n owner account needs one-time browser setup.

Later launches reuse installed files and the downloaded model. The **Stop services** button stops the API, n8n, and native model server. Closing the launcher leaves them running. See [Run locally](../docs/RUN_LOCALLY.md) for setup and troubleshooting.
