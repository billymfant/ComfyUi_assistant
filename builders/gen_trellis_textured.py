"""Generate workflows/3d modeling helper/12_TRELLIS_TEXTURED.json — image -> TEXTURED 3D asset .glb.

Clean textured Trellis 2 GGUF chain built against the CURRENT installed node widget order
(the pack's example workflows have stale widget layouts and misalign on load). Settings per
the validated recipe: 200k faces, uv_unwrap_method=Xatlas, texture_size 2048.
Seed widgets include the "fixed" control_after_generate token (frontend adds a control
widget for any INT input named `seed` — omitting the token shifts every later widget).
Run:
    python_embeded/python.exe builders/gen_trellis_textured.py
"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wf_lib import WF

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "workflows", "3d modeling helper", "12_TRELLIS_TEXTURED.json")
INSTALL = "F:/ComfyUI/ComfyUI-Easy-Install/ComfyUI/user/default/workflows/3d modeling helper"

PV3D_TYPE = "STRING,FILE_3D_GLB,FILE_3D_GLTF,FILE_3D_FBX,FILE_3D_OBJ,FILE_3D_STL,FILE_3D_USDZ,FILE_3D"

w = WF()
# id, type, pos, size, widgets, inputs[(name,type)], outputs[(name,type)]
w.add(1, "Trellis2LoadImageWithTransparency_GGUF", [40, 60], [320, 340],
      ["example.png", "image"], [],
      [("image", "IMAGE"), ("mask", "MASK"), ("image_with_alpha", "IMAGE")],
      title="Input image (subject on plain/transparent bg)")
w.add(2, "Trellis2PreProcessImage_GGUF", [40, 460], [300, 90],
      [0, False], [("image", "IMAGE")], [("image", "IMAGE")])
w.add(3, "Trellis2LoadModel_GGUF", [40, 610], [320, 180],
      ["TRELLIS.2-4B", "GGUF Q4_K_M", "flash_attn", "cuda", True, True], [],
      [("pipeline", "TRELLIS2PIPELINE")])
w.add(4, "Trellis2MeshWithVoxelAdvancedGenerator_GGUF", [420, 60], [360, 720],
      [12345, "fixed", "1024_cascade",
       12, 6.5, 0.05, 4.0,          # sparse structure
       12, 6.5, 0.05, 4.0,          # shape
       12, 3.0, 0.2, 3.0,           # texture slat
       49152, 4, 32, True,          # max_tokens, max_views, ss_resolution, texture slat on
       0.1, 1.0, 0.1, 1.0, 0.0, 0.9,  # guidance intervals
       True,                        # use_tiled_decoder
       "euler", "euler", "euler"],
      [("pipeline", "TRELLIS2PIPELINE"), ("image", "IMAGE")],
      [("mesh", "MESHWITHVOXEL"), ("bvh", "BVH")], title="Trellis generator")
w.add(5, "Trellis2Remesh_GGUF", [820, 60], [300, 160],
      [1.0, 0.0, "Auto", True, True], [("mesh", "MESHWITHVOXEL")], [("mesh", "MESHWITHVOXEL")])
w.add(6, "Trellis2SimplifyMesh_GGUF", [820, 280], [300, 100],
      [200000, "Cumesh"], [("mesh", "MESHWITHVOXEL")], [("mesh", "MESHWITHVOXEL")],
      title="Simplify (200k = clean-up-friendly)")
w.add(7, "Trellis2FillHolesWithMeshlib_GGUF", [820, 440], [300, 70],
      [], [("mesh", "MESHWITHVOXEL")], [("mesh", "MESHWITHVOXEL"), ("holes_filled", "INT")])
w.add(8, "Trellis2MeshWithVoxelToTrimesh_GGUF", [820, 570], [300, 90],
      ["90 degrees"], [("mesh", "MESHWITHVOXEL")], [("trimesh", "TRIMESH")])
w.add(9, "Trellis2MeshTexturing_GGUF", [1160, 60], [360, 680],
      [0, "fixed",
       12, 3.0, 0.2, 3.0,           # texture steps / guidance
       1024, 2048,                  # resolution, texture_size
       "OPAQUE", False, 0.0, 0.9, 4,
       False, False, "Xatlas",      # bake_on_vertices, use_custom_normals, uv method
       60.0, False, 512, 24, False, 120, 48, "euler"],
      [("pipeline", "TRELLIS2PIPELINE"), ("image", "IMAGE"), ("trimesh", "TRIMESH")],
      [("trimesh", "TRIMESH"), ("base_color_texture", "IMAGE"), ("metallic_roughness_texture", "IMAGE")],
      title="Texturing (Xatlas — only working uv method)")
w.add(10, "Trellis2ExportMesh_GGUF", [1560, 60], [300, 110],
      ["3D/12_TRELLIS_TEXTURED", "glb"], [("trimesh", "TRIMESH")], [("glb_path", "STRING")])
pv = w.add(11, "Preview3D", [1560, 230], [420, 450], ["", ""],
      [("camera_info", "LOAD3D_CAMERA"), ("bg_image", "IMAGE"), ("model_file", PV3D_TYPE)], [])
pv["inputs"][0]["shape"] = 7
pv["inputs"][1]["shape"] = 7
pv["inputs"][2]["widget"] = {"name": "model_file"}
w.add(12, "PreviewImage", [1560, 740], [300, 270], [],
      [("images", "IMAGE")], [], title="Baked base-color texture")

note = ("12 - TRELLIS TEXTURED  (single image -> textured 3D asset)\n\n"
        "1. Put your concept image (subject on plain or transparent background,\n"
        "   e.g. from workflow 01) in ComfyUI/input and pick it in the loader.\n"
        "2. Run. Output: output/3D/12_TRELLIS_TEXTURED_*.glb with UVs + baked texture.\n\n"
        "Defaults = the validated recipe: 200,000 faces, Xatlas unwrap, 2048 texture\n"
        "(~2 min on the 4080S). More detail: SimplifyMesh 500k-2M (slower to unwrap).\n"
        "Sharper texture: texture_size 4096. Q5_K_M in LoadModel = a bit better, slower.\n"
        "For a better mesh from 4 views, use 13_ASSET_FACTORY instead.")
w.add(99, "Note", [40, 860], [340, 300], [note], [], [], color="#432")

w.connect(1, 2, 2, 0, "IMAGE")            # load.image_with_alpha(slot 2!) -> prep.image
w.connect(3, 0, 4, 0, "TRELLIS2PIPELINE")
w.connect(2, 0, 4, 1, "IMAGE")
w.connect(4, 0, 5, 0, "MESHWITHVOXEL")
w.connect(5, 0, 6, 0, "MESHWITHVOXEL")
w.connect(6, 0, 7, 0, "MESHWITHVOXEL")
w.connect(7, 0, 8, 0, "MESHWITHVOXEL")
w.connect(3, 0, 9, 0, "TRELLIS2PIPELINE")
w.connect(2, 0, 9, 1, "IMAGE")
w.connect(8, 0, 9, 2, "TRIMESH")
w.connect(9, 0, 10, 0, "TRIMESH")
w.connect(10, 0, 11, 2, "STRING")
w.connect(9, 1, 12, 0, "IMAGE")

w.group(1, "TRELLIS TEXTURED — image -> textured .glb (Xatlas, 200k)", [20, 0, 1980, 1180], "#3f5f9e")
res = w.finalize(os.path.abspath(OUT), wid="trellis-textured")
print("wrote", os.path.abspath(OUT), res)
if os.path.isdir(INSTALL):
    shutil.copy(os.path.abspath(OUT), os.path.join(INSTALL, "12_TRELLIS_TEXTURED.json"))
    print("installed to ComfyUI")
