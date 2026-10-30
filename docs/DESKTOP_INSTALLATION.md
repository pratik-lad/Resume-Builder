# Project Edition 1.6.3

The repository contains source code and build instructions. Installers and downloaded assets are local build outputs and must be built or obtained separately.

Build with `desktop/build_projects.ps1`; it includes the cross-domain quality
regressions and backs up the previous installer before replacing the latest one.
New versioned metadata does not regenerate existing drafts or overwrite saved edits.
Full fictional generation remains enabled. Mac hosting is a separate, deferred phase.
This release bundles Qwen3-4B-Instruct-2507 Q4_K_M in one offline installer.
See [skill coverage verification](../desktop/SKILL_COMPLETENESS_RESULTS.md) for measured results and remaining quality items. The earlier strict no-slowdown gate failed; generation timing and output quality vary.

# Install or build the Windows desktop application

This guide is for **Resume Optimizer Project Edition 1.6.3** on branch `final-version`.

## 1. Install a complete build on another laptop

1. Obtain `ResumeOptimizerProjectsSetup.exe` and its SHA-256 checksum from the maintainer/build output. This source branch does not contain the installer or GGUF weights, and no GitHub Release download is assumed by these instructions.
2. Check the [requirements](DESKTOP_REQUIREMENTS.md), and close Project Edition before upgrading it.
3. Optionally verify the file in PowerShell against the checksum supplied with that exact build:

   ```powershell
   Get-FileHash -Algorithm SHA256 -LiteralPath '.\ResumeOptimizerProjectsSetup.exe'
   ```

4. Run the installer and open **Resume Optimizer Project Edition** from the desktop or Start menu shortcut. The free build is unsigned, so Windows may show an unknown-publisher prompt; verify the source and checksum before proceeding.
5. Choose a text PDF/DOCX, paste the JD and select **Generate resume**. There is no minimum-free-RAM startup check; the separate running-memory cap remains enabled.
6. Review the preview, select **Edit resume** if needed, then save DOCX and HTML. Generate a fresh resume to use the new pipeline; saved drafts are not regenerated over your edits.

The complete installer includes model/runtime assets, so target installation/use is designed for offline operation. You do not install Python, Docker or n8n and do not configure an API key. Full fabricated professional generation remains enabled; report review notes should be checked before using an export.

## 2. Prepare the developer environment

Install Git and Python 3.11 x64 on Windows. To build the bundled GPU runtime, also install CMake, Visual Studio 2022 Build Tools with Desktop C++/Windows SDK, and CUDA Toolkit 13.3.1. These are free developer tools; installer users only need a compatible NVIDIA driver to use GPU acceleration, or they can use CPU fallback. Use the free NSISBI compiler for this larger model; standard NSIS cannot produce an installer this large. Its official project is <https://sourceforge.net/projects/nsisbi/>. The compiler is a build tool only; target laptops need none of these tools.

Clone the desktop branch into a new directory:

```powershell
git clone --branch final-version --single-branch https://github.com/pratik-lad/Resume-Builder.git
Set-Location Resume-Builder
py -3.11 -m venv desktop\.venv
.\desktop\.venv\Scripts\python.exe -m pip install -r desktop\requirements.txt
.\desktop\.venv\Scripts\python.exe desktop\build_cuda.py --cuda-path "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3"
.\desktop\.venv\Scripts\python.exe desktop\prepare_assets.py
```

Download and verify the pinned portable compiler from the repository root:

```powershell
$tool = Get-Content desktop\installer-toolchain.json -Raw | ConvertFrom-Json
New-Item -ItemType Directory -Force build\nsisbi | Out-Null
$archive = Join-Path (Get-Location) ('build\nsisbi\' + $tool.filename)
Invoke-WebRequest -Uri $tool.url -OutFile $archive -UseBasicParsing
if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $tool.sha256) { throw 'Compiler checksum mismatch' }
Expand-Archive -LiteralPath $archive -DestinationPath build\nsisbi\nsisbi-3.12.3 -Force
```

Initial preparation needs internet and downloads the pinned Qwen GGUF, ONNX/tokenizer assets, CPU/CUDA llama.cpp runtimes and notices. Repeated preparation checks/reuses valid existing files. Assets are kept in `build/desktop-assets`, which Git ignores. No personal resumes, model weights or generated documents need to be uploaded to GitHub.

## 3. Run from source

From the repository root:

