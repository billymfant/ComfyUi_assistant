"""SeedVR2 video upscaler test — diffusion-based detail upscale of a generated clip.
Loads a clip from input/, upscales short side to ~1080, saves. Auto-downloads the 3B model.
"""
import json, urllib.request, time, uuid, sys

BASE = "http://127.0.0.1:8188"
SRC = sys.argv[1] if len(sys.argv) > 1 else "seedvr_src.mp4"
CAP = 13  # few frames for a quick validation

p = {
 "1": {"class_type": "VHS_LoadVideo", "inputs": {"video": SRC, "force_rate": 16, "custom_width": 0, "custom_height": 0, "frame_load_cap": CAP, "skip_first_frames": 0, "select_every_nth": 1}},
 "2": {"class_type": "SeedVR2LoadDiTModel", "inputs": {"model": "seedvr2_ema_3b_fp8_e4m3fn.safetensors", "device": "cuda:0", "offload_device": "cpu"}},
 "3": {"class_type": "SeedVR2LoadVAEModel", "inputs": {"model": "ema_vae_fp16.safetensors", "device": "cuda:0"}},
 "4": {"class_type": "SeedVR2VideoUpscaler",
       "inputs": {"image": ["1", 0], "dit": ["2", 0], "vae": ["3", 0], "seed": 42,
                  "resolution": 1080, "max_resolution": 1920, "batch_size": 5,
                  "uniform_batch_size": True, "color_correction": "wavelet", "offload_device": "cpu"}},
 "5": {"class_type": "CreateVideo", "inputs": {"fps": 16, "images": ["4", 0]}},
 "6": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "SEEDVR2_UPSCALE", "format": "auto", "codec": "auto", "video": ["5", 0]}},
}

print("SeedVR2 upscale of", SRC, "| cap", CAP, "frames -> short side 1080")
cid = str(uuid.uuid4())
data = json.dumps({"prompt": p, "client_id": cid}).encode()
req = urllib.request.Request(BASE + "/prompt", data=data, headers={"Content-Type": "application/json"})
try:
    r = json.loads(urllib.request.urlopen(req).read())
except urllib.error.HTTPError as e:
    print("SUBMIT ERROR", e.code); print(e.read().decode()); raise SystemExit
pid = r["prompt_id"]; print("queued", pid)
t0 = time.time()
while time.time() - t0 < 2400:
    h = json.loads(urllib.request.urlopen(BASE + "/history/" + pid).read())
    if pid in h:
        print("status:", h[pid]["status"].get("status_str"))
        print("OUTPUTS:", json.dumps(h[pid].get("outputs", {}))[:300])
        print("ELAPSED %.1fs" % (time.time() - t0)); break
    time.sleep(4)
else:
    print("TIMEOUT")
