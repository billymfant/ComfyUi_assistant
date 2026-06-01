"""Phase 3 — storyboard -> video orchestrator.

Reads a storyboard (a list of shots) and produces one assembled film by driving the
already-built local workflows via the ComfyUI API:
  - Shot keyframe  : Flux 2 (t2i), with character consistency via ReferenceLatent
                     (shot 1 defines the character; later shots reuse it -> on-model).
  - Shot motion    : Wan 2.2 5B image-to-video.
  - Assembly       : ffmpeg concat of the per-shot clips -> storyboard_final.mp4.

A shot = {"prompt": str, "frames": int}.  The first shot's character is locked and
carried into every later shot via reference, so the same person appears throughout.

Usage:
  python builders/storyboard_to_video.py [storyboard.json]
Without an arg it runs a built-in 2-shot demo.
"""
import json, urllib.request, time, uuid, shutil, os, subprocess, sys

BASE = "http://127.0.0.1:8188"
COMFY = "F:/ComfyUI/ComfyUI-Easy-Install/ComfyUI"
OUT, INP = COMFY + "/output", COMFY + "/input"
W, H, FPS = 832, 480, 24
NEG = ("overexposed, static, blurry, subtitles, worst quality, low quality, deformed, "
       "extra limbs, fused fingers, motionless, cluttered")

DEMO = [
    {"prompt": "cinematic film still, a young woman with copper-red curly hair, freckles, "
               "wearing a teal field jacket, standing in a misty pine forest at dawn, "
               "soft volumetric light, looking slowly around", "frames": 49},
    {"prompt": "cinematic film still, the same woman walking along a sunlit beach at golden "
               "hour, wind moving her hair, gentle smile, waves behind her", "frames": 49},
]

def submit(prompt, timeout):
    cid = str(uuid.uuid4())
    data = json.dumps({"prompt": prompt, "client_id": cid}).encode()
    req = urllib.request.Request(BASE + "/prompt", data=data, headers={"Content-Type": "application/json"})
    try:
        pid = json.loads(urllib.request.urlopen(req).read())["prompt_id"]
    except urllib.error.HTTPError as e:
        print("SUBMIT ERROR", e.code); print(e.read().decode()); raise SystemExit
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.loads(urllib.request.urlopen(BASE + "/history/" + pid).read())
        if pid in h:
            fn = None
            for _, o in h[pid].get("outputs", {}).items():
                for im in o.get("images", []):
                    fn = im["filename"]
            return fn, h[pid]["status"].get("status_str")
        time.sleep(2)
    return None, "timeout"

def flux_loaders(p):
    p["1"] = {"class_type": "UNETLoader", "inputs": {"unet_name": "flux-2-klein-4b-fp8.safetensors", "weight_dtype": "default"}}
    p["2"] = {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_4b.safetensors", "type": "flux2", "device": "default"}}
    p["3"] = {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}}

def keyframe(prompt, idx, ref=None):
    """Flux 2 still; if ref (filename in input/) given, lock identity via ReferenceLatent."""
    p = {}; flux_loaders(p)
    p["4"] = {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}}
    p["5"] = {"class_type": "FluxGuidance", "inputs": {"conditioning": ["4", 0], "guidance": 4.0}}
    cond = ["5", 0]
    if ref:
        p["20"] = {"class_type": "LoadImage", "inputs": {"image": ref}}
        p["21"] = {"class_type": "ImageScale", "inputs": {"image": ["20", 0], "upscale_method": "bicubic", "width": W, "height": H, "crop": "center"}}
        p["22"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["21", 0], "vae": ["3", 0]}}
        p["23"] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["5", 0], "latent": ["22", 0]}}
        cond = ["23", 0]
    p["6"] = {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": W, "height": H, "batch_size": 1}}
    p["7"] = {"class_type": "BasicGuider", "inputs": {"model": ["1", 0], "conditioning": cond}}
    p["8"] = {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}}
    p["9"] = {"class_type": "Flux2Scheduler", "inputs": {"steps": 20, "width": W, "height": H}}
    p["10"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": 1000 + idx}}
    p["11"] = {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["10", 0], "guider": ["7", 0], "sampler": ["8", 0], "sigmas": ["9", 0], "latent_image": ["6", 0]}}
    p["12"] = {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}}
    p["13"] = {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": "SB_KEY_%02d" % idx}}
    return submit(p, 300)

def animate(start_image, prompt, frames, idx):
    """Wan 2.2 5B image-to-video from a keyframe."""
    p = {
     "37": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_ti2v_5B_fp16.safetensors", "weight_dtype": "default"}},
     "38": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
     "39": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}},
     "48": {"class_type": "ModelSamplingSD3", "inputs": {"shift": 8, "model": ["37", 0]}},
     "56": {"class_type": "LoadImage", "inputs": {"image": start_image}},
     "6":  {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["38", 0]}},
     "7":  {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["38", 0]}},
     "55": {"class_type": "Wan22ImageToVideoLatent", "inputs": {"width": W, "height": H, "length": frames, "batch_size": 1, "vae": ["39", 0], "start_image": ["56", 0]}},
     "3":  {"class_type": "KSampler", "inputs": {"seed": 50 + idx, "steps": 20, "cfg": 5, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1, "model": ["48", 0], "positive": ["6", 0], "negative": ["7", 0], "latent_image": ["55", 0]}},
     "8":  {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["39", 0]}},
     "57": {"class_type": "CreateVideo", "inputs": {"fps": FPS, "images": ["8", 0]}},
     "58": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "SB_SHOT_%02d" % idx, "format": "auto", "codec": "auto", "video": ["57", 0]}},
    }
    return submit(p, 900)

def main():
    board = json.load(open(sys.argv[1], encoding="utf-8")) if len(sys.argv) > 1 else DEMO
    print("STORYBOARD: %d shots @ %dx%d" % (len(board), W, H))
    ref = None
    clips = []
    for i, shot in enumerate(board):
        print("\n--- SHOT %d ---\n  prompt: %s" % (i, shot["prompt"][:70]))
        key, st = keyframe(shot["prompt"], i, ref)
        print("  keyframe:", key, st)
        if not key:
            print("  keyframe failed, skipping"); continue
        if ref is None:                              # lock the character from shot 0
            ref = "sb_character.png"
            shutil.copy(os.path.join(OUT, key), os.path.join(INP, ref))
            print("  locked character ->", ref)
        start = "sb_start_%02d.png" % i
        shutil.copy(os.path.join(OUT, key), os.path.join(INP, start))
        clip, st = animate(start, shot["prompt"], shot.get("frames", 49), i)
        print("  clip:", clip, st)
        if clip:
            clips.append(os.path.join(OUT, clip))

    if not clips:
        print("no clips produced"); return
    # assemble with ffmpeg concat (all clips share codec/res/fps -> stream copy)
    listfile = os.path.join(OUT, "sb_list.txt")
    with open(listfile, "w") as f:
        for c in clips:
            f.write("file '%s'\n" % c.replace("\\", "/"))
    final = os.path.join(OUT, "STORYBOARD_FINAL.mp4")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile, "-c", "copy", final]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:                            # fallback: re-encode
        subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", final], capture_output=True, text=True)
    print("\nASSEMBLED:", final, "from", len(clips), "shots")

if __name__ == "__main__":
    main()
