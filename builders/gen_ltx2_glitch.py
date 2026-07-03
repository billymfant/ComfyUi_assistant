"""Generate workflows/08_LTX2_i2v_glitch.json — LTX 2.3 i2v (+audio) 2-pass
crystal-clear pipeline with a bypassable glitchcore post group.

Mirrors the exact node graph validated live in tests/test_ltx2_glitch.py
(both 1-pass and 2-pass run on the server with audio). Layout is column-per-
stage, left to right. The GLITCH group (TimeSliceGrid + GlitchOverlay) is
mode 0 (active); set those two nodes to mode 4 (Ctrl+B) to bypass for a clean
crystal-clear clip with no glitch.
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from wf_lib import WF

OUT = os.path.join(os.path.dirname(__file__), "..", "workflows", "09_LTX2_i2v_glitch.json")
# ComfyUI sidebar reads from here too — install a copy on build:
INSTALL = r"F:\ComfyUI\ComfyUI-Easy-Install\ComfyUI\user\default\workflows\Video\09_LTX2_i2v_glitch.json"

CKPT = "ltx-2.3-22b-dev-fp8.safetensors"
ENC  = "gemma_3_12B_it_fp4_mixed.safetensors"
LORA = "ltx_2.3_22b_distilled_1.1_lora_dynamic_fro09_avg_rank_111_bf16.safetensors"
UPS  = "ltx-2.3-spatial-upscaler-x2-1.1.safetensors"
SIG_FULL = "1.0, 0.99375, 0.9875, 0.98125, 0.975, 0.909375, 0.725, 0.421875, 0.0"
SIG_REFINE = "0.85, 0.7250, 0.4219, 0.0"
POS = ("cinematic close-up of a confident man in a suit, shallow depth of field, "
       "natural skin texture, soft window light, subtle head movement, photographic, 4k")
NEG = "pc game, console game, video game, cartoon, childish, ugly, blurry"

w = WF()
X = lambda c: 80 + c * 360          # column -> x
def Y(r): return 120 + r * 200      # row -> y

# id, type, col, row, widgets, ins, outs, [title,color]
N = [
 (1, "CheckpointLoaderSimple", 0,0, [CKPT], [], [("MODEL","MODEL"),("CLIP","CLIP"),("VAE","VAE")]),
 (2, "LoraLoaderModelOnly", 1,0, [LORA,0.5], [("model","MODEL")], [("MODEL","MODEL")]),
 (3, "LTXAVTextEncoderLoader", 0,1, [ENC,CKPT,"default"], [], [("CLIP","CLIP")]),
 (4, "LTXVAudioVAELoader", 0,2, [CKPT], [], [("Audio VAE","VAE")]),
 (5, "CLIPTextEncode", 1,1, [POS], [("clip","CLIP")], [("CONDITIONING","CONDITIONING")], "Positive","#232"),
 (6, "CLIPTextEncode", 1,2, [NEG], [("clip","CLIP")], [("CONDITIONING","CONDITIONING")], "Negative","#322"),
 (7, "LTXVConditioning", 2,1, [25.0], [("positive","CONDITIONING"),("negative","CONDITIONING")],
     [("positive","CONDITIONING"),("negative","CONDITIONING")]),
 (8, "LoadImage", 0,3, ["BEST_MAN.jpg","image"], [], [("IMAGE","IMAGE"),("MASK","MASK")]),
 (9, "ImageScale", 1,3, ["lanczos",768,512,"center"], [("image","IMAGE")], [("IMAGE","IMAGE")]),
 (10,"LTXVPreprocess", 2,3, [18], [("image","IMAGE")], [("output_image","IMAGE")]),
 (11,"EmptyLTXVLatentVideo", 2,4, [768,512,49,1], [], [("LATENT","LATENT")]),
 (12,"LTXVImgToVideoInplace", 3,3, [0.7,False],
     [("vae","VAE"),("image","IMAGE"),("latent","LATENT")], [("latent","LATENT")]),
 (13,"LTXVEmptyLatentAudio", 3,4, [49,25,1], [("audio_vae","VAE")], [("Latent","LATENT")]),
 (14,"LTXVConcatAVLatent", 4,3, [], [("video_latent","LATENT"),("audio_latent","LATENT")], [("latent","LATENT")]),
 (15,"RandomNoise", 4,0, [42,"fixed"], [], [("NOISE","NOISE")]),
 (16,"CFGGuider", 3,1, [1.0], [("model","MODEL"),("positive","CONDITIONING"),("negative","CONDITIONING")],
     [("GUIDER","GUIDER")]),
 (17,"KSamplerSelect", 4,1, ["euler"], [], [("SAMPLER","SAMPLER")]),
 (18,"ManualSigmas", 4,2, [SIG_FULL], [], [("SIGMAS","SIGMAS")]),
 (19,"SamplerCustomAdvanced", 5,2, [],
     [("noise","NOISE"),("guider","GUIDER"),("sampler","SAMPLER"),("sigmas","SIGMAS"),("latent_image","LATENT")],
     [("output","LATENT"),("denoised_output","LATENT")]),
 (20,"LTXVSeparateAVLatent", 6,2, [], [("av_latent","LATENT")], [("video_latent","LATENT"),("audio_latent","LATENT")]),
 # ---- refine pass (2-pass quality) ----
 (21,"LatentUpscaleModelLoader", 6,0, [UPS], [], [("LATENT_UPSCALE_MODEL","LATENT_UPSCALE_MODEL")]),
 (22,"LTXVLatentUpsampler", 7,1, [], [("samples","LATENT"),("upscale_model","LATENT_UPSCALE_MODEL"),("vae","VAE")],
     [("LATENT","LATENT")]),
 (23,"LTXVImgToVideoInplace", 7,2, [1.0,False],
     [("vae","VAE"),("image","IMAGE"),("latent","LATENT")], [("latent","LATENT")]),
 (24,"LTXVCropGuides", 7,3, [], [("positive","CONDITIONING"),("negative","CONDITIONING"),("latent","LATENT")],
     [("positive","CONDITIONING"),("negative","CONDITIONING"),("latent","LATENT")]),
 (25,"LTXVConcatAVLatent", 8,2, [], [("video_latent","LATENT"),("audio_latent","LATENT")], [("latent","LATENT")]),
 (26,"RandomNoise", 8,0, [42,"fixed"], [], [("NOISE","NOISE")]),
 (27,"CFGGuider", 8,1, [1.0], [("model","MODEL"),("positive","CONDITIONING"),("negative","CONDITIONING")],
     [("GUIDER","GUIDER")]),
 (28,"ManualSigmas", 8,3, [SIG_REFINE], [], [("SIGMAS","SIGMAS")]),
 (29,"SamplerCustomAdvanced", 9,2, [],
     [("noise","NOISE"),("guider","GUIDER"),("sampler","SAMPLER"),("sigmas","SIGMAS"),("latent_image","LATENT")],
     [("output","LATENT"),("denoised_output","LATENT")]),
 (30,"LTXVSeparateAVLatent", 10,2, [], [("av_latent","LATENT")],
     [("video_latent","LATENT"),("audio_latent","LATENT")]),
 # ---- decode ----
 (31,"VAEDecodeTiled", 11,2, [768,64,64,8], [("samples","LATENT"),("vae","VAE")], [("IMAGE","IMAGE")]),
 (32,"LTXVAudioVAEDecode", 11,4, [], [("samples","LATENT"),("audio_vae","VAE")], [("Audio","AUDIO")]),
 # ---- glitch group (bypassable) ----
 (33,"TimeSliceGrid", 12,1, ["grid (cols x rows)",10,10,96,96,5,"wave",0.35,"mirror",0.5,1.0,7],
     [("images","IMAGE")], [("IMAGE","IMAGE")], "Time-Slice","#2a2"),
 (34,"GlitchOverlay", 13,1, [18,0.5,"neon",True,10,0.9,0.5,1.0,3],
     [("images","IMAGE")], [("IMAGE","IMAGE")], "Glitch Overlay","#2a2"),
 # ---- mux + save ----
 (35,"CreateVideo", 14,2, [25.0], [("images","IMAGE"),("audio","AUDIO")], [("VIDEO","VIDEO")]),
 (36,"SaveVideo", 15,2, ["video/09_LTX2_glitch","auto","auto"], [("video","VIDEO")], []),
]

for item in N:
    nid, typ, col, row, wid, ins, outs = item[:7]
    title = item[7] if len(item) > 7 else None
    color = item[8] if len(item) > 8 else None
    w.add(nid, typ, (X(col), Y(row)), (300, 130), wid, ins, outs, title=title, color=color)

# connections: (src, srcslot, dst, dstslot, type)
C = [
 (1,0, 2,0, "MODEL"),
 (3,0, 5,0, "CLIP"), (3,0, 6,0, "CLIP"),
 (5,0, 7,0, "CONDITIONING"), (6,0, 7,1, "CONDITIONING"),
 (8,0, 9,0, "IMAGE"), (9,0, 10,0, "IMAGE"),
 (1,2, 12,0, "VAE"), (10,0, 12,1, "IMAGE"), (11,0, 12,2, "LATENT"),
 (4,0, 13,0, "VAE"),
 (12,0, 14,0, "LATENT"), (13,0, 14,1, "LATENT"),
 (2,0, 16,0, "MODEL"), (7,0, 16,1, "CONDITIONING"), (7,1, 16,2, "CONDITIONING"),
 (15,0, 19,0, "NOISE"), (16,0, 19,1, "GUIDER"), (17,0, 19,2, "SAMPLER"), (18,0, 19,3, "SIGMAS"), (14,0, 19,4, "LATENT"),
 (19,0, 20,0, "LATENT"),
 # refine
 (20,0, 22,0, "LATENT"), (21,0, 22,1, "LATENT_UPSCALE_MODEL"), (1,2, 22,2, "VAE"),
 (1,2, 23,0, "VAE"), (10,0, 23,1, "IMAGE"), (22,0, 23,2, "LATENT"),
 (7,0, 24,0, "CONDITIONING"), (7,1, 24,1, "CONDITIONING"), (12,0, 24,2, "LATENT"),
 (23,0, 25,0, "LATENT"), (20,1, 25,1, "LATENT"),
 (2,0, 27,0, "MODEL"), (24,0, 27,1, "CONDITIONING"), (24,1, 27,2, "CONDITIONING"),
 (26,0, 29,0, "NOISE"), (27,0, 29,1, "GUIDER"), (17,0, 29,2, "SAMPLER"), (28,0, 29,3, "SIGMAS"), (25,0, 29,4, "LATENT"),
 (29,0, 30,0, "LATENT"),
 # decode
 (30,0, 31,0, "LATENT"), (1,2, 31,1, "VAE"),
 (30,1, 32,0, "LATENT"), (4,0, 32,1, "VAE"),
 # glitch
 (31,0, 33,0, "IMAGE"), (33,0, 34,0, "IMAGE"),
 # mux
 (34,0, 35,0, "IMAGE"), (32,0, 35,1, "AUDIO"), (35,0, 36,0, "VIDEO"),
]
for c in C:
    w.connect(*c)

w.group(1, "BASE  (LTX 2.3 i2v + audio, 8-step distilled)", [X(0)-20, Y(0)-60, 360*6, 1000])
w.group(2, "REFINE  (2x spatial upscaler -> crystal clear)", [X(6)+150, Y(0)-60, 360*5, 900])
w.group(3, "GLITCH  (Ctrl+B these two to bypass)", [X(12)-20, Y(1)-60, 360*2, 360], "#234d20")
w.group(4, "DECODE + SAVE", [X(11)-20, Y(2)-60, 340, 700])

res = w.finalize(os.path.abspath(OUT), "ltx2_glitch")
print("wrote", os.path.abspath(OUT))
print(res)
# install into ComfyUI's sidebar workflows dir
import shutil
shutil.copyfile(os.path.abspath(OUT), INSTALL)
print("installed ->", INSTALL)
