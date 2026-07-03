"""3D Modeling Assistant - Ortho Kit driver.

Turns ONE concept image (subject on plain/transparent bg, already in ComfyUI/input)
into a complete modeling-reference kit:

  1. MV-Adapter (SDXL)   -> 4 crisp orthographic SIDE views (front/back/left/right)
  2. Trellis 2 (GGUF)    -> rough 3D blockout mesh (.glb) for Blender
  3. ortho_render        -> geometrically-correct TOP/BOTTOM from that mesh
  4. assemble_sheet      -> labeled turnaround "blueprint" (crisp sides + mesh top/bottom)

Output kit folder gets: sheet.png, the 6 individual views, and blockout.glb.

The heavy generation runs on the live ComfyUI server (POST /prompt); the mesh render +
sheet run locally in this (embedded) python. Server must be up at 127.0.0.1:8188.

Usage:
    python make_ortho_kit.py INPUT_IMAGE_NAME [--title "Name"] [--out DIR]
      INPUT_IMAGE_NAME = filename that exists in ComfyUI/input (subject, plain bg)
"""
import json, urllib.request, urllib.parse, os, time, sys, argparse, shutil, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ortho_render, assemble_sheet

os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
H = "http://127.0.0.1:8188"
COMFY = "F:/ComfyUI/ComfyUI-Easy-Install/ComfyUI"

# ---------- ComfyUI helpers ----------
_cache = {}
def info(t):
    if t not in _cache:
        _cache[t] = json.load(urllib.request.urlopen(H + "/object_info/" + urllib.parse.quote(t)))[t]
    return _cache[t]

def defaults(t):
    di = info(t); allin = {**di['input'].get('required', {}), **di['input'].get('optional', {})}
    CONN = {"IMAGE","MASK","MODEL","TRELLIS2PIPELINE","MESHWITHVOXEL","BVH","TRIMESH",
            "LATENT","CONDITIONING","CLIP","VAE","PIPELINE","AUTOENCODER","SCHEDULER","FUNCTION","LIST"}
    out = {}
    for name, spec in allin.items():
        ts = spec[0]
        if isinstance(ts, str) and ts in CONN: continue
        if isinstance(ts, list):
            out[name] = spec[1].get("default", ts[0]) if len(spec) > 1 and isinstance(spec[1], dict) else ts[0]
        elif ts in ("INT","FLOAT","STRING","BOOLEAN"):
            out[name] = spec[1].get("default") if len(spec) > 1 and isinstance(spec[1], dict) else None
    return out

def node(t, **over):
    d = defaults(t); d.update(over); return {"class_type": t, "inputs": d}

def run(prompt, label, timeout=600):
    body = json.dumps({"prompt": prompt}).encode()
    r = json.load(urllib.request.urlopen(urllib.request.Request(H + "/prompt", body, {"Content-Type": "application/json"})))
    if r.get("node_errors"):
        raise RuntimeError(f"{label} node_errors: {json.dumps(r['node_errors'])[:500]}")
    pid = r["prompt_id"]; t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.load(urllib.request.urlopen(H + "/history/" + pid))
        if pid in h:
            st = h[pid]["status"]
            if st.get("status_str") == "error":
                msgs = [m[1] for m in st.get("messages", []) if m[0] == "execution_error"]
                raise RuntimeError(f"{label} error: {msgs[0]['exception_message'][:300] if msgs else '?'}")
            print(f"  [{label}] done in {int(time.time()-t0)}s")
            return h[pid]
        time.sleep(3)
    raise TimeoutError(f"{label} timed out")

def outputs_images(hist):
    """Collect saved/temp image file paths from a history entry, in node+order."""
    paths = []
    for nid, o in hist.get("outputs", {}).items():
        for im in o.get("images", []):
            sub = im.get("subfolder", ""); typ = im.get("type", "output")
            root = {"output": COMFY + "/output", "temp": COMFY + "/temp", "input": COMFY + "/input"}[typ]
            paths.append((nid, os.path.join(root, sub, im["filename"])))
    return paths

# ---------- stage graphs ----------
def mvadapter_sides(image_name, prompt_text, seed):
    """4 orthographic sides via MV-Adapter LDM i2mv. Returns history."""
    p = {}
    p["vae"] = node("LdmVaeLoader", vae_name="sdxl_vae.safetensors", upcast_fp32=True)
    p["pipe"] = node("LdmPipelineLoader", ckpt_name="sd_xl_base_1.0.safetensors",
                     pipeline_name="MVAdapterI2MVSDXLPipeline")
    p["sched"] = node("DiffusersMVSchedulerLoader", pipeline=["pipe", 0],
                      scheduler_name="DDPM", shift_snr=True, shift_mode="interpolated", shift_scale=8.0)
    p["makeup"] = node("DiffusersMVModelMakeup", pipeline=["pipe", 0], scheduler=["sched", 0],
                       autoencoder=["vae", 0], load_mvadapter=True, adapter_path="huanngzh/mv-adapter",
                       adapter_name="mvadapter_i2mv_sdxl.safetensors", num_views=4)
    p["birefnet"] = node("BiRefNet", ckpt_name="ZhengPeng7/BiRefNet")  # non-gated (briaai/RMBG-2.0 is gated)
    p["load"] = node("LoadImage", image=image_name)
    p["prep"] = node("ImagePreprocessor", remove_bg_fn=["birefnet", 0], image=["load", 0], height=768, width=768)
    p["views"] = node("ViewSelector", front_view=True, front_right_view=False, right_view=True,
                      back_view=True, left_view=True, front_left_view=False)   # front,right,back,left
    p["sampler"] = node("DiffusersMVSampler", pipeline=["makeup", 0], num_views=4, prompt=prompt_text,
                        negative_prompt="watermark, ugly, deformed, noisy, blurry, low contrast",
                        width=768, height=768, steps=40, cfg=3.0, seed=seed,
                        reference_image=["prep", 0], azimuth_degrees=["views", 0])
    p["save"] = node("SaveImage", images=["sampler", 0], filename_prefix="OrthoKit_side")
    return run(p, "MV-Adapter sides", timeout=600)

