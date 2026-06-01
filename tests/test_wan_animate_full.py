"""Wan-Animate 14B FULL fidelity — ViTPose body+face + SAM2 character mask + background.
Driving video -> ViTPose(pose+face) + YOLO bboxes -> SAM2 mask -> WanAnimateToVideo with
reference_image + pose_video + face_video + background_video + character_mask.
ONNX on CPUExecutionProvider (no onnxruntime-gpu needed). Slow first run (CPU pose + SAM2 dl).

Usage: python test_wan_animate_full.py [driving_video.mp4] [ref_image.png]
"""
import json, urllib.request, time, uuid, sys

BASE = "http://127.0.0.1:8188"
DRIVE = sys.argv[1] if len(sys.argv) > 1 else "DancerInRed.mp4"
REF = sys.argv[2] if len(sys.argv) > 2 else "char_fullbody.png"
W, H, LEN, FPS = 480, 832, 25, 16          # 25 frames keeps CPU-ViTPose tractable
MODEL = "Wan2_2-Animate-14B_fp8_scaled_e4m3fn_KJ_v2.safetensors"
LX = "lightx2v_I2V_14B_480p_cfg_step_distill_rank64_bf16.safetensors"
RELIGHT = "WanAnimate_relight_lora_fp16.safetensors"
POS = "a young woman with copper-red curly hair, freckles, teal field jacket, full body"

p = {
 # ---- model + LoRAs ----
 "10": {"class_type": "DiffusionModelLoaderKJ", "inputs": {"model_name": MODEL, "weight_dtype": "fp8_e4m3fn", "compute_dtype": "bf16", "patch_cublaslinear": False, "sage_attention": "disabled", "enable_fp16_accumulation": False}},
 "11": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["10", 0], "lora_name": LX, "strength_model": 1.0}},
 "12": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["11", 0], "lora_name": RELIGHT, "strength_model": 1.0}},
 # ---- text + vae ----
 "20": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
 "21": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["20", 0]}},
 "22": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["21", 0]}},
 "23": {"class_type": "VAELoader", "inputs": {"vae_name": "Wan2_1_VAE_bf16.safetensors"}},
 # ---- driving video ----
 "30": {"class_type": "VHS_LoadVideo", "inputs": {"video": DRIVE, "force_rate": FPS, "custom_width": W, "custom_height": H, "frame_load_cap": LEN, "skip_first_frames": 0, "select_every_nth": 1}},
 # ---- ONNX pose + face detection (CPU) ----
 "31": {"class_type": "OnnxDetectionModelLoader", "inputs": {"vitpose_model": "vitpose_h_wholebody_model.onnx", "yolo_model": "yolov10m.onnx", "onnx_device": "CUDAExecutionProvider"}},
 "32": {"class_type": "PoseAndFaceDetection", "inputs": {"model": ["31", 0], "images": ["30", 0], "width": W, "height": H}},
 "33": {"class_type": "DrawViTPose", "inputs": {"pose_data": ["32", 0], "width": W, "height": H, "retarget_padding": 0, "body_stick_width": 4, "hand_stick_width": 2, "draw_head": True}},
 # ---- SAM2 character mask ----
 "40": {"class_type": "DownloadAndLoadSAM2Model", "inputs": {"model": "sam2.1_hiera_base_plus.safetensors", "segmentor": "video", "device": "cuda", "precision": "fp16"}},
 "41": {"class_type": "Sam2Segmentation", "inputs": {"sam2_model": ["40", 0], "image": ["30", 0], "keep_model_loaded": False, "bboxes": ["32", 3]}},
 "42": {"class_type": "GrowMaskWithBlur", "inputs": {"mask": ["41", 0], "expand": 10, "incremental_expandrate": 0.0, "tapered_corners": True, "flip_input": False, "blur_radius": 0.0, "lerp_alpha": 1.0, "decay_factor": 1.0}},
 "43": {"class_type": "BlockifyMask", "inputs": {"masks": ["42", 0], "block_size": 32}},
 "44": {"class_type": "DrawMaskOnImage", "inputs": {"image": ["30", 0], "mask": ["43", 0], "color": "0, 0, 0"}},
 # ---- reference character ----
 "50": {"class_type": "LoadImage", "inputs": {"image": REF}},
 "51": {"class_type": "ImageScale", "inputs": {"image": ["50", 0], "upscale_method": "lanczos", "width": W, "height": H, "crop": "center"}},
 # ---- animate ----
 "60": {"class_type": "WanAnimateToVideo", "inputs": {"positive": ["21", 0], "negative": ["22", 0], "vae": ["23", 0], "width": W, "height": H, "length": LEN, "batch_size": 1, "continue_motion_max_frames": 5, "video_frame_offset": 0, "reference_image": ["51", 0], "face_video": ["32", 1], "pose_video": ["33", 0], "background_video": ["44", 0], "character_mask": ["43", 0]}},
 # ---- 4-step LCM ----
 "70": {"class_type": "CFGGuider", "inputs": {"model": ["12", 0], "positive": ["60", 0], "negative": ["60", 1], "cfg": 1.0}},
 "71": {"class_type": "BasicScheduler", "inputs": {"model": ["12", 0], "scheduler": "simple", "steps": 4, "denoise": 1.0}},
 "72": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "lcm"}},
 "73": {"class_type": "RandomNoise", "inputs": {"noise_seed": 42}},
 "74": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["73", 0], "guider": ["70", 0], "sampler": ["72", 0], "sigmas": ["71", 0], "latent_image": ["60", 2]}},
 "80": {"class_type": "VAEDecode", "inputs": {"samples": ["74", 0], "vae": ["23", 0]}},
 "81": {"class_type": "CreateVideo", "inputs": {"fps": FPS, "images": ["80", 0]}},
 "82": {"class_type": "SaveVideo", "inputs": {"filename_prefix": "WAN_ANIMATE_FULL", "format": "auto", "codec": "auto", "video": ["81", 0]}},
}

print("FULL Wan-Animate | DRIVE:", DRIVE, "REF:", REF, "|", W, "x", H, LEN, "frames (CPU pose, slow)")
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
