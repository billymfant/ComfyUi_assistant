"""Wan 2.2 14B i2v (general quality upgrade) — dual-expert MoE + lightx2v 4-step.
high_noise expert (steps 0-2) -> low_noise expert (steps 2-4), CFG 1, euler/simple.
Much higher quality than the 5B for plain image-to-video.

Usage: python test_wan14b_i2v.py [start_image.png]
"""
import json, urllib.request, time, uuid, sys

BASE = "http://127.0.0.1:8188"
START = sys.argv[1] if len(sys.argv) > 1 else "char_fullbody.png"
W, H, LEN, FPS = 832, 480, 49, 16
LX = "lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors"
POS = ("a young woman with copper-red curly hair, freckles, teal field jacket, walking "
       "forward, hair and jacket moving in the wind, natural motion, cinematic, detailed")
NEG = "overexposed, static, blurry, low quality, deformed, fused fingers, motionless"

p = {
 "95": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
 "96": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
 "101": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["95", 0], "lora_name": LX, "strength_model": 1.0}},
 "102": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["96", 0], "lora_name": LX, "strength_model": 1.0}},
 "103": {"class_type": "ModelSamplingSD3", "inputs": {"shift": 5.0, "model": ["101", 0]}},  # high
 "104": {"class_type": "ModelSamplingSD3", "inputs": {"shift": 5.0, "model": ["102", 0]}},  # low
 "84": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
 "93": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["84", 0]}},
 "89": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["84", 0]}},
 "90": {"class_type": "VAELoader", "inputs": {"vae_name": "Wan2_1_VAE_bf16.safetensors"}},
 "97": {"class_type": "LoadImage", "inputs": {"image": START}},
 "98": {"class_type": "WanImageToVideo",
        "inputs": {"positive": ["93", 0], "negative": ["89", 0], "vae": ["90", 0],
                   "width": W, "height": H, "length": LEN, "batch_size": 1, "start_image": ["97", 0]}},
 # stage 1 (high expert): steps 0-2, add noise, leave leftover noise
 "86": {"class_type": "KSamplerAdvanced",
        "inputs": {"add_noise": "enable", "noise_seed": 264, "steps": 4, "cfg": 1.0,
                   "sampler_name": "euler", "scheduler": "simple", "start_at_step": 0, "end_at_step": 2,
                   "return_with_leftover_noise": "enable", "model": ["103", 0],
                   "positive": ["98", 0], "negative": ["98", 1], "latent_image": ["98", 2]}},
 # stage 2 (low expert): steps 2-4, no new noise
 "85": {"class_type": "KSamplerAdvanced",
        "inputs": {"add_noise": "disable", "noise_seed": 0, "steps": 4, "cfg": 1.0,
                   "sampler_name": "euler", "scheduler": "simple", "start_at_step": 2, "end_at_step": 4,
                   "return_with_leftover_noise": "disable", "model": ["104", 0],
                   "positive": ["98", 0], "negative": ["98", 1], "latent_image": ["86", 0]}},
 "87": {"class_type": "VAEDecode", "inputs": {"samples": ["85", 0], "vae": ["90", 0]}},
 "94": {"class_type": "CreateVideo", "inputs": {"fps": FPS, "images": ["87", 0]}},
 "108": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "WAN14B_I2V", "format": "auto", "codec": "auto", "video": ["94", 0]}},
}

print("START:", START, "|", W, "x", H, LEN, "frames | dual-expert 14B + lightx2v 4-step")
cid = str(uuid.uuid4())
data = json.dumps({"prompt": p, "client_id": cid}).encode()
req = urllib.request.Request(BASE + "/prompt", data=data, headers={"Content-Type": "application/json"})
try:
    r = json.loads(urllib.request.urlopen(req).read())
except urllib.error.HTTPError as e:
    print("SUBMIT ERROR", e.code); print(e.read().decode()); raise SystemExit
pid = r["prompt_id"]; print("queued", pid)
t0 = time.time()
while time.time() - t0 < 1800:
    h = json.loads(urllib.request.urlopen(BASE + "/history/" + pid).read())
    if pid in h:
        print("status:", h[pid]["status"].get("status_str"))
        print("OUTPUTS:", json.dumps(h[pid].get("outputs", {}))[:300])
        print("ELAPSED %.1fs" % (time.time() - t0)); break
    time.sleep(3)
else:
    print("TIMEOUT")
