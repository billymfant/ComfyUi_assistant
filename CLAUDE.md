# COMFYUI_HELPER — local image-generation stack

Helper project for building & testing ComfyUI workflows on the user's local machine.
**Goal:** a 100% local, free replacement for paid image generators (Midjourney/DALL·E/Firefly/Photoshop-generative).

## Environment
- ComfyUI install: `F:\ComfyUI\ComfyUI-Easy-Install` (ComfyUI v0.22.3). Server: http://127.0.0.1:8188
- GPU: RTX 4080 SUPER (16 GB). This helper dir: `F:\APPS\COMFYUI_HELPER`
- Embedded Python (use for everything): `F:/ComfyUI/ComfyUI-Easy-Install/python_embeded/python.exe`
- Workflows install to: `F:\ComfyUI\ComfyUI-Easy-Install\ComfyUI\user\default\workflows`

## Talking to the running server (important gotchas)
- Reach localhost only via proxy-bypass: `curl.exe --noproxy "*" http://127.0.0.1:8188/...`
- `object_info.json` (node defs) is huge; PowerShell `ConvertFrom-Json` fails on duplicate case-keys — parse with the embedded python instead. Refresh model lists by GET-ing `/object_info/<NodeName>`.
- Console is Greek cp1253 → set `PYTHONIOENCODING=utf-8` (or `ascii:backslashreplace`) when printing unicode.
- Test a workflow by POSTing API-format JSON to `/prompt`, then poll `/history/<id>` (see `test_*.py`).

## The workflows (installed, all live-tested)
- **00_MASTER** — all modules in one file; only Flux 2 active by default; enable a module's group with Ctrl+B.
- **01 Flux 2 Klein** — t2i / i2i / multi-reference. Reference = ReferenceLatent chain + SamplerCustomAdvanced + Flux2Scheduler + BasicGuider (guidance-distilled, no negative). CLIP type `flux2`.
- **02 Image→Text** — `AILab_QwenVL_GGUF` (Qwen3VL-8B-Instruct-Q8) → `iToolsPreviewText`.
- **03 Z-Image Turbo** — t2i. `UNETLoader`→`ModelSamplingAuraFlow`(shift 3)→KSampler(8 steps, CFG 1, dpmpp_sde/beta). CLIP type **`lumina2`**, encoder `qwen_3_4b`, VAE `ae.safetensors`.
- **04 Qwen-Image-Edit 2511** — instruction editing. REQUIRED wiring: UnetLoaderGGUF→ModelSamplingAuraFlow(3.1)→CFGNorm(1)→KSampler; `TextEncodeQwenImageEditPlus`(clip+vae+image1)→`FluxKontextMultiReferenceLatentMethod`(index_timestep_zero)→KSampler pos/neg; `FluxKontextImageScale` on input; VAEEncode→latent; CFG 4, steps 20-40. Encoder `qwen_2.5_vl_7b_fp8_scaled` (type `qwen_image`), VAE `qwen_image_vae`. Without the ref-latent-method it ignores the reference. Reference graph: ComfyUI `blueprints/Image Edit (Qwen 2511).json`.
- **05 Z-Image + ControlNet** — Fun ControlNet in `models/model_patches`, loaded via `ModelPatchLoader` + `ZImageFunControlnet` (patches MODEL — NOT standard ControlNet nodes). `AIO_Preprocessor` picks canny/depth/pose.
- All generating workflows have a bypassed **4K UPSCALE** group: `ImageUpscaleWithModel`(4x-UltraSharp) → `ImageScaleToMaxDimension`(3840).

## Project structure
```
COMFYUI_HELPER/
├── CLAUDE.md                  # this file (project context)
├── README.md                  # user-facing guide (which workflow when, settings)
├── workflows/                 # the deliverables — load these in ComfyUI
│   ├── 00_MASTER_WORKFLOW.json     # all modules in one (Flux2 on by default)
│   ├── 01_FLUX2_AllInOne_T2I_I2I_Reference.json
│   ├── 02_IMAGE_to_TEXT_QwenVL.json
│   ├── 03_ZIMAGE_t2i.json
│   ├── 04_QWEN_EDIT.json
│   └── 05_ZIMAGE_controlnet.json
├── builders/                  # workflow generators (write into ../workflows/)
│   ├── wf_lib.py                   # WF builder class (UI JSON v0.4: add/connect/group/finalize+validate)
│   ├── gen_workflow.py             # generates workflows/01 (Flux 2 all-in-one)
│   ├── merge_master.py             # reads installed 01-05, writes workflows/00 master
│   └── add_4k_upscale.py           # `add_4k_upscale.py in out PREFIX` injects bypassed 4K branch
├── tests/                     # API smoke tests (POST /prompt, poll /history)
│   ├── test_t2i.py test_ref.py test_2ref.py test_upscale.py
│   └── gen_from3.py upscale_fusion.py
├── scripts/                   # one-off model download shell scripts
│   └── download_models.sh download_big.sh
└── docs/
    └── README_FLUX2_WORKFLOW.md    # original Flux-2-only guide
```
Workflow filenames here match what is installed in ComfyUI's `user/default/workflows/`.
Builders use `__file__`-relative paths, so run them from anywhere:
`python_embeded/python.exe builders/gen_workflow.py` and `.../merge_master.py`.

## Models present (in F:\ComfyUI\...\ComfyUI\models)
diffusion_models: flux-2-klein-4b/9b-fp8, z_image_turbo_bf16 · unet: qwen-image-edit-2511-Q4_K_M.gguf ·
text_encoders: qwen_3_4b, qwen_3_8b_fp8mixed, qwen_2.5_vl_7b_fp8_scaled · vae: flux2-vae, ae, qwen_image_vae ·
model_patches: Z-Image-Turbo-Fun-Controlnet-Union-2.1 · upscale_models: 4x-UltraSharp, RealESRGAN_x4plus ·
LLM: Qwen3-VL-8B-Instruct GGUF + 2B.

## Conventions
- Never ship an untested workflow — validate JSON link integrity (wf_lib reports errors) AND run it via `/prompt` against the live server, viewing the output image, before claiming done.
- Verify HF download sizes (a truncated controlnet caused a reshape error; resume with `curl -C -`).
