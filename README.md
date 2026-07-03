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

## 09 — LTX 2.3 crystal-clear i2v + glitchcore (NEW)
`09_LTX2_i2v_glitch.json` — turn a still image into a **crystal-clear video with synced audio**, then run it through a **glitchcore time-slice + overlay** post effect (the Instagram-reel look).

- **Pipeline:** LTX 2.3 (22B fp8) image→video, 8-step distilled, **2-pass** = base 768×512 → `LTXVLatentUpsampler` 2× → refine → tiled VAE decode → **TimeSliceGrid** → **GlitchOverlay** → muxed MP4 with audio. Output **1536×1024, ~2s @ 25fps in ~60s** on the 4080S (model warm).
- **Groups:** `BASE` · `REFINE` (2× upscaler — the "crystal clear") · `GLITCH` (green — **Ctrl+B the two nodes to bypass** for a clean clip) · `DECODE+SAVE`.
- **Glitch nodes** (`custom_nodes/glitch_pack`, plain IMAGE-batch ops, no model):
  - **Time-Slice Grid** — N×N grid, each tile pulled from a staggered point in time (mosaic/shatter). `stagger_pattern`: random/radial/linear/wave · `boundary`: clamp/mirror/wrap.
  - **Glitch Overlay** — flickering neon bars + code-snippet fragments as data artifacts. `color_palette`: neon/monochrome/data · `flicker_rate` · `max_drift`.
- **Models added:** `checkpoints/ltx-2.3-22b-dev-fp8.safetensors` (27 GB, has video+audio VAE) · `text_encoders/gemma_3_12B_it_fp4_mixed` (8.8 GB) · `loras/ltx_2.3_22b_distilled_1.1_lora…` (2.5 GB) · `latent_upscale_models/ltx-2.3-spatial-upscaler-x2-1.1` (0.9 GB).
- Headless test/convert helpers: `tests/test_ltx2_glitch.py` (`--twopass`) and `tests/run_ui_workflow.py <wf.json>` (UI→prompt run).

## 10 + 11 — 3D Modeling Assistant: concept → orthographic reference (NEW)
Turn a concept image into **modeling reference for Blender**: a 6-view orthographic turnaround sheet + a rough 3D blockout mesh. Hybrid design — **MV-Adapter** makes crisp concept-art SIDES (front/back/L/R); the **Trellis 2** mesh gives geometrically-correct TOP/BOTTOM + the blockout `.glb` (so you stop relying on the auto-mesh being final art).

- **One-shot driver (recommended):** `python_embeded/python.exe builders/make_ortho_kit.py <image-in-ComfyUI/input> --title Name --prompt "..."`
  → writes `output/OrthoKit_<Name>/` = `sheet.png` (labeled turnaround) + 6 individual view PNGs + `blockout.glb`. ~4 min (MV-Adapter ~210s + Trellis ~35s + render). Input should be the subject on a plain/transparent background.
- **`10_ORTHO_MULTIVIEW.json`** — MV-Adapter i2mv (SDXL): one subject image → 4 orthographic side views. `ViewSelector` = front/right/back/left; **BiRefNet must be `ZhengPeng7/BiRefNet`** (default `briaai/RMBG-2.0` is gated). Needs `sd_xl_base_1.0.safetensors` + `sdxl_vae.safetensors`.
- **`11_TRELLIS_BLOCKOUT.json`** — Trellis 2 GGUF Q4_K_M, fast geometry-only path (no texture, SimplifyMesh→150k faces, `reorient "90 degrees"`) → `.glb`. ~35s. Gotcha: `PreProcessImage` needs the loader's **`image_with_alpha`** output (slot 2); `texture_steps` min is 1 (not 0).
- **Front-end (concept + options):** use **01 Flux 2** to generate/iterate the hero image (text + optional reference), and **02 Qwen3-VL** to analyze it / suggest a modeling approach. Save the chosen image into `ComfyUI/input`, then run the driver or workflows 10/11.
- **Helpers:** `builders/ortho_render.py` (headless numpy orthographic z-buffer rasterizer for mesh top/bottom — open3d/pyrender fail headless on Windows), `builders/assemble_sheet.py` (turnaround layout), `builders/gen_ortho_blockout.py` (regenerates wf 11).

## 12 + 13 — Asset Factory: concept → 4 ortho views → TEXTURED 3D asset (NEW)
The "building aspect" pipeline: ComfyUI builds clean-up-friendly 3D assets (characters, props, set pieces — **~200k faces, holes filled, Xatlas UVs, 2048 baked PBR texture**); you assemble & animate by hand in Blender (~15–30 min polish per asset, not remodeling).

- **`13_ASSET_FACTORY.json` — the master pipeline (recommended).** Three Ctrl+B groups:
  1. **CONCEPT** (active) — Flux 2 t2i + optional image-reference nodes. Iterate the prompt/seed until you love the concept (~seconds per run). Keep the seed control on **`fixed`**.
  2. **MULTIVIEW** (bypassed) — MV-Adapter i2mv: concept → 4 ortho views front/right/back/left (~3.5 min), saved as `ASSET_VIEWS_*` (your Blender reference sheet).
  3. **TRELLIS 3D** (bypassed) — the 4 views feed `Trellis2MeshWithVoxelMultiViewGenerator` (better geometry than single-image) → post-process/unwrap/bake → `output/3D/13_ASSET_FACTORY_*.glb` + 3D preview.
  **"Press play" UX:** when the concept is right, select groups 2+3, Ctrl+B, Run — the cached concept is reused (that's why the seed stays `fixed`), only the 3D stages execute (~6–7 min total).
- **`12_TRELLIS_TEXTURED.json`** — single image → textured .glb (no multiview). Faster (~3–4 min); use it when you already have a perfect concept/turnaround image. Same quality settings.
- **Why these instead of the pack's example workflows:** the GGUF pack examples have stale widget layouts vs the installed nodes (values land in the wrong widgets — the cause of the earlier texturing crashes). 12/13 are generated by `builders/gen_trellis_textured.py` / `builders/gen_asset_factory.py` against the live `/object_info`, so widgets line up. Regenerate after a Trellis pack update.
- Only **`uv_unwrap_method=Xatlas`** works on this machine (`Smart` needs the smart_uv wheel, `Blender` needs bpy). More detail: raise SimplifyMesh/target_face_num (2M ≈ 13 min unwrap) or texture_size 4096; GGUF `Q5_K_M` is a slightly better, slower model tier.
- In Blender: `File > Import > glTF 2.0` — texture is embedded; views make a paintover/modeling reference.

## Remote access
Not set up. ComfyUI binds 127.0.0.1 only (local-only). If remote access is wanted later, **Tailscale** (private encrypted VPN, only your own devices) is the recommended secure option.
