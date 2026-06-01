# COMFYUI MASTERPLAN — local motion-project asset engine

_Created 2026-06-01. The strategic plan behind COMFYUI_HELPER. Read `CLAUDE.md` for technical reference and `HANDOFF.md` for session state._

## Vision
Build a 100% local, free ComfyUI arsenal that produces **every asset a motion-graphics / design project needs** — for a working creative director & motion designer. Not single hobbyist images: a production pipeline from concept to finished shots.

The 6 image workflows already delivered (Flux 2, Z-Image, Qwen-Edit, Qwen-VL, Z-Image ControlNet, Master) are the **foundation**. This plan covers the motion / video expansion.

## The asset pipeline (target end-state)
```
   CONCEPT          DESIGN              MOTION                 FINISH
   ───────          ──────              ──────                 ──────
 storyboard  →  character + bg   →   animate the     →   upscale / cleanup
 (the shots)     stills, on-model     character/scene      → assemble shots
```

| Stage | Need | Status |
|---|---|---|
| Character / asset stills | Generate hero character, props, backgrounds | ✅ Have (Flux 2, Z-Image) |
| On-model consistency | Same character across every shot/angle | ⚠️ Gap (IPAdapter / PuLID) |
| Pose control (stills) | Put character in a chosen pose | ✅ Have (Z-Image + Fun ControlNet) |
| **Skeleton → animation** 🎯 | Drive character with a skeleton/pose → clip | ❌ Headline gap |
| Plain image→video | Push a still into motion | ❌ Gap |
| Storyboard → video | Board shots → generate each → assemble | ❌ Pipeline gap |
| Finish | 4K upscale | ✅ Have |

## Headline goals (user's explicit asks)
1. **Skeleton / pose-driven character animation** — generate a character, drive it with a skeleton/pose to animate. Top priority.
2. **Image + video generation** both in the arsenal.
3. **Storyboard → video** workflow (board the shots, then generate the clips). A favorite.

## Key decisions
- **Motion authoring = control-video path** (Wan VACE / Wan-Animate style). Same input socket accepts EITHER a pose auto-extracted from a reference video OR hand-authored skeleton/OpenPose frames — user picks per shot. Designed for "both / flexible."
- **VRAM ceiling = 16 GB** (RTX 4080S). Favor fittable / quantized models: Wan 2.2 5B for plain i2v; Wan VACE via GGUF/fp8 + block-swap for pose animation; MimicMotion as a light fallback. Steer away from un-quantized 14B / Hunyuan as a first step.
- Reuse the existing local stack; never the paid cloud API nodes (per `HANDOFF.md`).
- Cloudflare stays removed; Tailscale is the agreed remote-access option if it ever comes up.

## Build order (each phase = its own spec → plan → implement cycle)
```
Phase 0  ▸  Video foundation        Stand up Wan on the box; prove plain image→video.
            (proves VRAM + nodes)    Wan 2.2 5B i2v. De-risks VRAM, node install,
                                     download integrity. Unlocks everything below.

Phase 1  ▸  Character consistency    IPAdapter / PuLID so one character stays on-model
            (stills)                 across shots. Feeds the whole pipeline.

Phase 2  ▸  Skeleton → animation 🎯  Wan VACE: character image + pose control video → clip.
            (the headline)           Built on the Phase 0 Wan stack.

Phase 3  ▸  Storyboard → video       Orchestration: board shots → generate each → assemble.
            (the workflow he loves)  Ties Phases 0–2 together.
```
**Rationale:** Phase 2 (headline), Phase 0, and Phase 3 all ride the same Wan backbone. Proving plain i2v first (Phase 0) makes the VACE pose module a small, low-risk addition rather than a blind gamble.

## Status
- **✅ Phase 0 DONE (2026-06-01)** — Wan video foundation live-tested on the box.
  - Models downloaded & size-verified: `wan2.2_ti2v_5B_fp16.safetensors` (9.4G), `umt5_xxl_fp8_e4m3fn_scaled.safetensors` (6.3G), `wan2.2_vae.safetensors` (1.4G), all in the standard `diffusion_models/ text_encoders/ vae/` folders.
  - Native pipeline (no wrapper needed for plain video): `UNETLoader → ModelSamplingSD3(shift 8) → KSampler(20 steps, CFG 5, uni_pc/simple)`; `CLIPLoader(umt5, type "wan")`; `Wan22ImageToVideoLatent`; `VAEDecode → CreateVideo(24fps) → SaveVideo`.
  - Live results @ 720p (1280×704), RTX 4080S: **t2v 49 frames ~105 s**, **i2v 49 frames ~96 s** (model warm). Both produced coherent motion (verified by extracting & viewing frames). 5s clips (121 frames) ≈ ~9 min per docs.
  - Deliverable: `workflows/06_WAN_VIDEO_t2v_i2v.json` (official 5B template; LoadImage bypassed = t2v, Ctrl+B to enable = i2v). Installed in ComfyUI. Test harness: `tests/test_wan_i2v.py` (no arg = t2v, image arg = i2v).
  - TODO when convenient: add a bypassed 4K/video-upscale group (seedvr2_videoupscaler is installed) to match the other workflows' convention.
