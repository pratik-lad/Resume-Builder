# Bundled components

The installer supplies application source, pinned build requirements and
third-party notices. Qt DLLs remain dynamically linked and replaceable.

| Component | Upstream / terms |
| --- | --- |
| Qwen3-4B-Instruct-2507 | Qwen Apache-2.0 model; pinned GGUF from unsloth/Qwen3-4B-Instruct-2507-GGUF |
| llama.cpp | MIT; native Windows CPU release b11316 |
| BGE small en v1.5 | BAAI model declaring MIT; pinned Xenova INT8 ONNX conversion |
| PySide6 / Qt | LGPLv3 / GPLv3 / commercial options; this build uses the open source distribution |
| Python | Python Software Foundation licence |
| PyMuPDF / MuPDF | AGPL-3.0; corresponding upstream sources are required when redistributing |
| python-docx, NumPy, ONNX Runtime, tokenizers, other Python dependencies | See packaged individual licence and metadata notices |
| NSIS | zlib/libpng-style licence; some bundled plugins have separate notices |
| NSISBI 3.12.3 | NSIS derivative for large offline installers; see packaged NSISBI.txt and pinned installer-toolchain.json |

Source locations:

- https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
- https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF
- https://huggingface.co/BAAI/bge-small-en-v1.5
- https://huggingface.co/Xenova/bge-small-en-v1.5
- https://github.com/ggml-org/llama.cpp/tree/b11316
- https://code.qt.io/cgit/pyside/pyside-setup.git/
- https://code.qt.io/cgit/qt/
- https://github.com/pymupdf/PyMuPDF/tree/1.25.1
- https://mupdf.com/releases
- https://github.com/kichik/nsis
- https://sourceforge.net/projects/nsisbi/

Do not remove packaged copyright, licence or attribution files when sharing.
Before public distribution, supply the corresponding source for the shipped
copyleft components, including required dependency source and build materials.
The included application Python source alone is not the complete Qt/MuPDF
corresponding source. This build is for local preview and release qualification.


Project Edition 1.6.0 includes a CUDA runtime built from llama.cpp b11316, commit `2232bc8b5f8cd91493a2c251b077c4d45cf2e832`, under its MIT licence. Build source and SHA-256 are pinned in `desktop/build_cuda.py`; native file hashes and toolchain provenance are collected in the asset manifest. CUDA 13.3.1 redistributable libraries and their NVIDIA notices are included; these are not required for CPU fallback. Only the selected GGUF is packaged. Comparison model pins/licence links are in `desktop/model_candidates.json`; Phi-4 Mini and Qwen3.5 comparison weights are not bundled unless selected.
