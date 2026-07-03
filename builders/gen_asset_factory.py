"""Generate workflows/3d modeling helper/13_ASSET_FACTORY.json — the master pipeline:

  G1 CONCEPT   (Flux 2 Klein t2i + optional image reference)   -> concept image
  G2 MULTIVIEW (MV-Adapter i2mv SDXL)                          -> 4 ortho views (F/R/B/L)
  G3 TRELLIS   (multiview generator + unwrap/rasterize)        -> textured .glb (Xatlas, 200k)

"Press play" UX: G2+G3 ship BYPASSED. Iterate the concept in G1 (edit prompt / seed, Run —
seconds per try). When you love it, select the G2+G3 groups, Ctrl+B, Run: ComfyUI's caching
reuses the unchanged G1 result (seed control is `fixed` for exactly this reason) and only
the 3D stages execute.

Widget layouts match the CURRENTLY installed nodes (queried via /object_info 2026-07-03);
seed widgets carry the "fixed" control_after_generate token the frontend serializes.
Run:
    python_embeded/python.exe builders/gen_asset_factory.py
"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wf_lib import WF

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "workflows", "3d modeling helper", "13_ASSET_FACTORY.json")
INSTALL = "F:/ComfyUI/ComfyUI-Easy-Install/ComfyUI/user/default/workflows/3d modeling helper"

PV3D_TYPE = "STRING,FILE_3D_GLB,FILE_3D_GLTF,FILE_3D_FBX,FILE_3D_OBJ,FILE_3D_STL,FILE_3D_USDZ,FILE_3D"
BYPASS = 4

CONCEPT_PROMPT = ("a stylized fantasy treasure chest with brass fittings, clean 3d asset "
                  "concept art, single object centered, neutral gray studio background, "
                  "soft even lighting, full object in frame")
MV_PROMPT = ("clean 3d asset render, neutral studio background, consistent subject, "
             "orthographic model sheet")
MV_NEG = "watermark, ugly, deformed, noisy, blurry, low contrast"

w = WF()

# ---------------- G1 CONCEPT (Flux 2 Klein) — ACTIVE ----------------
w.add(1, "UNETLoader", [40, 80], [300, 82], ["flux-2-klein-4b-fp8.safetensors", "default"],
      [], [("MODEL", "MODEL")], title="Diffusion Model (4B=fast / 9B=quality)")
w.add(2, "CLIPLoader", [40, 220], [300, 106], ["qwen_3_4b.safetensors", "flux2", "default"],
      [], [("CLIP", "CLIP")], title="Text Encoder (Qwen3)")
w.add(3, "VAELoader", [40, 380], [300, 58], ["flux2-vae.safetensors"],
      [], [("VAE", "VAE")], title="VAE")
w.add(4, "CLIPTextEncode", [380, 80], [380, 220], [CONCEPT_PROMPT],
      [("clip", "CLIP")], [("CONDITIONING", "CONDITIONING")], title="ASSET PROMPT", color="#232")
w.add(5, "FluxGuidance", [380, 350], [380, 58], [4],
      [("conditioning", "CONDITIONING")], [("CONDITIONING", "CONDITIONING")], title="Guidance (3-5)")

# optional image reference (bypassed) — same pattern as workflow 01
w.add(30, "LoadImage", [380, 480], [300, 314], ["example.png", "image"],
      [], [("IMAGE", "IMAGE"), ("MASK", "MASK")], mode=BYPASS, title="Reference image", color="#322")
w.add(31, "ImageScaleToTotalPixels", [380, 850], [280, 106], ["lanczos", 1.0, 16],
      [("image", "IMAGE")], [("IMAGE", "IMAGE")], mode=BYPASS)
w.add(32, "VAEEncode", [380, 1000], [210, 46], [],
      [("pixels", "IMAGE"), ("vae", "VAE")], [("LATENT", "LATENT")], mode=BYPASS)
w.add(33, "ReferenceLatent", [380, 1090], [210, 66], [],
      [("conditioning", "CONDITIONING"), ("latent", "LATENT")], [("CONDITIONING", "CONDITIONING")],
      mode=BYPASS)

w.add(6, "EmptyFlux2LatentImage", [800, 80], [280, 106], [1024, 1024, 1],
      [], [("LATENT", "LATENT")], title="Canvas size")
w.add(7, "RandomNoise", [800, 230], [280, 82], [12345, "fixed"],
      [], [("NOISE", "NOISE")], title="Seed (fixed = 3D stages reuse the cached concept)")
w.add(8, "KSamplerSelect", [800, 360], [280, 58], ["euler"],
      [], [("SAMPLER", "SAMPLER")])
w.add(9, "Flux2Scheduler", [800, 460], [280, 82], [20, 1024, 1024],
      [], [("SIGMAS", "SIGMAS")], title="Scheduler (steps)")
w.add(10, "BasicGuider", [800, 590], [280, 46], [],
      [("model", "MODEL"), ("conditioning", "CONDITIONING")], [("GUIDER", "GUIDER")])
w.add(11, "SamplerCustomAdvanced", [1120, 80], [300, 150], [],
      [("noise", "NOISE"), ("guider", "GUIDER"), ("sampler", "SAMPLER"),
       ("sigmas", "SIGMAS"), ("latent_image", "LATENT")],
      [("output", "LATENT"), ("denoised_output", "LATENT")], title="Sampler")
w.add(12, "VAEDecode", [1120, 290], [210, 46], [],
      [("samples", "LATENT"), ("vae", "VAE")], [("IMAGE", "IMAGE")])
w.add(13, "SaveImage", [1120, 390], [400, 440], ["ASSET_CONCEPT"],
      [("images", "IMAGE")], [], title="CONCEPT — iterate until you love it")

w.connect(1, 0, 10, 0, "MODEL")
w.connect(2, 0, 4, 0, "CLIP")
w.connect(4, 0, 5, 0, "CONDITIONING")
w.connect(5, 0, 33, 0, "CONDITIONING")
w.connect(30, 0, 31, 0, "IMAGE")
w.connect(31, 0, 32, 0, "IMAGE")
w.connect(3, 0, 32, 1, "VAE")
w.connect(32, 0, 33, 1, "LATENT")
w.connect(33, 0, 10, 1, "CONDITIONING")
w.connect(7, 0, 11, 0, "NOISE")
w.connect(10, 0, 11, 1, "GUIDER")
w.connect(8, 0, 11, 2, "SAMPLER")
w.connect(9, 0, 11, 3, "SIGMAS")
w.connect(6, 0, 11, 4, "LATENT")
w.connect(11, 0, 12, 0, "LATENT")
w.connect(3, 0, 12, 1, "VAE")
w.connect(12, 0, 13, 0, "IMAGE")

# ---------------- G2 MULTIVIEW (MV-Adapter) — BYPASSED ----------------
w.add(20, "BiRefNet", [1650, 80], [300, 58], ["ZhengPeng7/BiRefNet"],
      [], [("FUNCTION", "FUNCTION")], mode=BYPASS, title="BG removal (NOT briaai — gated)")
w.add(21, "ImagePreprocessor", [1650, 190], [300, 106], [768, 768],
      [("remove_bg_fn", "FUNCTION"), ("image", "IMAGE")], [("IMAGE", "IMAGE")], mode=BYPASS)
w.add(22, "LdmPipelineLoader", [1650, 350], [300, 106],
      ["sd_xl_base_1.0.safetensors", "MVAdapterI2MVSDXLPipeline"],
      [], [("PIPELINE", "PIPELINE"), ("AUTOENCODER", "AUTOENCODER"), ("SCHEDULER", "SCHEDULER")],
      mode=BYPASS)
w.add(23, "DiffusersMVSchedulerLoader", [1650, 510], [300, 130], ["DDPM", True, "interpolated", 8.0],
      [("pipeline", "PIPELINE")], [("SCHEDULER", "SCHEDULER")], mode=BYPASS)
w.add(24, "LdmVaeLoader", [1650, 690], [300, 82], ["sdxl_vae.safetensors", True],
      [], [("AUTOENCODER", "AUTOENCODER")], mode=BYPASS, title="SDXL VAE (fp16 fix)")
w.add(25, "DiffusersMVModelMakeup", [2000, 80], [320, 180],
      [True, "huanngzh/mv-adapter", "mvadapter_i2mv_sdxl.safetensors", 4, True, False],
      [("pipeline", "PIPELINE"), ("scheduler", "SCHEDULER"), ("autoencoder", "AUTOENCODER")],
      [("PIPELINE", "PIPELINE")], mode=BYPASS)
w.add(26, "ViewSelector", [2000, 320], [320, 190], [True, False, True, True, True, False],
      [], [("LIST", "LIST")], mode=BYPASS, title="Views: front/right/back/left")
mv = w.add(27, "DiffusersMVSampler", [2370, 80], [380, 380],
      [4, MV_PROMPT, MV_NEG, 768, 768, 40, 3.0, 0, "fixed", 1.0],
      [("pipeline", "PIPELINE"), ("reference_image", "IMAGE"),
       ("controlnet_image", "IMAGE"), ("azimuth_degrees", "LIST")],
      [("IMAGE", "IMAGE")], mode=BYPASS, title="MV-Adapter sampler (~3.5 min)")
mv["inputs"][1]["shape"] = 7
mv["inputs"][2]["shape"] = 7
mv["inputs"][3]["shape"] = 7
w.add(28, "SaveImage", [2370, 520], [400, 440], ["ASSET_VIEWS"],
      [("images", "IMAGE")], [], mode=BYPASS, title="4 ortho views (F/R/B/L)")

w.connect(20, 0, 21, 0, "FUNCTION")
w.connect(12, 0, 21, 1, "IMAGE")          # concept -> preprocessor
w.connect(22, 0, 23, 0, "PIPELINE")
w.connect(22, 0, 25, 0, "PIPELINE")
w.connect(23, 0, 25, 1, "SCHEDULER")
w.connect(24, 0, 25, 2, "AUTOENCODER")
w.connect(25, 0, 27, 0, "PIPELINE")
w.connect(21, 0, 27, 1, "IMAGE")
w.connect(26, 0, 27, 3, "LIST")
w.connect(27, 0, 28, 0, "IMAGE")

# ---------------- G3 TRELLIS 3D (multiview -> textured glb) — BYPASSED ----------------
# split the 4-view batch: ViewSelector order = front(0), right(1), back(2), left(3)
for i, (nid, label) in enumerate([(40, "front"), (41, "right"), (42, "back"), (43, "left")]):
    w.add(nid, "ImageFromBatch", [2850, 80 + i * 170], [260, 106], [i, 1],
          [("image", "IMAGE")], [("IMAGE", "IMAGE")], mode=BYPASS, title=f"view {i}: {label}")
    w.connect(27, 0, nid, 0, "IMAGE")
    w.add(nid + 10, "Trellis2PreProcessImage_GGUF", [3150, 80 + i * 170], [280, 90],
          [25, True], [("image", "IMAGE")], [("image", "IMAGE")], mode=BYPASS,
          title=f"prep {label} (rembg)")
    w.connect(nid, 0, nid + 10, 0, "IMAGE")

w.add(48, "Trellis2LoadModel_GGUF", [2850, 780], [320, 180],
      ["TRELLIS.2-4B", "GGUF Q4_K_M", "flash_attn", "cuda", True, True], [],
      [("pipeline", "TRELLIS2PIPELINE")], mode=BYPASS)
w.add(49, "Trellis2MeshWithVoxelMultiViewGenerator_GGUF", [3470, 80], [360, 740],
      [12345, "fixed", "1024_cascade",
       12, 6.5, 0.05, 4.0,            # sparse structure
       12, 6.5, 0.05, 4.0,            # shape
       12, 3.0, 0.2, 3.0,             # texture slat
       999999, 32, True,              # max_tokens, ss_resolution, texture slat on
       0.1, 1.0, 0.1, 1.0, 0.0, 0.9,  # guidance intervals
       True, "z", 1.0,                # tiled decoder, front_axis, blend_temperature
       "euler", "euler", "euler"],
      [("pipeline", "TRELLIS2PIPELINE"), ("front_image", "IMAGE"),
       ("back_image", "IMAGE"), ("left_image", "IMAGE"), ("right_image", "IMAGE")],
      [("mesh", "MESHWITHVOXEL"), ("bvh", "BVH")], mode=BYPASS, title="Trellis multiview generator")
w.connect(48, 0, 49, 0, "TRELLIS2PIPELINE")
w.connect(40 + 10, 0, 49, 1, "IMAGE")   # front
w.connect(42 + 10, 0, 49, 2, "IMAGE")   # back
w.connect(43 + 10, 0, 49, 3, "IMAGE")   # left
w.connect(41 + 10, 0, 49, 4, "IMAGE")   # right

w.add(60, "Trellis2PostProcessAndUnWrapAndRasterizer_GGUF", [3870, 80], [360, 620],
      [60.0, 0, 1, 1,                 # mesh cluster
       2048,                          # texture_size
       True, 1.0, 0.0,                # remesh
       200000, "Cumesh", True,        # simplify to 200k, fill holes
       "OPAQUE", "1024", False,       # alpha, dual contouring res, double-side
       True, False, False,            # remove_floaters, bake_on_vertices, custom normals
       "Xatlas", True],               # uv method, remove_inner_faces
      [("mesh", "MESHWITHVOXEL"), ("bvh", "BVH")],
      [("trimesh", "TRIMESH"), ("base_color_texture", "IMAGE"), ("metallic_roughness_texture", "IMAGE")],
      mode=BYPASS, title="Post-process + Xatlas unwrap + texture bake")
w.connect(49, 0, 60, 0, "MESHWITHVOXEL")
w.connect(49, 1, 60, 1, "BVH")

w.add(61, "Trellis2ExportMesh_GGUF", [4270, 80], [300, 110],
      ["3D/13_ASSET_FACTORY", "glb"], [("trimesh", "TRIMESH")], [("glb_path", "STRING")],
      mode=BYPASS)
pv = w.add(62, "Preview3D", [4270, 250], [420, 450], ["", ""],
      [("camera_info", "LOAD3D_CAMERA"), ("bg_image", "IMAGE"), ("model_file", PV3D_TYPE)], [],
      mode=BYPASS)
pv["inputs"][0]["shape"] = 7
pv["inputs"][1]["shape"] = 7
pv["inputs"][2]["widget"] = {"name": "model_file"}
w.add(63, "PreviewImage", [4270, 760], [300, 270], [],
      [("images", "IMAGE")], [], mode=BYPASS, title="Baked base-color texture")
w.connect(60, 0, 61, 0, "TRIMESH")
w.connect(61, 0, 62, 2, "STRING")
w.connect(60, 1, 63, 0, "IMAGE")

# ---------------- Note ----------------
note = ("13 - ASSET FACTORY   concept -> 4 ortho views -> textured 3D asset\n\n"
        "STEP 1 - CONCEPT (group 1, active):\n"
        "  Type your asset prompt, Run (~seconds). Iterate by editing the prompt or\n"
        "  bumping the Seed. Optional: enable the Reference nodes (Ctrl+B) to guide\n"
        "  with an image. KEEP the seed control on 'fixed' — that is what lets the\n"
        "  3D stages reuse the cached concept later.\n\n"
        "STEP 2 - PRESS PLAY ON 3D (groups 2+3):\n"
        "  When you love the concept, select ALL nodes of groups 2 and 3 and press\n"
        "  Ctrl+B to enable, then Run. The concept is NOT regenerated (cache); the\n"
        "  run makes 4 ortho views (~3.5 min) then the textured mesh (~3 min).\n"
        "  Output: output/3D/13_ASSET_FACTORY_*.glb (200k faces, Xatlas UVs, 2048\n"
        "  texture) + ASSET_VIEWS_* (front/right/back/left reference sheet images).\n\n"
        "In Blender: File > Import > glTF. Views = your modeling/paintover reference.\n"
        "Quality knobs: SimplifyMesh target faces, texture_size, GGUF Q5_K_M model.")
w.add(99, "Note", [40, 900], [340, 420], [note], [], [], color="#432")

# ---------------- groups ----------------
w.group(1, "1. CONCEPT — Flux 2 (iterate here)", [20, 0, 1520, 1350], "#3f789e")
w.group(2, "1b. IMAGE REFERENCE (optional — Ctrl+B)", [360, 420, 640, 780], "#a1309b")
w.group(3, "2. MULTIVIEW — 4 ortho views (Ctrl+B when concept approved)", [1620, 0, 1180, 1000], "#3f9b46")
w.group(4, "3. TRELLIS 3D — textured .glb (Ctrl+B with group 2)", [2820, 0, 1900, 1060], "#9b6b3f")

res = w.finalize(os.path.abspath(OUT), wid="asset-factory")
print("wrote", os.path.abspath(OUT), res)
if os.path.isdir(INSTALL):
    shutil.copy(os.path.abspath(OUT), os.path.join(INSTALL, "13_ASSET_FACTORY.json"))
    print("installed to ComfyUI")
