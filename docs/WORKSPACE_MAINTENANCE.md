# Current workspace and future updates

## Cleanup on 29 October 2026

At the user's request, obsolete local app bundles and installers, the old 2B model, comparison models, duplicated benchmark assets, temporary build caches, partial downloads and LibreOffice test downloads were removed from this repository. The installed applications and saved resumes under Local AppData were outside this cleanup. Source documents elsewhere on the laptop were not cleanup targets.

The current Project Edition 1.6.1 app, installer and model were preserved. Older documentation records historical tests; paths to superseded builds and rollback installers in those records no longer exist. Keep the current installer as the baseline for the next update. Cleanup does not change the previously recorded performance or quality limitations.

Result: **246 obsolete artifact targets removed, zero removal errors, approximately 70.7 GiB of disk space recovered**. The repository folder now contains approximately **11.1 GiB** (11.9 GB decimal). Logical file sizes include hard-linked copies, so the reduction in reported folder size is larger than the actual recovered disk space. The final worker verified all **161 retained assets**, and the frozen GUI started successfully after cleanup. No tracked source file was deleted; existing working-tree edits were retained.

## Keep these files and folders

- `desktop/`, `api/`, `tests/`, `scripts/`, `docs/` and the other small source/configuration folders: generator, prompts, template, interface, tests and maintenance code. Some older modules are shared dependencies; their presence is not another installed application.
- `.git/`: source history and future code updates. Existing uncommitted changes were preserved.
- `desktop/.venv/`: Python build and test dependencies.
- `build/desktop-assets/`: the selected Qwen3-4B-Instruct-2507 Q4_K_M model, embedding files, CPU/CUDA runtimes, asset checksums and redistribution notices. Do not remove these if you want to rebuild without downloading the assets again.
- `build/llama-source/`, `build/llama-cuda-local/` and the pinned CPU/source archives: native runtime source and build inputs for future runtime changes.
- `build/nsisbi/`: the installer compiler supporting the offline installer size.
- `build/project-latest.json`: current bundle/installer locations and checksums.
- `build/quality-benchmark/`: retained final samples, generation measurements, comparison control measurements and final UI/layout checks. Large redundant benchmark copies were removed.
- `build/model-candidates/`: only the final verification helpers and cancellation result remain; comparison models were removed.
- `dist/projects-evidence-complete/ResumeOptimizerProjects/`: the current directly runnable application.
- `dist/ResumeOptimizerProjectsSetup.exe`, its `.sha256` file and `dist/ResumeOptimizerProjects-manifest.json`: current offline installer and integrity records.
- `data/` and user data outside the repository: preserve saved documents and datasets.

The removal plan and exact results are recorded in `build/cleanup-plan.json` and `build/cleanup-result.json`. `build/cleanup_workspace.ps1` records the audited cleanup rules and defaults to a dry run. Review its keep lists before using it for a future release with different artifact names.

## Run the current application

From the repository root:

```powershell
& '.\dist\projects-evidence-complete\ResumeOptimizerProjects\ResumeOptimizerProjects.exe'
```

Alternatively, use `dist/ResumeOptimizerProjectsSetup.exe` to install this version. Saved Project Edition data normally lives under `%LOCALAPPDATA%\ResumeOptimizerProjectEdition`, or a configured `RESUME_DESKTOP_DATA` path.

## Make and verify future changes

The main pipeline is in `desktop/project_generation.py`, `desktop/generation.py`, `desktop/project_profile.py`, `desktop/project_rules.py` and `desktop/job_brief.py`. The document format is in `desktop/reference_layout.py`. Model/runtime pins are in `desktop/assets.json`; asset downloads are handled by `desktop/prepare_assets.py`. The finetuning Modelfile belongs to the older Ollama workflow, not the current llama.cpp desktop inference runtime.

Run the existing regression checks:

```powershell
& '.\desktop\.venv\Scripts\python.exe' -m pytest desktop/test_generation.py desktop/test_desktop.py desktop/test_project_edition.py desktop/test_project_quality.py desktop/test_project_profile.py desktop/test_general_quality.py desktop/test_reference_release.py desktop/test_evidence_quality.py -q
```

Build a new installer after testing changes:

```powershell
& '.\desktop\build_projects.ps1' -NSISCompiler '.\build\nsisbi\nsisbi-3.12.3\Bin\makensis.exe'
```

Asset preparation may access the internet to refresh notices or obtain changed dependencies. Rebuilding the CUDA runtime requires its documented compiler/toolkit; normal application changes reuse the retained runtime. The build script creates a new bundle and preserves the previous installer before replacement. After validating the next release, review the new manifest before removing superseded outputs.
