"""Phase 1 — character consistency via Flux 2 native reference (no new models).
Step A: generate a distinctive character (portrait).
Step B: copy it into ComfyUI/input/, then regenerate the SAME character in a new
        pose + scene using ReferenceLatent. Visually compare identity.
"""
import json, urllib.request, time, uuid, shutil, os

BASE = "http://127.0.0.1:8188"
OUT = "F:/ComfyUI/ComfyUI-Easy-Install/ComfyUI/output"
INP = "F:/ComfyUI/ComfyUI-Easy-Install/ComfyUI/input"

CHAR = ("portrait of a young woman with curly copper-red hair, green eyes, light "
        "freckles, wearing a mustard-yellow raincoat, plain neutral grey studio "
        "background, soft even lighting, sharp focus, photorealistic")

def run(prompt, label):
    cid = str(uuid.uuid4())
    data = json.dumps({"prompt": prompt, "client_id": cid}).encode()
    req = urllib.request.Request(BASE + "/prompt", data=data, headers={"Content-Type": "application/json"})
    try:
        r = json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        print(label, "SUBMIT ERROR", e.code); print(e.read().decode()); raise SystemExit
    pid = r["prompt_id"]; print(label, "queued", pid)
    t0 = time.time()
    while time.time() - t0 < 300:
        h = json.loads(urllib.request.urlopen(BASE + "/history/" + pid).read())
        if pid in h:
            print(label, "status:", h[pid]["status"].get("status_str"))
            fn = None
            for _, o in h[pid].get("outputs", {}).items():
                for im in o.get("images", []):
                    fn = im["filename"]; print(label, "IMAGE:", im)
            print(label, "ELAPSED %.1fs" % (time.time() - t0))
            return fn
        time.sleep(2)
    print(label, "TIMEOUT"); return None

def flux_loaders(p):
    p["1"] = {"class_type": "UNETLoader", "inputs": {"unet_name": "flux-2-klein-4b-fp8.safetensors", "weight_dtype": "default"}}
    p["2"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2", "device": "default"}}
    p["3"] = {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}}

# --- Step A: base character ---
pa = {}
flux_loaders(pa)
pa["4"] = {"class_type": "CLIPTextEncode", "inputs": {"text": CHAR, "clip": ["2", 0]}}
pa["5"] = {"class_type": "FluxGuidance", "inputs": {"conditioning": ["4", 0], "guidance": 4.0}}
pa["6"] = {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": 1024, "height": 1024, "batch_size": 1}}
pa["7"] = {"class_type": "BasicGuider", "inputs": {"model": ["1", 0], "conditioning": ["5", 0]}}
pa["8"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}}
pa["9"] = {"class_type": "Flux2Scheduler", "inputs": {"steps": 20, "width": 1024, "height": 1024}}
pa["10"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": 4242}}
pa["11"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["10", 0], "guider": ["7", 0], "sampler": ["8", 0], "sigmas": ["9", 0], "latent_image": ["6", 0]}}
pa["12"] = {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}}
pa["13"] = {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": "CHAR_BASE"}}
base = run(pa, "[A base]")
if not base:
    raise SystemExit("base generation failed")

# copy base into input/ for reference use
src = os.path.join(OUT, base)
ref_name = "char_ref.png"
shutil.copy(src, os.path.join(INP, ref_name))
print("[copy] base ->", os.path.join(INP, ref_name))

# --- Step B: same character, new pose + scene via reference ---
NEW = ("full body shot of the same woman walking through a rainy neon-lit city "
       "street at night, holding an umbrella, dynamic pose, cinematic, "
       "preserve her face, copper-red curly hair, freckles and yellow raincoat")
pb = {}
flux_loaders(pb)
pb["4"] = {"class_type": "CLIPTextEncode", "inputs": {"text": NEW, "clip": ["2", 0]}}
pb["5"] = {"class_type": "FluxGuidance", "inputs": {"conditioning": ["4", 0], "guidance": 4.0}}
pb["20"] = {"class_type": "LoadImage", "inputs": {"image": ref_name}}
pb["21"] = {"class_type": "ImageScale", "inputs": {"image": ["20", 0], "upscale_method": "bicubic", "width": 1024, "height": 1024, "crop": "center"}}
pb["22"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["21", 0], "vae": ["3", 0]}}
pb["23"] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["5", 0], "latent": ["22", 0]}}
pb["6"] = {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": 768, "height": 1280, "batch_size": 1}}
pb["7"] = {"class_type": "BasicGuider", "inputs": {"model": ["1", 0], "conditioning": ["23", 0]}}
pb["8"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}}
pb["9"] = {"class_type": "Flux2Scheduler", "inputs": {"steps": 20, "width": 768, "height": 1280}}
pb["10"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": 99}}
pb["11"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["10", 0], "guider": ["7", 0], "sampler": ["8", 0], "sigmas": ["9", 0], "latent_image": ["6", 0]}}
pb["12"] = {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}}
pb["13"] = {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": "CHAR_NEWPOSE"}}
newpose = run(pb, "[B newpose]")
print("RESULT base:", base, "| newpose:", newpose)
