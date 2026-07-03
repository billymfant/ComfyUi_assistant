"""Generate workflows/11_TRELLIS_BLOCKOUT.json — image -> rough 3D blockout .glb.

Fast geometry-only Trellis 2 path (no texture, decimated to ~150k faces) for a Blender
blockout. Widget values match the installed Trellis2-GGUF node signatures (2026-07). Run:
    python_embeded/python.exe builders/gen_ortho_blockout.py
"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wf_lib import WF

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "workflows", "3d modeling helper", "11_TRELLIS_BLOCKOUT.json")
INSTALL = "F:/ComfyUI/ComfyUI-Easy-Install/ComfyUI/user/default/workflows/3d modeling helper"

w = WF()
# id, type, pos, size, widgets, inputs[(name,type)], outputs[(name,type)]
w.add(1, "Trellis2LoadImageWithTransparency_GGUF", [40, 40], [300, 100],
      ["example.png", "image"], [], [("image", "IMAGE"), ("mask", "MASK"), ("image_with_alpha", "IMAGE")])
w.add(2, "Trellis2PreProcessImage_GGUF", [40, 200], [280, 90],
      [0, False], [("image", "IMAGE")], [("image", "IMAGE")])
w.add(3, "Trellis2LoadModel_GGUF", [40, 340], [300, 160],
      ["TRELLIS.2-4B", "GGUF Q4_K_M", "flash_attn", "cuda", True, True], [],
      [("pipeline", "TRELLIS2PIPELINE")])
w.add(4, "Trellis2MeshWithVoxelGenerator_GGUF", [380, 120], [320, 320],
      [0, "fixed", "512", 12, 12, 1, 49152, 32, 4, False, True, "euler"],
      [("pipeline", "TRELLIS2PIPELINE"), ("image", "IMAGE")],
      [("mesh", "MESHWITHVOXEL"), ("bvh", "BVH")])
w.add(5, "Trellis2SimplifyMesh_GGUF", [740, 120], [280, 100],
      [150000, "Cumesh"], [("mesh", "MESHWITHVOXEL")], [("mesh", "MESHWITHVOXEL")])
w.add(6, "Trellis2MeshWithVoxelToTrimesh_GGUF", [740, 260], [280, 90],
      ["90 degrees"], [("mesh", "MESHWITHVOXEL")], [("trimesh", "TRIMESH")])
w.add(7, "Trellis2ExportMesh_GGUF", [1060, 120], [280, 110],
      ["OrthoKit_Blockout", "glb"], [("trimesh", "TRIMESH")], [("glb_path", "STRING")])

w.connect(1, 2, 2, 0, "IMAGE")          # load.image_with_alpha(2) -> prep.image
w.connect(3, 0, 4, 0, "TRELLIS2PIPELINE")
w.connect(2, 0, 4, 1, "IMAGE")
w.connect(4, 0, 5, 0, "MESHWITHVOXEL")  # gen.mesh -> simplify
w.connect(5, 0, 6, 0, "MESHWITHVOXEL")  # simplify -> toTrimesh
w.connect(6, 0, 7, 0, "TRIMESH")        # toTrimesh -> export

w.group(1, "TRELLIS BLOCKOUT — image -> rough .glb for Blender", [20, 0, 1340, 520], "#3f5f9e")
res = w.finalize(os.path.abspath(OUT))
print("wrote", os.path.abspath(OUT), res)
if os.path.isdir(INSTALL):
    shutil.copy(os.path.abspath(OUT), os.path.join(INSTALL, "11_TRELLIS_BLOCKOUT.json"))
    print("installed to ComfyUI")
