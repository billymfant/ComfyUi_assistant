"""End-to-end live test: LTX 2.3 i2v (+audio) -> glitch_pack -> video.
Single-pass (fast smoke) by default; pass --twopass for the full upscaler refine.
POSTs API-format prompt to /prompt, polls /history, prints output path."""
import json, sys, time, urllib.request, os
os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
HOST = "http://127.0.0.1:8188"

CKPT = "ltx-2.3-22b-dev-fp8.safetensors"
ENC  = "gemma_3_12B_it_fp4_mixed.safetensors"
LORA = "ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors"
UPS  = "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"
IMG  = "BEST_MAN.jpg"

W, H, LEN, FPS = 768, 512, 49, 25            # 49 = 8*6+1 -> ~2s
SIG_FULL = "1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"
SIG_REFINE = "0.85, 0.7250, 0.4219, 0.0"
POS = ("cinematic close-up of a confident man in a suit, shallow depth of field, "
       "natural skin texture, soft window light, subtle head movement, photographic, 4k")
NEG = "pc game, console game, video game, cartoon, childish, ugly, blurry"
SEED = 42
twopass = "--twopass" in sys.argv

def post(p):
    data = json.dumps({"prompt": p}).encode()
    r = urllib.request.urlopen(urllib.request.Request(HOST+"/prompt", data,
        {"Content-Type": "application/json"}))
    return json.load(r)["prompt_id"]

g = {}
def add(i, ct, ins):
    g[i] = {"class_type": ct, "inputs": ins}; return i

# --- loaders ---
add("ckpt", "CheckpointLoaderSimple", {"ckpt_name": CKPT})
add("lora", "LoraLoaderModelOnly", {"model": ["ckpt", 0], "lora_name": LORA, "strength_model": 0.5})
add("clip", "LTXAVTextEncoderLoader", {"text_encoder": ENC, "ckpt_name": CKPT, "device": "default"})
add("avae", "LTXVAudioVAELoader", {"ckpt_name": CKPT})
# --- conditioning ---
add("pos", "CLIPTextEncode", {"clip": ["clip", 0], "text": POS})
add("neg", "CLIPTextEncode", {"clip": ["clip", 0], "text": NEG})
add("cond", "LTXVConditioning", {"positive": ["pos", 0], "negative": ["neg", 0], "frame_rate": float(FPS)})
# --- image prep ---
add("img", "LoadImage", {"image": IMG})
add("scale", "ImageScale", {"image": ["img", 0], "upscale_method": "lanczos",
    "width": W, "height": H, "crop": "center"})
add("pre", "LTXVPreprocess", {"image": ["scale", 0], "img_compression": 18})
# --- base latents (video + audio) ---
add("elat", "EmptyLTXVLatentVideo", {"width": W, "height": H, "length": LEN, "batch_size": 1})
add("i2v", "LTXVImgToVideoInplace", {"vae": ["ckpt", 2], "image": ["pre", 0],
    "latent": ["elat", 0], "strength": 0.7, "bypass": False})
add("alat", "LTXVEmptyLatentAudio", {"frames_number": LEN, "frame_rate": FPS,
    "batch_size": 1, "audio_vae": ["avae", 0]})
add("cat", "LTXVConcatAVLatent", {"video_latent": ["i2v", 0], "audio_latent": ["alat", 0]})
# --- base sampling (8-step distilled) ---
add("noise", "RandomNoise", {"noise_seed": SEED})
add("guide", "CFGGuider", {"model": ["lora", 0], "positive": ["cond", 0],
    "negative": ["cond", 1], "cfg": 1.0})
add("samp", "KSamplerSelect", {"sampler_name": "euler"})
add("sig", "ManualSigmas", {"sigmas": SIG_FULL})
add("ksa", "SamplerCustomAdvanced", {"noise": ["noise", 0], "guider": ["guide", 0],
    "sampler": ["samp", 0], "sigmas": ["sig", 0], "latent_image": ["cat", 0]})