```powershell
.\desktop\.venv\Scripts\python.exe desktop\project_main.py
```

Use **project_main.py** for the current Project Edition. `desktop/main.py` is the retained legacy edition entrypoint. Starting the desktop app does not require Docker Compose, the API server or n8n.

## 4. Run checks and build the installer

```powershell
.\desktop\.venv\Scripts\python.exe -m pytest desktop\test_generation.py desktop\test_desktop.py desktop\test_project_edition.py desktop\test_project_quality.py desktop\test_project_profile.py desktop\test_general_quality.py desktop\test_reference_release.py -q
powershell -NoProfile -ExecutionPolicy Bypass -File desktop\build_projects.ps1 -NSISCompiler (Join-Path (Get-Location) 'build\nsisbi\nsisbi-3.12.3\Bin\makensis.exe')
```

The execution-policy option applies to that PowerShell process. The build script prepares/checks assets, runs regressions, creates the PyInstaller directory bundle, and compiles NSIS. It stages the installer before replacing the previous output, retains a backup, and records its actual checksum/version.

Outputs:

- `dist/ResumeOptimizerProjectsSetup.exe`: complete offline installer.
- `dist/ResumeOptimizerProjectsSetup.exe.sha256`: SHA-256 checksum.
- `dist/ResumeOptimizerProjects-manifest.json`: release version, paths, size and checksum.
- `build/project-latest.json`: path to the current generated bundle/installer.
- `dist/projects-<id>/ResumeOptimizerProjects/`: portable directory bundle; copy the **entire** directory if using it directly.

These outputs are local build artifacts and are not committed to this code branch. A maintainer can distribute the complete installer separately after the documented release checks.

## 5. Data, upgrades and backup

Default installed application: `%LOCALAPPDATA%\Programs\ResumeOptimizerProjectEdition`.

Saved data: `%LOCALAPPDATA%\ResumeOptimizerProjectEdition`. It includes drafts, cache, artifacts and logs. Draft JSON can include uploaded source text and the JD. Back up this directory and any exports saved elsewhere before upgrades or moving laptops.

Upgrades replace installation files while keeping user data. Uninstall preserves saved data. The legacy desktop edition uses a separate identity/data directory, so it can coexist. The app owns only its worker/model processes and uses an allocated loopback port.

## 6. Troubleshooting and acceptance checklist

- **Insufficient memory:** close unused apps and retry. Do not reduce the safety threshold to make a benchmark pass.
- **Missing/corrupt model or DLL:** repair the complete installation, or rerun `desktop/prepare_assets.py` in a developer checkout. The installed app does not download replacements automatically.
- **Scanned PDF:** use a text PDF or DOCX; OCR is not included.
- **Slow generation:** CPU inference can take several minutes. Check free RAM and the HTML report; output quality and timing vary by machine.
- **Old layout after upgrade:** existing drafts are preserved. Generate a new resume for the six-bullet Project Edition layout.
- **Unexpected content or metric:** edit the section and re-export. HTML coverage is recalculated from those edits. The local checks are not an external ATS score or factual verification of fictional claims.

Before distribution, verify fresh launch, one full generation, editing/undo/redo, autosave recovery, Cancel, both exports, restart, upgrade, data-preserving uninstall and coexistence. Also complete the physically disconnected clean-Windows test and actual 8 GB reference-laptop benchmark; these remain release gates in the current [test report](../desktop/PROJECT_TEST_RESULTS.md).


## GPU selection, benchmarks and rollback

GPU selection is automatic. The runtime tries full layers with available headroom, then a partial allocation, then CPU. This is layer offloading, not an isolated GPU memory partition. Model ports stay private. For troubleshooting only, launch from PowerShell with `$env:RESUME_MODEL_BACKEND = 'cpu'` to force CPU; remove that environment variable to restore automatic selection.

Model comparison pins are in `desktop/model_candidates.json`. Developer benchmarks use isolated profiles:

```powershell
.\desktop\.venv\Scripts\python.exe desktop\benchmark_quality.py --candidate qwen3 --resume 'C:\path\to\test-resume.docx' --fixtures full-stack,salesforce,java,databricks,aws,azure-genai,qa --label comparison
```

Keep the previous installer before upgrading. Close Project Edition, then run the previous installer to roll back the program files; saved drafts are preserved. Do not manually delete the user-data folder. Rollback installers are local artifacts and are not included in the Git repository.
