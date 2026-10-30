# Set up Resume Optimizer on another Windows PC

## What to copy

Download [ResumeOptimizerLauncher.exe](../downloads/ResumeOptimizerLauncher.exe) from this repository's `main` branch. On GitHub, open the file and select **Download raw file**. You can also copy this EXE to a USB drive or share it in a private Google Drive folder.

The EXE contains the application code and n8n workflow. Do not copy the repository folder, `.env`, generated resumes, `build/`, or `models/` to the other PC.

## First run

1. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) and start it. Complete any Windows restart it requests.
2. Save `ResumeOptimizerLauncher.exe` locally on the Windows PC and double-click it. Keep the PC online and allow at least 12 GB of free disk space. The first run downloads the Qwen3.5 4B GGUF model (about 2.7 GB), a native runner, and Docker images. It verifies the model and runner downloads.
3. If n8n opens its owner-account setup, complete it in the browser, then click **Continue after setup** in the launcher.
4. The launcher opens the form at `http://localhost:5679/form/resume-optimize-v2`. Upload a PDF or DOCX resume, paste the job description, and submit.

Ollama, Python, and Git are not required on the other PC. The browser form retains the current demo fabrication settings.

## Later use

Open `%LOCALAPPDATA%\ResumeOptimizerCopy\ResumeOptimizerLauncher.exe`. The model and application files are reused; no download or n8n setup is needed again. If the services were left running, open `http://localhost:5679/form/resume-optimize-v2` directly for the next resume.

Closing the launcher window leaves the services running. Click **Stop services** to stop the API, n8n, and model server. After stopping them or restarting Windows, double-click the launcher to start them again. Model loading and Docker startup can take from tens of seconds to a few minutes, depending on the PC; generating each new resume takes additional time.

If startup fails, read `%LOCALAPPDATA%\ResumeOptimizerCopy\logs\launcher.log`. See [Run locally](RUN_LOCALLY.md) for more troubleshooting.
