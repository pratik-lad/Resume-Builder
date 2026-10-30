# Desktop application requirements

Applies to Project Edition 1.6.3 on branch `final-version`.
Mac hosting and Metal acceleration are planned for Phase 2 after quality approval;
they are not required or included in this Windows quality release.

## Laptops running the installer

| Item | Requirement or current behavior |
| --- | --- |
| Operating system | Windows 11 x64; Windows ARM and macOS are not release targets |
| Memory | 8 GB target; no minimum-free-RAM startup threshold; combined running-memory cap remains 4 GiB |
| CPU | x64 CPU; four physical cores are the reference target; default inference uses at most four threads |
| Graphics | CPU fallback requires no dedicated GPU; the speed target is measured on RTX 3050 6 GB with a compatible NVIDIA driver |
| Storage | SSD recommended; allow at least 12 GB free for the installer, installed files and temporary work, plus room for drafts/exports |
| Internet | Required to obtain the installer; the complete installer is designed to install and run offline |
| Accounts | No cloud subscription, account or paid LLM API required |
| Input | Text PDF or DOCX up to 25 MiB; identifiable education section; scanned PDFs need conversion because OCR is not included |
| Output | DOCX resume and HTML report; use a compatible viewer to open them |

Python, Docker, n8n, Git and NSIS are **developer tools**, not requirements for target users receiving the complete installer. No `.env` file is needed by this desktop entrypoint.

The controller monitors combined interface/worker/child-process RSS and stops a job observed above 4 GiB. Windows also limits worker/model committed memory to 4 GiB and kills owned children on close. GPU driver backing allocations count toward that commit limit; the separate RSS monitor measures resident host RAM, including the GUI. These safeguards are not an operating-system RAM reservation. Close large applications before generation. There is no free-memory preflight rejection.

The historical 1.1.0 benchmark used a Windows 11 x64 host with approximately 16 GB RAM and 10 physical cores, limited to four inference threads. It measured 392.31 seconds, 22 model calls and 2.15 GiB peak RSS. This does not establish the same performance on an 8 GB laptop; that hardware benchmark remains pending.

Current measurements, model comparisons and limitations are in [QUALITY_REFERENCE_RESULTS.md](../desktop/QUALITY_REFERENCE_RESULTS.md).

## Developers building from source

- Windows x64, Python **3.11 x64**, Git, and PowerShell.
- Free **NSISBI 3.12.3** compiler for the all-in-one installer with a 2.50 GB model. Standard NSIS has a 2 GiB installer limit. See `desktop/installer-toolchain.json` and the installation guide for the pinned archive and checksum.
- CMake, Visual Studio 2022 Build Tools with C++/Windows SDK, and CUDA Toolkit 13.3.1 for the pinned-source CUDA runtime. The current native build includes sm_86 plus forward PTX; RTX 30-series is the validated baseline.
- Internet during initial dependency and asset preparation. Downloaded files are pinned and checked against hashes/sizes.
- At least **40 GB free disk** recommended for a virtual environment, model assets, temporary packaging files and installer copies. This is a build-space allowance, not a measured runtime requirement.
- Install dependencies from `desktop/requirements.txt`; `desktop/requirements.lock` constrains the validated environment. The separate `api/requirements.txt` is for the web deployment and is not the desktop installation command.

| Technology | Declared version / use |
| --- | --- |
| PySide6 | 6.8.3, native Qt interface |
| PyInstaller | 6.15.0, directory-bundle packaging |
| HTTPX | 0.28.1, owned loopback model requests |
| psutil | 7.0.0, CPU and memory/process monitoring |
| PyMuPDF | 1.25.1, PDF parsing |
| python-docx | 1.1.2, DOCX parsing/rendering |
| ONNX Runtime | 1.20.1, bundled embedding adapter |
| tokenizers / NumPy | 0.21.0 / 2.2.1 |
| pytest | 8.3.4, regression checks |

## Bundled models and runtime

- **Text generation:** `unsloth/Qwen3-4B-Instruct-2507-GGUF`, file `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`; revision `a06e946bb6b655725eafa393f4a9745d460374c9`. File size 2,497,281,120 bytes (2.50 GB / 2.33 GiB); this is not the application's RAM requirement. SHA-256: `3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597`.
- **Inference:** llama.cpp Windows CPU x64, build `b11316`; one 4,096-token slot and at most 768 output tokens per request. CUDA layer offloading is automatic on compatible NVIDIA devices; CPU fallback remains available. Reasoning is disabled.
- **Memory:** weight repacking is disabled for the selected 4B model to avoid duplicate weight buffers. The combined 4 GiB running-memory monitor remains enabled; no minimum-free-RAM startup gate is added. See [model upgrade results](../desktop/MODEL_UPGRADE_RESULTS.md) for measured use and remaining release gates.
- **Embedding assets:** quantized ONNX `Xenova/bge-small-en-v1.5`, revision `ea104dacec62c0de699686887e3f920caeb4f3e3`. These support the older matching path; the current Project Edition generation/evidence path uses scoped prompts and local text rules.
- Exact filenames, sizes and checksums are in `desktop/assets.json`. `desktop/prepare_assets.py` downloads and verifies them into ignored `build/desktop-assets/`.

Do not commit downloaded GGUF/ONNX weights, virtual environments, installers, `.env` files, source resumes or generated artifacts. Bundled redistribution notices are collected by asset preparation; see `desktop/THIRD_PARTY.md`.

## Release checks still required

Before broad distribution, test installation and use on a physically disconnected clean Windows machine without developer tools, and benchmark the actual 8 GB/four-core reference laptop. See [verification results](../desktop/PROJECT_TEST_RESULTS.md) for completed checks and remaining content limitations.
