# 3D Modeling Assistant — Handoff (DELIVERED)

**For:** creative director → 3D motion designer (Blender). **Goal:** turn a concept image
into modeling reference — a 6-view orthographic turnaround sheet + a rough 3D blockout mesh.

**Status: built & live-tested end-to-end on the RTX 4080S (2026-07-02).** Proof kit generated
for a test character in `output/OrthoKit_Kiwano/` (sheet + 6 views + blockout.glb).

---

---
## SESSION 2 HANDOFF — Trellis troubleshooting (2026-07-02, latest)

**Where we are:** the ortho-kit pipeline (below) is built & working. This session was spent
getting the user's own Trellis "high-quality textured" workflows to run. Context ran to ~94%.

**Key findings (all verified live):**
1. **TWO Trellis packs installed** — `ComfyUI-Trellis2` (non-GGUF, wants BF16 models NOT on disk)
   and `ComfyUI-Trellis2-GGUF` (works, Q4/Q5 on disk). Mixing them = `AttributeError: 'Trellis2
   ImageTo3DPipeline' object has no attribute 'isPixal3D'`. **Rule: use all-`_GGUF` nodes.**
   The user's downloaded `High_Quality_GGUF.json`/`Trellis2Multiviews_GGUF.json` (in
   `C:\Users\User\Downloads\workflows`) are non-GGUF-pack workflows → they crash.
2. **Models COMPLETE & verified** — Q4_K_M + Q5_K_M full sets (refiner/shape512+1024/tex512+1024)
   + fp16 support (decoders, encoders, dinov3) all pass integrity. Nothing missing. NOT downloaded:
   Q6_K/Q8_0/BF16 (optional, offered).
3. **UV unwrap / texturing:** `Trellis2MeshTexturing_GGUF` → **use uv_unwrap_method = `Xatlas`**
   (verified end-to-end: 104s, 189k faces, UVs+baked texture, 9.9MB glb via my direct-API test
   `scratchpad/test_texture_xatlas.py`). `Smart` needs `smart_uv` wheel (github Aero-Ex/Smart-UV-
   Projection, external-wheel install BLOCKED in auto mode — user must run it or ComfyUI-Manager
   "Try Fix"). `Blender` needs `bpy` (missing). `backend` on LoadModel = **flash_attn** (installed);
   fallback `sdpa`.
4. **GGUF-pack example workflows have STALE widget layouts** vs installed nodes → widget
   misalignment on load (symptoms in log: "Value not in list: uv_unwrap_method: 60",
   "dual_contouring_resolution: False"). This is why the user's textured runs kept failing.

**Recommended settings for the user's textured workflow:** target_face_num **200,000**,
uv_unwrap_method **Xatlas**, texture_size 1024–2048. (2M faces + any method = ~13min; 200k = ~2min.)

**OPEN TASK — ✅ DONE 2026-07-03:** shipped as `12_TRELLIS_TEXTURED.json` (+ the bigger
`13_ASSET_FACTORY.json` master pipeline; see `docs/superpowers/specs/2026-07-03-asset-factory-design.md`
and HANDOFF.md). Original spec kept below for reference:
build a CLEAN textured Trellis workflow via `wf_lib` (like
`builders/gen_ortho_blockout.py` did for wf 11) against the CURRENT installed node widget order,
with uv_unwrap_method=Xatlas preset — install to `workflows/3d modeling helper/`. This removes the
stale-widget misalignment for good. Node chain: LoadImageWithTransparency → PreProcessImage(image
slot **2**) + LoadModel(GGUF Q4_K_M, flash_attn) → MeshWithVoxelAdvancedGenerator → Remesh →
SimplifyMesh(200k) → FillHolesWithMeshlib → MeshWithVoxelToTrimesh(90 deg) → MeshTexturing
(pipeline+prep image+trimesh, uv=Xatlas) → ExportMesh glb. Get exact widget order from
`/object_info/<node>` first (widgets drift!). Validate with `tests/run_ui_workflow.py`.

**Env changes made this session:** installed `dash`,`nbformat` (probing open3d, harmless),
`xatlas` (turned out cumesh has its own bundled — harmless), MV-Adapter node pack, SDXL base+vae.
**Deliverables now live in `workflows/3d modeling helper/`** (10_ORTHO_MULTIVIEW, 11_TRELLIS_
BLOCKOUT + 4 GGUF-native Trellis examples copied from the pack). Memory: `ortho-modeling-kit.md`.

