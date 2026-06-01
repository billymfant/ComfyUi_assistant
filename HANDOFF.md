# HANDOFF — COMFYUI_HELPER

_Last updated: 2026-06-01. Read `CLAUDE.md` for full technical reference; this is the "where we are / what's next" summary._

## What this project is
A helper repo for building & testing local ComfyUI workflows for the user (billymfant). Goal: a 100% local, free replacement for paid image generators. The actual ComfyUI install lives at `F:\ComfyUI\ComfyUI-Easy-Install` (server http://127.0.0.1:8188); this repo holds the workflow JSONs + the tooling that generates them.

## Environment (quick facts)
- GPU: RTX 4080 SUPER (16 GB). ComfyUI v0.22.3. ~687 GB free.
- Embedded Python (use for everything): `F:/ComfyUI/ComfyUI-Easy-Install/python_embeded/python.exe`
- Workflows install to: `F:\ComfyUI\ComfyUI-Easy-Install\ComfyUI\user\default\workflows` (names match `workflows/` here).
- GitHub: https://github.com/billymfant/ComfyUi_assistant (remote `origin`, branch `main`, creds cached on the machine — `git push` just works).

## Status: DONE (all live-tested against the running server)
| Workflow | Task | Model | Notes |
|---|---|---|---|
| 00_MASTER | everything in one file | — | only Flux 2 active by default; Ctrl+B a group to enable |
| 01_FLUX2_AllInOne | t2i / i2i / multi-reference | Flux 2 Klein | ref groups bypassed by default; +4K group |
| 02_IMAGE_to_TEXT | caption / prompt-extract / VQA | Qwen3-VL 8B | ~18s |
| 03_ZIMAGE_t2i | fast t2i + best in-image text | Z-Image Turbo | ~5s; +4K group |
| 04_QWEN_EDIT | instruction editing | Qwen-Image-Edit 2511 | heavy 20B, ~60-170s; +4K group |
| 05_ZIMAGE_controlnet | pose/depth/edge control | Z-Image + Fun ControlNet | +4K group |

- 4K upscaling added everywhere (4x-UltraSharp → cap longest side 3840). Verified true 3840px output.
- Repo restructured into `workflows/ builders/ tests/ scripts/ docs/` (builders use `__file__`-relative paths).
- Separate project `F:\APPS\CREATIVE_OS` (a Node app) now has all 56 global skills in its `.claude/skills`.

## UPDATE 2026-06-01 — Video & motion arsenal added (see `docs/COMFYUI_MASTERPLAN.md`)
Built out per the masterplan (4 phases) + a quality-upgrade pass. All live-tested.
- **06 Wan 2.2 5B** text/image→video. **07 skeleton→character animation** (Fun-Control 5B + DWPose). **08 Wan-Animate full** (loadable; ViTPose+SAM2, deps installed).
- **builders/storyboard_to_video.py** — boards shots → keyframes (Flux 2, consistent character) → i2v → assembled film.
- **Quality upgrade:** Wan-Animate 14B (pose-only, `tests/test_wan_animate.py`, ~60s) and Wan 2.2 14B i2v (`tests/test_wan14b_i2v.py`, ~69s) both > 5B; lightx2v Lightning LoRA (4-step); SeedVR2 upscaler (832×480→1872×1080, `tests/test_seedvr2_upscale.py`).
- Models added (~75 GB): wan2.2_ti2v_5B, wan2.2_fun_control_5B, Wan2_2-Animate-14B fp8, wan2.2_i2v high+low 14B fp8, Wan2_1_VAE_bf16, umt5, lightx2v + relight LoRAs; detection onnx (ViTPose/YOLO) in models/detection; SAM2 node pack cloned.
- Gotchas: 14B i2v uses ModelSamplingSD3 **shift 5** + Wan2.1 VAE + no clip_vision; Wan-Animate DiffusionModelLoaderKJ must omit extra_state_dict, WanAnimateToVideo continue_motion_max_frames≥1; SAM2 segmentor=single_image for bboxes; run detection onnx on CPUExecutionProvider (installed onnxruntime is OpenVINO/CPU, no CUDA provider).
- Work committed on branch **feat/video-motion-arsenal** (not yet merged to main / pushed).

## Decisions / things NOT to redo
- **Cloudflare tunnel was REMOVED at user request** ("not working"). Do not re-add Cloudflare. If remote access comes up again, the agreed-on secure option is **Tailscale** (needs the user's login on PC + phone).
- Flux 2 Klein is the user's hero model; don't suggest swapping the base generator.
- Use the LOCAL sampling path, never the Flux2Pro/Max/Image API (cloud, paid) nodes.

## Critical wiring gotchas (these bit us — keep them)
- **Qwen-Image-Edit (04):** REQUIRES `ModelSamplingAuraFlow`(3.1) + `CFGNorm`(1) on the model AND conditioning routed through `FluxKontextMultiReferenceLatentMethod`(index_timestep_zero). Without the ref-latent method it ignores the input image and outputs garbage. Reference graph: ComfyUI `blueprints/Image Edit (Qwen 2511).json`. Encoder `qwen_2.5_vl_7b_fp8_scaled` (type `qwen_image`), VAE `qwen_image_vae`. CFG 4, steps 20-40.
- **Z-Image (03/05):** CLIPLoader type MUST be `lumina2`; CFG 1, steps 8, dpmpp_sde/beta; `ModelSamplingAuraFlow` shift 3. Reuses existing `qwen_3_4b` encoder + `ae.safetensors` VAE.
- **Z-Image ControlNet (05):** Fun ControlNet lives in `models/model_patches`, loads via `ModelPatchLoader` + `ZImageFunControlnet` (patches the MODEL — NOT standard ControlNet nodes).
- **Downloads:** verify HF file sizes — a truncated 5.0G-vs-6.4G controlnet caused a `shape invalid for input of size` reshape error. Resume with `curl -C -`.

## Operational gotchas
- Reach the local server from tools via proxy bypass: `curl.exe --noproxy "*" http://127.0.0.1:8188/...`
- `object_info.json` is huge and PowerShell `ConvertFrom-Json` chokes on duplicate case-keys → parse with the embedded python. Refresh model lists by GET `/object_info/<NodeName>`.
- Console is Greek cp1253 → set `PYTHONIOENCODING=utf-8` when printing unicode.
- Test a workflow by POSTing API-format JSON to `/prompt`, poll `/history/<id>`, then VIEW the output image (see `tests/`).

## How to continue / regenerate
- Regenerate Flux 2 workflow: `python_embeded/python.exe builders/gen_workflow.py` → writes `workflows/01_...json`.
- Rebuild master: `... builders/merge_master.py` (reads the installed 01-05, writes `workflows/00_...json`).
- Inject a 4K branch into any workflow: `... builders/add_4k_upscale.py in.json out.json PREFIX`.
- After regenerating, copy the file into ComfyUI's `user/default/workflows/` to install.

## Open items / possible next steps (none blocking)
1. **Remote access** — not set up. Recommend Tailscale (private VPN) when the user is at the machine to log in. (Cloudflare is off-limits per their call.)
2. **LoRA support** — add a `Power Lora Loader (rgthree)` to the Flux 2 / Z-Image workflows (user has no LoRAs yet).
3. **Auto image→prompt→image** — wire `02` (Qwen3-VL caption) output into `01`/`03` prompt for one-click "describe a reference then generate".
4. **ControlNet tuning** — try the `Union-2.1-8steps` variant (better suited to Z-Image's 8-step turbo) vs the base 2.1 we installed.
5. **CREATIVE_OS** — offered a structure/quality pass; user hasn't taken it up.

## Memory
Persistent notes for this project live in `C:\Users\User\.claude\projects\F--APPS-COMFYUI-HELPER\memory\` (setup-comfyui-flux2, flux2-workflow-design, local-image-stack). Update them as things change.
