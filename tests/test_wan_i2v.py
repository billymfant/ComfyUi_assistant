"""Wan 2.2 TI2V-5B smoke test (native ComfyUI nodes).
Usage:
  python test_wan_i2v.py                 # text-to-video (no input image)
  python test_wan_i2v.py my_char.png     # image-to-video; file must be in ComfyUI/input/
Validates the Phase-0 video foundation: model loads, produces frames, saves a clip.
Short settings (49 frames ~2s, 1280x704) for a fast validation; bump length to 121 for 5s.
"""
import json, urllib.request, time, uuid, sys

BASE = "http://127.0.0.1:8188"
start_image = sys.argv[1] if len(sys.argv) > 1 else None
mode = "I2V" if start_image else "T2V"

POS = ("A street musician plays guitar in a sunlit plaza, gentle breeze moving his "
       "jacket, pigeons taking off, cinematic, the camera slowly pushes in.")
NEG = ("color tones overexposed, static, blurry details, subtitles, overall gray, "
       "worst quality, low quality, deformed limbs, fused fingers, motionless, "
       "cluttered background")

prompt = {
 "37": {"class_type": "UNETLoader",
        "inputs": {"unet_name": "wan2.2_ti2v_5B_fp16.safetensors", "weight_dtype": "default"}},
 "38": {"class_type": "CLIPLoader",
        "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
 "39": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}},
 "48": {"class_type": "ModelSamplingSD3", "inputs": {"shift": 8, "model": ["37", 0]}},
 "6":  {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["38", 0]}},
 "7":  {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["38", 0]}},
 "55": {"class_type": "Wan22ImageToVideoLatent",
        "inputs": {"width": 1280, "height": 704, "length": 49, "batch_size": 1, "vae": ["39", 0]}},
 "3":  {"class_type": "KSampler",
        "inputs": {"seed": 12345, "steps": 20, "cfg": 5, "sampler_name": "uni_pc",
                   "scheduler": "simple", "denoise": 1,
                   "model": ["48", 0], "positive": ["6", 0], "negative": ["7", 0],
                   "latent_image": ["55", 0]}},
 "8":  {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["39", 0]}},
 "57": {"class_type": "CreateVideo", "inputs": {"fps": 24, "images": ["8", 0]}},
 "58": {"class_type": "SaveVideo",
        "inputs": {"filename_prefix": "WAN_%s_TEST" % mode, "format": "auto", "codec": "auto",
                   "video": ["57", 0]}},
}

if start_image:
    prompt["56"] = {"class_type": "LoadImage", "inputs": {"image": start_image}}
    prompt["55"]["inputs"]["start_image"] = ["56", 0]

print("MODE:", mode, "| start_image:", start_image)
cid = str(uuid.uuid4())
data = json.dumps({"prompt": prompt, "client_id": cid}).encode()
req = urllib.request.Request(BASE + "/prompt", data=data, headers={"Content-Type": "application/json"})
try:
    r = json.loads(urllib.request.urlopen(req).read())
except urllib.error.HTTPError as e:
    print("SUBMIT ERROR", e.code); print(e.read().decode()); raise SystemExit
pid = r["prompt_id"]; print("queued", pid)
t0 = time.time()
while time.time() - t0 < 900:
    h = json.loads(urllib.request.urlopen(BASE + "/history/" + pid).read())
    if pid in h:
        st = h[pid]["status"]
        print("status:", st.get("status_str"), "completed:", st.get("completed"))
        print("OUTPUTS:", json.dumps(h[pid].get("outputs", {}), ensure_ascii=False))
        print("ELAPSED %.1fs" % (time.time() - t0))
        break
    time.sleep(3)
else:
    print("TIMEOUT")