add("sep", "LTXVSeparateAVLatent", {"av_latent": ["ksa", 0]})

video_latent, audio_latent = ["sep", 0], ["sep", 1]

if twopass:
    add("upsl", "LatentUpscaleModelLoader", {"model_name": UPS})
    add("ups", "LTXVLatentUpsampler", {"samples": ["sep", 0],
        "upscale_model": ["upsl", 0], "vae": ["ckpt", 2]})
    add("i2v2", "LTXVImgToVideoInplace", {"vae": ["ckpt", 2], "image": ["pre", 0],
        "latent": ["ups", 0], "strength": 1.0, "bypass": False})
    add("crop", "LTXVCropGuides", {"positive": ["cond", 0], "negative": ["cond", 1],
        "latent": ["i2v", 0]})
    add("cat2", "LTXVConcatAVLatent", {"video_latent": ["i2v2", 0], "audio_latent": audio_latent})
    add("noise2", "RandomNoise", {"noise_seed": SEED})
    add("guide2", "CFGGuider", {"model": ["lora", 0], "positive": ["crop", 0],
        "negative": ["crop", 1], "cfg": 1.0})
    add("sig2", "ManualSigmas", {"sigmas": SIG_REFINE})
    add("ksa2", "SamplerCustomAdvanced", {"noise": ["noise2", 0], "guider": ["guide2", 0],
        "sampler": ["samp", 0], "sigmas": ["sig2", 0], "latent_image": ["cat2", 0]})
    add("sep2", "LTXVSeparateAVLatent", {"av_latent": ["ksa2", 0]})
    video_latent, audio_latent = ["sep2", 0], ["sep2", 1]

# --- decode ---
add("dec", "VAEDecodeTiled", {"samples": video_latent, "vae": ["ckpt", 2],
    "tile_size": 768, "overlap": 64, "temporal_size": 64, "temporal_overlap": 8})
add("adec", "LTXVAudioVAEDecode", {"samples": audio_latent, "audio_vae": ["avae", 0]})
# --- glitch post ---
add("ts", "TimeSliceGrid", {"images": ["dec", 0], "grid_size": 10, "time_offset_range": 5,
    "stagger_pattern": "random", "boundary": "mirror", "seed": 7})
add("ov", "GlitchOverlay", {"images": ["ts", 0], "element_count": 18, "flicker_rate": 0.5,
    "color_palette": "neon", "draw_text": True, "max_drift": 10, "opacity": 0.9, "seed": 3})
# --- mux + save ---
add("vid", "CreateVideo", {"images": ["ov", 0], "audio": ["adec", 0], "fps": float(FPS)})
add("save", "SaveVideo", {"video": ["vid", 0],
    "filename_prefix": "video/08_LTX2_glitch" + ("_2pass" if twopass else "_1pass"),
    "format": "auto", "codec": "auto"})

print(f"mode={'2-pass' if twopass else '1-pass'}  {W}x{H}x{LEN}f@{FPS}  nodes={len(g)}")
pid = post(g)
print("prompt_id:", pid)
t0 = time.time()
while True:
    time.sleep(3)
    h = json.load(urllib.request.urlopen(HOST+"/history/"+pid))
    if pid in h:
        st = h[pid]["status"]
        print(f"[{time.time()-t0:.0f}s] {st.get('status_str')}")
        if st.get("completed") or st.get("status_str") == "error":
            outs = h[pid].get("outputs", {})
            for nid, o in outs.items():
                for key in ("images", "video", "gifs"):
                    for f in o.get(key, []):
                        print("  OUT:", f.get("subfolder"), f.get("filename"))
            if st.get("status_str") == "error":
                for m in h[pid]["status"].get("messages", []):
                    if m[0] in ("execution_error","execution_interrupted"):
                        print("  ERR:", json.dumps(m[1])[:800])
            break
    if time.time()-t0 > 900:
        print("timeout"); break
