"""Wan-Animate 14B (simplified, pose-only) — character + DWPose skeleton -> faithful animation.
Uses the 14B Wan2.2-Animate model with the lightx2v distill LoRA (CFG 1 / 4 steps).
Skips the ONNX-ViTPose + SAM2 mask path (not installed); drives body via DWPose (Phase 2).

Usage: python test_wan_animate.py [driving_video.mp4] [ref_image.png]
"""
import json, urllib.request, time, uuid, sys

BASE = "http://127.0.0.1:8188"
DRIVE = sys.argv[1] if len(sys.argv) > 1 else "DancerInRed.mp4"
REF = sys.argv[2] if len(sys.argv) > 2 else "char_fullbody.png"
W, H, LEN, FPS = 480, 832, 49, 16
MODEL = "Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors"
LIGHTX2V = "lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors"
POS = "a young woman with copper-red curly hair, freckles, teal field jacket, dancing, full body, studio"

p = {
 # model + distill LoRA (enables CFG1 / 4-step)
 "10": {"class_type": "DiffusionModelLoaderKJ",
        "inputs": {"model_name": MODEL, "weight_dtype": "fp8_e4m3fn", "compute_dtype": "bf16",
                   "patch_cublaslinear": False, "sage_attention": "disabled",
                   "enable_fp16_accumulation": False}},
 "11": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["10", 0], "lora_name": LIGHTX2V, "strength_model": 1.0}},
 # text / vae
 "20": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
 "21": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["20", 0]}},
 "22": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["21", 0]}},
 "23": {"class_type": "VAELoader", "inputs": {"vae_name": "Wan2_1_VAE_bf16.safetensors"}},
 # driving video -> DWPose skeleton (pose_video)
 "30": {"class_type": "VHS_LoadVideo",
        "inputs": {"video": DRIVE, "force_rate": FPS, "custom_width": W, "custom_height": H,
                   "frame_load_cap": LEN, "skip_first_frames": 0, "select_every_nth": 1}},
 "31": {"class_type": "DWPreprocessor",
        "inputs": {"image": ["30", 0], "detect_hand": "enable", "detect_body": "enable",
                   "detect_face": "enable", "resolution": H,
                   "bbox_detector": "yolox_l.torchscript.pt",
                   "pose_estimator": "dw-ll_ucoco_384_bs5.torchscript.pt",
                   "scale_stick_for_xinsr_cn": "disable"}},
 # character reference
 "40": {"class_type": "LoadImage", "inputs": {"image": REF}},
 "41": {"class_type": "ImageScale", "inputs": {"image": ["40", 0], "upscale_method": "lanczos", "width": W, "height": H, "crop": "center"}},
 # animate node
 "50": {"class_type": "WanAnimateToVideo",
        "inputs": {"positive": ["21", 0], "negative": ["22", 0], "vae": ["23", 0],
                   "width": W, "height": H, "length": LEN, "batch_size": 1,
                   "continue_motion_max_frames": 5, "video_frame_offset": 0,
                   "reference_image": ["41", 0], "pose_video": ["31", 0]}},
 # 4-step LCM sampling
 "60": {"class_type": "CFGGuider", "inputs": {"model": ["11", 0], "positive": ["50", 0], "negative": ["50", 1], "cfg": 1.0}},
 "61": {"class_type": "BasicScheduler", "inputs": {"model": ["11", 0], "scheduler": "simple", "steps": 4, "denoise": 1.0}},
 "62": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "lcm"}},
 "63": {"class_type": "RandomNoise", "inputs": {"noise_seed": 42}},
 "64": {"class_type": "SamplerCustomAdvanced",
        "inputs": {"noise": ["63", 0], "guider": ["60", 0], "sampler": ["62", 0], "sigmas": ["61", 0], "latent_image": ["50", 2]}},
 "70": {"class_type": "VAEDecode", "inputs": {"samples": ["64", 0], "vae": ["23", 0]}},
 "71": {"class_type": "CreateVideo", "inputs": {"fps": FPS, "images": ["70", 0]}},
 "72": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "WAN_ANIMATE", "format": "auto", "codec": "auto", "video": ["71", 0]}},
}

print("DRIVE:", DRIVE, "| REF:", REF, "|", W, "x", H, LEN, "frames | model:", MODEL)
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
        st = h[pid]["status"]
        print("status:", st.get("status_str"), "completed:", st.get("completed"))
        print("OUTPUTS:", json.dumps(h[pid].get("outputs", {}), ensure_ascii=False)[:400])
        print("ELAPSED %.1fs" % (time.time() - t0))
        break
    time.sleep(3)
else:
    print("TIMEOUT")
