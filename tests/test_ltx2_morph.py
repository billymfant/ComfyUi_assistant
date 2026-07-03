"""Live test: LTX 2.3 First-Last-Frame MORPH (image A -> image B) + audio,
with the glitch firing around the transition midpoint (envelope center 0.5).
Single-pass. POST /prompt, poll, print output."""
import json, sys, time, urllib.request, os
os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
HOST = "http://127.0.0.1:8188"
CKPT="ltx-2.3-22b-dev-fp8.safetensors"; ENC="gemma_3_12B_it_fp4_mixed.safetensors"
LORA="ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors"
IMG_A=sys.argv[1] if len(sys.argv)>1 else "Cat.jpeg"
IMG_B=sys.argv[2] if len(sys.argv)>2 else "Dog.jpeg"
W,H,LEN,FPS=768,512,49,25
SIG="1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"
POS="a smooth cinematic morph transformation, fluid transition, photographic, soft light, 4k"
NEG="ugly, blurry, distorted, jitter, flicker"
SEED=42
g={}
def add(i,ct,ins): g[i]={"class_type":ct,"inputs":ins}; return i
add("ckpt","CheckpointLoaderSimple",{"ckpt_name":CKPT})
add("lora","LoraLoaderModelOnly",{"model":["ckpt",0],"lora_name":LORA,"strength_model":0.5})
add("clip","LTXAVTextEncoderLoader",{"text_encoder":ENC,"ckpt_name":CKPT,"device":"default"})
add("avae","LTXVAudioVAELoader",{"ckpt_name":CKPT})
add("pos","CLIPTextEncode",{"clip":["clip",0],"text":POS})
add("neg","CLIPTextEncode",{"clip":["clip",0],"text":NEG})
add("cond","LTXVConditioning",{"positive":["pos",0],"negative":["neg",0],"frame_rate":float(FPS)})
# two frames
add("imgA","LoadImage",{"image":IMG_A}); add("imgB","LoadImage",{"image":IMG_B})
add("scA","ImageScale",{"image":["imgA",0],"upscale_method":"lanczos","width":W,"height":H,"crop":"center"})
add("scB","ImageScale",{"image":["imgB",0],"upscale_method":"lanczos","width":W,"height":H,"crop":"center"})
add("preA","LTXVPreprocess",{"image":["scA",0],"img_compression":25})
add("preB","LTXVPreprocess",{"image":["scB",0],"img_compression":25})
add("elat","EmptyLTXVLatentVideo",{"width":W,"height":H,"length":LEN,"batch_size":1})
# inject first (A @0) then last (B @-1) via AddGuide
add("gA","LTXVAddGuide",{"positive":["cond",0],"negative":["cond",1],"vae":["ckpt",2],
    "latent":["elat",0],"image":["preA",0],"frame_idx":0,"strength":0.7})
add("gB","LTXVAddGuide",{"positive":["gA",0],"negative":["gA",1],"vae":["ckpt",2],
    "latent":["gA",2],"image":["preB",0],"frame_idx":-1,"strength":0.7})
add("alat","LTXVEmptyLatentAudio",{"frames_number":LEN,"frame_rate":FPS,"batch_size":1,"audio_vae":["avae",0]})
add("cat","LTXVConcatAVLatent",{"video_latent":["gB",2],"audio_latent":["alat",0]})
add("noise","RandomNoise",{"noise_seed":SEED})
add("guide","CFGGuider",{"model":["lora",0],"positive":["gB",0],"negative":["gB",1],"cfg":1.0})
add("samp","KSamplerSelect",{"sampler_name":"euler"})
add("sig","ManualSigmas",{"sigmas":SIG})
add("ksa","SamplerCustomAdvanced",{"noise":["noise",0],"guider":["guide",0],"sampler":["samp",0],
    "sigmas":["sig",0],"latent_image":["cat",0]})
add("sep","LTXVSeparateAVLatent",{"av_latent":["ksa",0]})
add("dec","VAEDecodeTiled",{"samples":["sep",0],"vae":["ckpt",2],"tile_size":768,"overlap":64,
    "temporal_size":64,"temporal_overlap":8})
add("adec","LTXVAudioVAEDecode",{"samples":["sep",1],"audio_vae":["avae",0]})
# glitch peaks at the morph midpoint (envelope center 0.5, narrow spread)
add("ts","TimeSliceGrid",{"images":["dec",0],"sizing":"grid (cols x rows)","cols":12,"rows":12,
    "tile_w":96,"tile_h":96,"time_offset_range":6,"stagger_pattern":"wave","flow_speed":0.5,
    "boundary":"mirror","intensity_center":0.5,"intensity_spread":0.4,"seed":7})
add("ov","GlitchOverlay",{"images":["ts",0],"element_count":20,"flicker_rate":0.55,"color_palette":"neon",
    "draw_text":True,"max_drift":12,"opacity":0.9,"intensity_center":0.5,"intensity_spread":0.4,"seed":3})
add("vid","CreateVideo",{"images":["ov",0],"audio":["adec",0],"fps":float(FPS)})
add("save","SaveVideo",{"video":["vid",0],"filename_prefix":"video/10_LTX2_morph_glitch","format":"auto","codec":"auto"})

print(f"MORPH {IMG_A} -> {IMG_B}  {W}x{H}x{LEN}f  nodes={len(g)}")
try:
    r=urllib.request.urlopen(urllib.request.Request(HOST+"/prompt",json.dumps({"prompt":g}).encode(),
        {"Content-Type":"application/json"})); pid=json.load(r)["prompt_id"]
except urllib.error.HTTPError as e:
    print("VALIDATION ERROR:"); print(json.dumps(json.loads(e.read()),indent=1)[:1800]); sys.exit(1)
print("prompt_id:",pid); t0=time.time()
while True:
    time.sleep(3); h=json.load(urllib.request.urlopen(HOST+"/history/"+pid))
    if pid in h:
        st=h[pid]["status"]
        if st.get("completed") or st.get("status_str")=="error":
            print(f"[{time.time()-t0:.0f}s] {st.get('status_str')}")
            for nid,o in h[pid].get("outputs",{}).items():
                for f in o.get("video",[]): print("  OUT:",f.get("subfolder"),f.get("filename"))
            if st.get("status_str")=="error":
                for m in h[pid]["status"].get("messages",[]):
                    if m[0]=="execution_error": print("  ERR:",json.dumps(m[1])[:800])
            break
    if time.time()-t0>900: print("timeout"); break