---

## The core idea (why it beats the built-in 3D)
The built-in Trellis auto-mesh felt underwhelming because it was being asked to be *final art*.
Here it isn't: **MV-Adapter** makes crisp concept-art SIDES (front/back/left/right), and the
**Trellis mesh** only supplies the geometrically-correct TOP/BOTTOM that 2D diffusion can't do,
plus the blockout `.glb` you actually model over in Blender. Hybrid = clean sheet + real geometry.

## How to use it
1. **Concept** — generate/iterate your hero image in **workflow 01 (Flux 2)** (text + optional
   image ref). Optionally analyze it / get modeling options with **workflow 02 (Qwen3-VL)**.
2. Save the chosen image (subject on plain/transparent bg) into `ComfyUI/input`.
3. **One command:**
   `python_embeded/python.exe builders/make_ortho_kit.py <image> --title Name --prompt "..."`
   → `output/OrthoKit_<Name>/`: `sheet.png` + front/back/left/right/top/bottom PNGs + `blockout.glb`.
4. In Blender: import `blockout.glb` as a proportions guide; pin `sheet.png` (or the individual
   views) as reference. ~4 min/run (MV-Adapter ~210s, Trellis ~35s, render/assemble the rest).

Interactive alternative: load **`10_ORTHO_MULTIVIEW.json`** (sides) and **`11_TRELLIS_BLOCKOUT.json`**
(mesh) in ComfyUI and tune per subject.

## What was built (files)
- `builders/make_ortho_kit.py` — end-to-end driver (the recommended entry point).
- `builders/ortho_render.py` — headless numpy orthographic z-buffer rasterizer (mesh → 6 clay
  views). Needed because open3d/pyrender/VTK all fail headless on this Windows box.
- `builders/assemble_sheet.py` — labeled turnaround-cross layout.
- `builders/gen_ortho_blockout.py` — regenerates workflow 11.
- `workflows/10_ORTHO_MULTIVIEW.json`, `workflows/11_TRELLIS_BLOCKOUT.json` — installed to ComfyUI, both live-validated.

## Install / models added
- Node pack **ComfyUI-MVAdapter** (cloned). Do NOT `pip install -r requirements.txt` — its pins
  would downgrade diffusers/transformers and break Flux/Qwen/Wan; it runs fine on the newer versions.
- `checkpoints/sd_xl_base_1.0.safetensors` (6.5 G) + `vae/sdxl_vae.safetensors` (fp16-fix, 320 M).
- MV-Adapter `mvadapter_i2mv_sdxl.safetensors` + `ZhengPeng7/BiRefNet` auto-download on first run.
- Trellis 2 already installed (uses on-disk **GGUF Q4_K_M**).
- Minor: `dash`, `nbformat` pip-installed while probing open3d rendering (harmless, unused now).

## Key gotchas (baked into the code)
- MV-Adapter BiRefNet ckpt = `ZhengPeng7/BiRefNet` (default `briaai/RMBG-2.0` is GATED → 401).
- 4 ortho sides = ViewSelector [front,‑,right,back,left,‑] → `azimuth_degrees` → sampler num_views=4.
- Trellis PreProcess needs loader output **slot 2 (`image_with_alpha`)**; `texture_steps` min = 1;
  raw ToTrimesh = 3.8 M faces → add `SimplifyMesh` (→147 k) for a Blender-friendly blockout.
- Ortho renderer decimates + drops floaters + culls sliver tris; top/bottom are the cleanest mesh views.

## Possible next steps (not done)
- **ControlNet cleanup pass** (Stage 4c in the original plan): re-render each view through Flux2/SDXL
  + lineart/depth ControlNet so top/bottom match the colored sides' art style. (Sheet is already
  usable without it.)
- White-key the MV-Adapter gray studio bg for a pure-white sheet.
- Optional single combined "workflow 10 master" with the Flux2/Qwen front-end inline (kept modular
  for now, matching the Ctrl+B module convention).
- Trellis `remove_floaters`/`remove_inner_faces` in-graph to further clean the blockout mesh.

Memory: `ortho-modeling-kit.md`. README section: "10 + 11 — 3D Modeling Assistant".
