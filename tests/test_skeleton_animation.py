"""Phase 2 — skeleton -> character animation (Wan 2.2 Fun-Control 5B).
Driving video -> DWPose skeleton -> drives a character (ref_image) -> animated clip.
Saves BOTH a POSE_PREVIEW (the extracted skeleton, to verify) and SKELETON_ANIM (result).

Usage: python test_skeleton_animation.py [driving_video.mp4] [ref_image.png]
Defaults: DancerInRed.mp4 + char_fullbody.png (both in ComfyUI/input/).
"""
import json, urllib.request, time, uuid, sys

BASE = "http://127.0.0.1:8188"
DRIVE = sys.argv[1] if len(sys.argv) > 1 else "DancerInRed.mp4"
REF = sys.argv[2] if len(sys.argv) > 2 else "char_fullbody.png"
W, H, LEN, FPS = 480, 832, 49, 16

POS = ("a young woman with copper-red curly hair, freckles, wearing a mustard-yellow "
       "raincoat, dancing, full body, studio backdrop, cinematic, sharp focus")
NEG = ("overexposed, static, blurry, subtitles, worst quality, low quality, deformed "
       "limbs, fused fingers, extra limbs, motionless, cluttered background")

p = {
 # models
 "37": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_fun_control_5B_bf16.safetensors", "weight_dtype": "default"}},
 "48": {"class_type": "ModelSamplingSD3", "inputs": {"shift": 8, "model": ["37", 0]}},
 "38": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
 "39": {"class_type": "VAELoader", "inputs": {"vae_name": "wan2.2_vae.safetensors"}},
 # driving video -> frames (capped/normalized)
 "66": {"class_type": "VHS_LoadVideo",
        "inputs": {"video": DRIVE, "force_rate": FPS, "custom_width": W, "custom_height": H,
                   "frame_load_cap": LEN, "skip_first_frames": 0, "select_every_nth": 1}},
 # frames -> DWPose skeleton (torchscript detectors, no onnxruntime dep)
 "68": {"class_type": "DWPreprocessor",
        "inputs": {"image": ["66", 0], "detect_hand": "enable", "detect_body": "enable",
                   "detect_face": "disable", "resolution": H,
                   "bbox_detector": "yolox_l.torchscript.pt",
                   "pose_estimator": "dw-ll_ucoco_384_bs5.torchscript.pt",
                   "scale_stick_for_xinsr_cn": "disable"}},
 # verify: save the skeleton itself
 "90": {"class_type": "CreateVideo", "inputs": {"fps": FPS, "images": ["68", 0]}},
 "91": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "POSE_PREVIEW", "format": "auto", "codec": "auto", "video": ["90", 0]}},
 # character reference
 "70": {"class_type": "LoadImage", "inputs": {"image": REF}},
 "6":  {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["38", 0]}},
 "7":  {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["38", 0]}},
 # fun-control: character + skeleton -> conditioning + latent
 "60": {"class_type": "Wan22FunControlToVideo",
        "inputs": {"positive": ["6", 0], "negative": ["7", 0], "vae": ["39", 0],
                   "width": W, "height": H, "length": LEN, "batch_size": 1,
                   "ref_image": ["70", 0], "control_video": ["68", 0]}},
 "3":  {"class_type": "KSampler",
        "inputs": {"seed": 7, "steps": 20, "cfg": 5, "sampler_name": "uni_pc", "scheduler": "simple",
                   "denoise": 1, "model": ["48", 0], "positive": ["60", 0], "negative": ["60", 1],
                   "latent_image": ["60", 2]}},
 "8":  {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["39", 0]}},
 "57": {"class_type": "CreateVideo", "inputs": {"fps": FPS, "images": ["8", 0]}},
 "58": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "SKELETON_ANIM", "format": "auto", "codec": "auto", "video": ["57", 0]}},
}

print("DRIVE:", DRIVE, "| REF:", REF, "|", W, "x", H, LEN, "frames")
cid = str(uuid.uuid4())
data = json.dumps({"prompt": p, "client_id": cid}).encode()
req = urllib.request.Request(BASE + "/prompt", data=data, headers={"Content-Type": "application/json"})
try:
    r = json.loads(urllib.request.urlopen(req).read())
except urllib.error.HTTPError as e:
    print("SUBMIT ERROR", e.code); print(e.read().decode()); raise SystemExit
pid = r["prompt_id"]; print("queued", pid)
t0 = time.time()
while time.time() - t0 < 1200:
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