- **✅ Phase 1 DONE (2026-06-01)** — character consistency, on-model, no new downloads.
  - Finding: **Flux 2's native reference (`ReferenceLatent`) IS the consistency engine** for this stack. SDXL-era IPAdapter/PuLID would regress quality — skipped. Already wired in `workflows/01`.
  - Live test: generated a distinctive character (portrait) → reproduced the SAME person full-body, walking in a rainy neon street with umbrella. Identity (face, freckles, copper curls, yellow raincoat) held strongly across pose + scene + framing change. ~22s base, ~18s reference.
  - Tool: `tests/test_character_consistency.py` (generates base, copies to input/, reference-regenerates). Qwen-Edit (WF 04) is the secondary "keep character, change scene" option.
  - Recipe to feed Phase 2: generate/lock one clean character ref → Wan-Animate needs only that single reference image.
- **✅ Phase 2 DONE (2026-06-01) — THE HEADLINE.** Skeleton → character animation, working locally on the 4080S.
  - Path: **Wan 2.2 Fun-Control 5B** (native, low-VRAM). One new model: `wan2.2_fun_control_5B_bf16.safetensors` (9.4G, diffusion_models). Reuses umt5 + wan2.2_vae.
  - Pipeline: `VHS_LoadVideo` (driving clip, frame-capped) → `DWPreprocessor` (skeleton, torchscript detectors) → `Wan22FunControlToVideo`(ref_image = character, control_video = skeleton) → KSampler(20, CFG 5, uni_pc/simple) → VAEDecode → CreateVideo → SaveVideo.
  - Live test: `DancerInRed.mp4` → DWPose skeleton → drove the Phase 1 red-haired character → she performed the dance with identity + outfit + scene preserved. 49 frames @ 480×832, ~couple min.
  - Honors "both/flexible": control video can be an extracted-pose clip OR hand-authored skeleton frames — same `control_video` socket.
  - Deliverable: `workflows/07_WAN_SKELETON_ANIMATION.json` (built from the official 5B Fun-Control template, Canny→DWPose swap; defaults = tested values). Test: `tests/test_skeleton_animation.py` (saves POSE_PREVIEW + SKELETON_ANIM). Driving clips ship in ComfyUI/input/ (DancerInRed, DanceVideo, KungFuVideo, ...).
  - Quality-upgrade option later: Wan-Animate (WanAnimatePreprocess + WanVideoWrapper installed) for stronger face/expression transfer; or Wan VACE 14B-GGUF.
- **✅ Phase 3 DONE (2026-06-01)** — storyboard → assembled film, fully automated.
  - Orchestrator `builders/storyboard_to_video.py`: reads a shot list (JSON), and for each shot generates a Flux 2 keyframe → animates it with Wan 2.2 5B i2v → concatenates all clips (ffmpeg) into `STORYBOARD_FINAL.mp4`. Shot 0 locks the character; later shots reuse it via ReferenceLatent (Phase 1) so the SAME person appears throughout.
  - Shot spec: `{"prompt": str, "frames": int}`; sample at `builders/storyboard_example.json`. Default fixed size 832×480 @ 24fps so clips stream-copy concat cleanly.
  - Live test: 2-shot story (forest dawn → beach golden-hour), same red-haired woman across the cut, assembled to a 4s film. Ties Phases 0+1 together.
  - Extension: add a `"mode": "skeleton"` branch to route a shot through `07` (Fun-Control) for choreographed action shots.

## ✅ MASTERPLAN COMPLETE (2026-06-01)
All four phases delivered & live-tested. The arsenal now spans **stills (Flux 2 / Z-Image) → consistent characters → image/text→video → skeleton-driven character animation → storyboard→assembled film**, plus the original Qwen-Edit / ControlNet / captioning / 4K-upscale workflows. New deliverables: `workflows/06`, `workflows/07`, `builders/storyboard_to_video.py`, and the `tests/test_wan_*`, `tests/test_character_consistency.py`, `tests/test_skeleton_animation.py` harness.
Possible follow-ups: Wan-Animate upgrade (face/expression) · video 4K upscale group (seedvr2 installed) · skeleton-mode storyboard shots · MCP wrapper so the whole arsenal is drivable by conversation.

