# HANDOFF — COMFYUI_HELPER

_Last updated: 2026-07-03. Read `CLAUDE.md` for technical reference, `docs/COMFYUI_MASTERPLAN.md` for the motion-arsenal plan, `3dmodeling assistant plan.md` + `docs/superpowers/specs/2026-07-03-asset-factory-design.md` for the 3D-assistant line of work. This file is the "where we are / what's next" summary._

## NEWEST: Asset Factory (2026-07-03) — direction chosen + shipped
Brainstormed ComfyUI+Blender direction with the user. **Chosen: ComfyUI = asset BUILDER** (characters/props/set pieces at "clean-up-friendly" tier: ~200k faces, holes filled, Xatlas UVs, 2048 baked PBR); the user assembles/animates by hand in Blender. Parked in memory for later: AI finishing pass on Blender renders (A), Blender addon bridge (B), rigged character pipeline (D) — see `parked-ideas-blender.md` memory; user wants B/D revisited after this ships.

Shipped & live-tested (in `workflows/3d modeling helper/` + installed):
- **12_TRELLIS_TEXTURED** — single image → textured .glb. Validated: Kiwano char → 189,570 faces, UVs, 2048² baseColor+metallicRoughness, 425s cold. (`builders/gen_trellis_textured.py`)
- **13_ASSET_FACTORY** — the master: G1 CONCEPT (Flux2 t2i + optional ref, active) → G2 MULTIVIEW (MV-Adapter 4 ortho views, bypassed) → G3 TRELLIS 3D (multiview generator → PostProcess/UnwrapRasterizer → glb, bypassed). "Press play" UX: iterate G1 (seed control **fixed** so the concept stays cached), then Ctrl+B groups 2+3 and Run. (`builders/gen_asset_factory.py`)
- Fixed en route: **frontend adds a control_after_generate widget to ANY INT input named `seed`** (name-based fallback confirmed in frontend 1.43.18 source) → UI workflows must serialize the "fixed" token after seed values. wf 11 had it missing (widgets displayed shifted) — regenerated. `tests/run_ui_workflow.py` now skips control tokens AND resolves links through bypassed nodes (UI passthrough semantics).
- **LOCAL PATCH to ComfyUI-Trellis2-GGUF** (user-approved, re-apply if the pack updates): `nodes.py`, class `Trellis2_GGUFPostProcessAndUnWrapAndRasterizer` — the author forgot `out_faces_int32 = out_faces.to(torch.int32)` when duplicating the rasterize block (single-image path has it at ~line 1218; multiview tail used it undefined at ~line 1956 → NameError). One line added before `print("Sampling attributes...")`. Worth PRing upstream.
- Phase 2 (NOT started): `builders/make_asset.py` one-command driver + `--type` presets — do after the user has driven wf 13 and is happy with defaults.