def trellis_blockout(image_name, prefix, seed):
    """Fast geometry-only blockout -> glb path (relative to output)."""
    p = {}
    p["load"] = node("Trellis2LoadImageWithTransparency_GGUF", image=image_name)
    p["prep"] = node("Trellis2PreProcessImage_GGUF", image=["load", 2])
    p["model"] = node("Trellis2LoadModel_GGUF", modelname="TRELLIS.2-4B", model_format="GGUF Q4_K_M",
                      backend="flash_attn", device="cuda", low_vram=True, keep_models_loaded=True)
    p["gen"] = node("Trellis2MeshWithVoxelGenerator_GGUF", pipeline=["model", 0], image=["prep", 0], seed=seed,
                    pipeline_type="512", sparse_structure_steps=12, shape_steps=12, texture_steps=1,
                    generate_texture_slat=False, use_tiled_decoder=True)
    p["simp"] = node("Trellis2SimplifyMesh_GGUF", mesh=["gen", 0], target_face_num=150000, method="Cumesh")
    p["tri"] = node("Trellis2MeshWithVoxelToTrimesh_GGUF", mesh=["simp", 0], reorient_vertices="90 degrees")
    p["export"] = node("Trellis2ExportMesh_GGUF", trimesh=["tri", 0], filename_prefix=prefix, file_format="glb")
    p["show"] = {"class_type": "Show any [Crystools]",
                 "inputs": {"any_value": ["export", 0], "console": True, "display": "", "prefix": "GLB: "}}
    run(p, "Trellis blockout", timeout=600)
    # export writes output/<prefix>_00001_.glb (newest matching)
    import glob
    cands = sorted(glob.glob(f"{COMFY}/output/{prefix}*_.glb"), key=os.path.getmtime)
    if not cands:
        raise RuntimeError("blockout glb not found")
    return cands[-1]

# ---------- driver ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image", help="filename in ComfyUI/input (subject, plain/transparent bg)")
    ap.add_argument("--title", default=None)
    ap.add_argument("--out", default=None, help="kit output dir")
    ap.add_argument("--prompt", default="clean 3d character render, neutral studio background, consistent subject")
    ap.add_argument("--seed", type=int, default=random.randint(1, 10**8))
    a = ap.parse_args()
    title = a.title or os.path.splitext(a.image)[0]
    out = a.out or (COMFY + "/output/OrthoKit_" + "".join(ch for ch in title if ch.isalnum())[:24])
    os.makedirs(out, exist_ok=True)
    print(f"== Ortho Kit: {title} -> {out}")

    print("[1/4] MV-Adapter sides ...")
    hist = mvadapter_sides(a.image, a.prompt, a.seed)
    side_imgs = [pth for _, pth in outputs_images(hist)]
    # SaveImage yields the 4 views in ViewSelector order: front, right, back, left
    order = ["front", "right", "back", "left"]
    views = {}
    for name, src in zip(order, side_imgs[-4:]):
        dst = os.path.join(out, f"{name}.png"); shutil.copy(src, dst); views[name] = dst

    print("[2/4] Trellis blockout mesh ...")
    glb = trellis_blockout(a.image, "OrthoKit_" + "".join(ch for ch in title if ch.isalnum())[:16], a.seed)
    shutil.copy(glb, os.path.join(out, "blockout.glb"))

    print("[3/4] render top/bottom from mesh ...")
    ras = ortho_render.render_six(glb, os.path.join(out, "_mesh"), size=768, target_faces=60000)
    for name in ("top", "bottom"):
        dst = os.path.join(out, f"{name}.png"); shutil.copy(ras[name], dst); views[name] = dst

    print("[4/4] assemble sheet ...")
    sheet = assemble_sheet.assemble(views, os.path.join(out, "sheet.png"), cell=768,
                                    title=f"{title} - Orthographic Modeling Reference")
    print("DONE")
    print("  sheet :", sheet)
    print("  mesh  :", os.path.join(out, "blockout.glb"))
    print("  views :", ", ".join(views))

if __name__ == "__main__":
    main()
