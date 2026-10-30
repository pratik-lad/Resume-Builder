# Phase 2 — approved direction, implementation deferred

Start this phase after the user approves Phase 1 resume quality. This document
records decisions; it does not claim that a Mac server or tunnel has been built.

## Target

- Apple Silicon Mac with 8 GB unified memory; other computers use a browser.
- Reuse the improved Project Edition generator, not the legacy API generation.
- Upload, JD, Generate, progress, Cancel, editing, DOCX and HTML downloads.
- One active generation and one waiting job; the selected GGUF from desktop/assets.json, bounded context.
- Automatic service/tunnel startup after login, crash recovery and persistent data.
- The Mac stays powered on, awake and connected while serving requests.

## GPU and memory

Use a native Metal llama.cpp runtime on the Mac; partial model-layer offloading
and CPU fallback are required. Requested desktop backends are CUDA for NVIDIA
and Vulkan for supported AMD hardware. Bundle separate pinned/checksummed
runtimes; do not confuse layer offloading with isolated GPU partitions.
Mac CPU/GPU share memory. Measure native allocations and process ownership without
double-counting shared buffers or claiming a hard VRAM cap from layer flags.
Keep the removed 2.3 GB startup gate removed. Preserve owned-process cleanup,
running memory monitoring and idle unload. Verify on the actual 8 GB Mac.

Reference: [llama.cpp build documentation](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md).

## Free internet access

Default: ngrok Free's assigned HTTPS address and free account, without a paid
subscription, custom purchased domain or paid APIs. Quotas and the browser
interstitial apply; hitting a free-tier quota can interrupt access. Recheck the
provider's current limits when implementing. Use asynchronous jobs and restrained
polling. Local generation remains usable without the tunnel.

Require application login and per-user job/download access. Expose only the web
application; the loopback model endpoint and administrative paths remain private.
Do not store tunnel tokens or login secrets in Git. Resume content crosses the
tunnel provider even though inference remains on the Mac.

Reference: [ngrok Free limits](https://ngrok.com/docs/pricing-limits/free-plan-limits).

## Release gates

On the actual Mac: Metal/CPU fallback, memory, two browser sessions, queueing,
cancel isolation, edited downloads, access isolation, tunnel reconnects, login
startup, crash recovery, reboot and coexistence with other applications.