## What this project is
A helper repo for building & testing local ComfyUI workflows for the user (billymfant) — a **creative director / motion + graphic designer**. Goal: a 100% local, free ComfyUI arsenal that produces **all the assets a motion-graphics project needs** (stills, consistent characters, video, character animation, assembled films), replacing paid generators. The ComfyUI install lives at `F:\ComfyUI\ComfyUI-Easy-Install` (server http://127.0.0.1:8188); this repo holds the workflow JSONs + tooling.

## Environment (quick facts)
- GPU: RTX 4080 SUPER (16 GB). ComfyUI v0.22.3. 68 GB RAM. ~600 GB free after the model pulls below.
- Embedded Python (use for everything): `F:/ComfyUI/ComfyUI-Easy-Install/python_embeded/python.exe`
- Workflows install to: `F:\ComfyUI\ComfyUI-Easy-Install\ComfyUI\user\default\workflows` (names match `workflows/` here).
- GitHub: https://github.com/billymfant/ComfyUi_assistant (remote `origin`, branch `main`, creds cached — `git push` just works).
- **Everything below is committed & pushed to `main`** (latest merge `348bf17`).

## Status: the arsenal (all live-tested, GPU)
| WF / tool | Task | Model | Notes |
|---|---|---|---|
| 00–05 | stills / edit / controlnet / caption | Flux 2, Z-Image, Qwen-Edit, Qwen-VL | original set; +4K upscale groups |
| **06_WAN_VIDEO** | text/image → video | Wan 2.2 5B | t2v ~105s, i2v ~96s @720p |
| **07_WAN_SKELETON_ANIMATION** | skeleton → character animation | Wan Fun-Control 5B + DWPose | drop a character + driving video |
| **08_WAN_ANIMATE_full** | faithful character animation (face+mask) | Wan-Animate 14B + ViTPose + SAM2 | **best quality**, ~64s, all GPU |
| `builders/storyboard_to_video.py` | storyboard → assembled film | Flux2 keyframes → Wan 5B i2v → ffmpeg | consistent character across shots |

Quality-upgrade models also tested: **Wan 2.2 14B i2v** (dual-expert, ~69s, sharper than 5B; `tests/test_wan14b_i2v.py`), **Wan-Animate 14B pose-only** (~60s; `tests/test_wan_animate.py`), **lightx2v Lightning LoRA** (4-step), **SeedVR2** upscaler (832×480→1872×1080; `tests/test_seedvr2_upscale.py`).

**Best-quality recipe:** character motion → `08` (Wan-Animate full); plain shots → Wan 2.2 14B i2v; 4-step via lightx2v; SeedVR2 to upscale finals; run video at 720p / 80+ frames / ~30 steps when not using lightx2v.

## Models added this round (~75 GB, all on disk)
diffusion_models: `wan2.2_ti2v_5B_fp16`, `wan2.2_fun_control_5B_bf16`, `Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2`, `wan2.2_i2v_high_noise_14B_fp8_scaled`, `wan2.2_i2v_low_noise_14B_fp8_scaled` · vae: `wan2.2_vae`, `Wan2_1_VAE_bf16` · text_encoders: `umt5_xxl_fp8_e4m3fn_scaled` · loras: `lightx2v_I2V_14B_480p_..._rank64_bf16`, `WanAnimate_relight_lora_fp16` · models/detection: `vitpose_h_wholebody_model.onnx`+`.bin`, `yolov10m.onnx` · SAM2 auto-downloads (sam2.1_hiera_base_plus).
Custom node added: `ComfyUI-segment-anything-2` (cloned). Everything else (WanVideoWrapper, WanAnimatePreprocess, GGUF, VHS, kjnodes, controlnet_aux, rmbg, sam3, TiledDiffusion, seedvr2, Trellis2) was already installed.

## Environment changes made (important)
- **onnxruntime → onnxruntime-gpu only (1.26.0).** Removed conflicting `onnxruntime` + `onnxruntime-openvino` (OpenVINO was hijacking the import and hiding CUDA). ViTPose/YOLO now run on the 4080 (cuDNN9 supplied by torch/lib, which ComfyUI loads). If onnx ever falls back to CPU, re-check that only `onnxruntime-gpu` is installed.
- ComfyUI was stopped/relaunched once to swap locked DLLs; it's back up and healthy.

## Critical wiring gotchas (keep these)
- **Wan-Animate full (08):** `DiffusionModelLoaderKJ` — omit `extra_state_dict`; `WanAnimateToVideo` `continue_motion_max_frames` ≥ 1; ONNX `onnx_device=CUDAExecutionProvider`; SAM2 needs a **2.1 model + `segmentor=video`** to accept bboxes (2.0/single_image → bbox IndexError). 4-step LCM: CFGGuider cfg 1 + BasicScheduler simple/4 + KSamplerSelect lcm.
- **Wan 2.2 14B i2v:** `WanImageToVideo` (NO clip_vision), `ModelSamplingSD3` **shift 5**, `Wan2_1_VAE_bf16`, dual-expert two-stage `KSamplerAdvanced` (high steps 0-2 leftover-noise on, low 2-4) + lightx2v, CFG 1, euler/simple.
- **Wan 2.2 5B (06/07):** `ModelSamplingSD3` shift 8, CLIPLoader type `wan`, `wan2.2_vae`. 5B i2v = `Wan22ImageToVideoLatent`; Fun-Control = `Wan22FunControlToVideo` (ref_image + control_video from DWPose).
- **pip on this embedded python:** set `TEMP`/`TMP` to the **F:** drive (cross-drive move = WinError 17); ComfyUI must be **stopped** to replace locked DLLs (kill PID on :8188, relaunch `python_embeded\python.exe -s ComfyUI/main.py --windows-standalone-build --use-flash-attention`).
- (Earlier, unchanged) Qwen-Edit ref-latent-method; Z-Image CLIP type `lumina2`; verify HF download sizes (`curl -C -`); reach server via `curl.exe --noproxy "*"`; parse object_info with embedded python; `PYTHONIOENCODING=utf-8`.

## Decisions / do NOT redo
- Cloudflare stays removed (Tailscale is the agreed remote-access option if it ever comes up).
- Flux 2 Klein is the hero stills model; never the paid cloud API nodes.
- Character consistency = Flux 2 native `ReferenceLatent` (workflows 01); do NOT install SDXL-era IPAdapter/PuLID (quality regression).

## Open / possible next steps (none blocking)
1. **Loadable WF for 06/07/14B-i2v** — only `08` and the templates are loadable; the 14B-i2v + pose-only paths exist as tested scripts. Could ship UI workflows.
2. **storyboard_to_video.py upgrades** — add a `"mode":"skeleton"`/`"animate"` branch to route shots through `07`/`08`; option to use Wan 14B i2v instead of 5B; auto-SeedVR2 finishing pass.
3. **Master workflow refresh** — `00_MASTER` predates the video work; could fold in 06/07/08.
4. **Test artifacts** left in ComfyUI input/output (CHAR_*, WAN_*, SEEDVR2_*, char_*, seedvr_src.mp4) — harmless, can be cleared.
5. Older backlog: LoRA loader in stills workflows; auto image→prompt→image (WF 02 → 01/03); ControlNet Union-2.1-8steps; CREATIVE_OS pass.

## Memory
Persistent notes in `C:\Users\User\.claude\projects\F--APPS-COMFYUI-HELPER\memory\`: user-profile, project-motion-arsenal, wan-video-foundation, character-consistency, skeleton-animation, storyboard-to-video, wan-animate-14b, + the original setup/flux2/local-stack notes. Update them as things change.