## QUALITY UPGRADE — Wan-Animate 14B (2026-06-01)
User reported the 5B video looked low-quality. Findings + actions:
- **Quick wins (no DL):** running 5B at full 720p / 81 frames / 30 steps (vs smoke-test 49/20) markedly improves quality. ~4 min/clip. **Rule: do finals at 720p, 80+ frames, ~30 steps.**
- **Wan-Animate 14B (simplified pose-only) WORKS & is the headline upgrade.** Downloaded (Kijai): `Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors` (17G, diffusion_models), `Wan2_1_VAE_bf16.safetensors` (vae), `lightx2v_I2V_14B_480p_..._rank64_bf16.safetensors` (loras, the **Lightning** distill LoRA), `WanAnimate_relight_lora_fp16.safetensors` (loras).
  - Tested graph (`tests/test_wan_animate.py`): `DiffusionModelLoaderKJ`(fp8_e4m3fn/bf16) → `LoraLoaderModelOnly`(lightx2v) ; `VHS_LoadVideo`→`DWPreprocessor`(pose_video) ; `LoadImage`→`ImageScale`(reference_image) → `WanAnimateToVideo`(pose-only; `continue_motion_max_frames`≥1, drop `extra_state_dict`) → `CFGGuider`(cfg 1)+`BasicScheduler`(simple,4)+`KSamplerSelect`(lcm)+`SamplerCustomAdvanced` → VAEDecode → SaveVideo.
  - Result: 49f @ 480×832 in **~60s** (4-step LCM + RAM offload of the 17G fp8 on 16G VRAM). Visibly better anatomy/motion than 5B Fun-Control, identity preserved.
  - **Gaps for FULL Wan-Animate** (face-detail + bg masking): needs a SAM2 node pack, onnxruntime-**gpu**, and ViTPose/YOLO onnx models — NOT installed. Pose-only path avoids all three.
### Full quality-upgrade results (2026-06-01, all four picks)
- **Wan-Animate 14B (pose-only)** ✅ tested — `tests/test_wan_animate.py`, ~60s, best character-animation quality.
- **Wan 2.2 14B i2v (general)** ✅ tested — `tests/test_wan14b_i2v.py`. Dual-expert MoE (`wan2.2_i2v_high_noise_14B_fp8_scaled` + `..._low_noise_...`, 14G each), **WanImageToVideo** (no clip_vision needed), **ModelSamplingSD3 shift 5**, `Wan2_1_VAE_bf16`, two-stage `KSamplerAdvanced` (high steps 0-2, low 2-4) + lightx2v, CFG 1, euler/simple. ~69s @ 832×480, visibly sharper than 5B.
- **Lightning (lightx2v) LoRA** ✅ in use across the 14B paths (enables 4-step).
- **SeedVR2 upscaler** — nodes present (`SeedVR2LoadDiTModel`/`...VAEModel`/`SeedVR2VideoUpscaler`); 3B fp8 + ema_vae auto-download; `tests/test_seedvr2_upscale.py`.
- **Full Wan-Animate (face+SAM2 mask)** — deps installed: ViTPose `vitpose_h_wholebody_model.onnx`+`.bin` & `yolov10m.onnx` in `models/detection`; SAM2 node pack cloned (`ComfyUI-segment-anything-2`); run ONNX on **CPUExecutionProvider** (no onnxruntime-gpu needed); SAM2 `DownloadAndLoadSAM2Model` use **segmentor=single_image** with bboxes. Loadable workflow `workflows/08_WAN_ANIMATE_full.json` (author example, configured, torch-compile bypassed). NOTE: the hand-built API mask branch hit a SAM2 bbox-batch indexing quirk — the author's UI graph (WF 08) encodes the correct routing; pose-only is the validated automated path.

**Quick recipe for finals:** Wan-Animate 14B (pose-only) for character motion; Wan 2.2 14B i2v for plain shots; lightx2v for speed; run video at 720p / 80+ frames / ~30 steps (or 4-step with lightx2v); SeedVR2 to upscale.
- Convention (from `CLAUDE.md`): never ship an untested workflow — validate JSON link integrity AND run it live against the server, viewing the output, before claiming done. Verify HF download sizes.

## Open backlog (from HANDOFF, non-blocking)
- Remote access via Tailscale · LoRA support · auto image→prompt→image · ControlNet Union-2.1-8steps tuning · CREATIVE_OS quality pass.
