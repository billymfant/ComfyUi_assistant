# Your Local Image Stack — replaces Midjourney / DALL·E / Firefly / Photoshop generative

100% local, free, on your RTX 4080 SUPER. All five workflows are in ComfyUI → **Workflows** sidebar (numbered 01–05). Every one was live-tested before delivery.

## The 5 workflows

| # | Workflow | Does | Model | Speed |
|---|---|---|---|---|
| 01 | `01_FLUX2_AllInOne` | Text→Image, Image→Image, Reference→Image (1–3 refs) | Flux 2 Klein | ~22s |
| 02 | `02_IMAGE_to_TEXT_QwenVL` | Image→Text (caption / prompt-extract / VQA) | Qwen3-VL 8B | ~18s |
| 03 | `03_ZIMAGE_t2i` | Fast Text→Image + best in-image text | Z-Image Turbo | ~5s |
| 04 | `04_QWEN_EDIT` | Instruction image **editing** | Qwen-Image-Edit 2511 | ~60–170s |
| 05 | `05_ZIMAGE_controlnet` | Pose / depth / edge structure control | Z-Image + Fun ControlNet | ~40s |

## Which to use when
- **Quick idea / poster / text in image** → 03 Z-Image (fastest)
- **Best photographic quality / combine reference images** → 01 Flux 2
- **"Change X / remove Y / edit the text"** on an existing image → 04 Qwen-Edit
- **Match an exact pose or composition** → 05 ControlNet
- **Describe an image or pull a prompt from a reference** → 02 Qwen3-VL

A great combo: run **02** on an image you like → copy the caption → paste into **01** or **03** to recreate/remix it.

## Models added this session
- `unet/qwen-image-edit-2511-Q4_K_M.gguf` (13 GB)
- `text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors` (8.8 GB)
- `diffusion_models/z_image_turbo_bf16.safetensors` (12 GB)
- `vae/qwen_image_vae.safetensors`, `vae/ae.safetensors`
- `model_patches/Z-Image-Turbo-Fun-Controlnet-Union-2.1.safetensors` (6.3 GB)
- (Z-Image reuses your existing `text_encoders/qwen_3_4b.safetensors`)

## Key per-model notes
- **Z-Image (03/05):** CLIP type must be `lumina2`; keep CFG=1, steps 8; `ModelSamplingAuraFlow` shift 3. Best text rendering — put the exact words in quotes.
- **Qwen-Edit (04):** uses the official 2511 wiring (`ModelSamplingAuraFlow` 3.1 + `CFGNorm` + `FluxKontextMultiReferenceLatentMethod`). Don't delete those nodes. CFG 4, steps 20 (40 for max). Heavy 20B model — offloads to RAM, hence slower.
- **ControlNet (05):** the Fun ControlNet lives in `models/model_patches` and loads via `ModelPatchLoader` + `ZImageFunControlnet` (NOT the normal ControlNet nodes). Switch control type in the `AIO_Preprocessor` dropdown.
- **Flux 2 (01):** reference groups are bypassed by default = text-to-image; `Ctrl+B` to enable a reference. Optional upscale group (4x-UltraSharp).

## Upscaling
Workflow 01 has a built-in 2× upscale group. For any image, you also have `4x-UltraSharp` and `RealESRGAN_x4plus` in `models/upscale_models`.

---

## 00 — MASTER WORKFLOW (all-in-one)
`00_MASTER_WORKFLOW.json` contains every module in one file as big coloured groups:
- **A** Flux 2 (ON by default) · **B** Z-Image · **C** Qwen-Edit · **D** ControlNet · **E** Image→Text · **F** 4K Upscaler (standalone)

**Use:** only Module A runs by default. To use another, click its group title to select it → **Ctrl+B** to enable (Ctrl+B again to disable). Turn a module OFF when done so two heavy models don't load at once on 16 GB. Each module keeps its own prompt + Save node.

## 4K upscaling (added everywhere)
- Every generating workflow (01/03/04/05) now has a **"4K UPSCALE" green group** (bypassed by default — Ctrl+B to enable). It runs 4x-UltraSharp then caps the longest side at 3840 = up to 4K.
- The master also has **Module F**: a standalone upscaler — load any image, enable, run → 4K.

## Remote access (status)
ComfyUI currently binds 127.0.0.1 only and no tunnel tool is installed, so it is NOT reachable remotely yet. Secure options: **Tailscale** (private VPN, most secure), **Cloudflare quick tunnel** (instant public URL, unauthenticated), or **ngrok** (needs a free account token, supports a password). A tunnel running on this PC reaches ComfyUI at localhost — ComfyUI does NOT need restarting.
