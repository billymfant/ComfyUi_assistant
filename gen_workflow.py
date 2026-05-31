import json

nodes=[]; links=[]; conns=[]; lid=[0]
NDEF={}  # id -> node dict

def add(nid,typ,pos,size,widgets,ins,outs,mode=0,title=None,color=None):
    nd={"id":nid,"type":typ,"pos":pos,"size":size,"flags":{},"order":0,"mode":mode,
        "inputs":[{"name":n,"type":t,"link":None} for n,t in ins],
        "outputs":[{"name":n,"type":t,"links":[],"slot_index":i} for i,(n,t) in enumerate(outs)],
        "properties":{"Node name for S&R":typ},
        "widgets_values":widgets}
    if title: nd["title"]=title
    if color: nd["color"]=color; nd["bgcolor"]=color
    nodes.append(nd); NDEF[nid]=nd
    return nd

def connect(src,sslot,dst,dslot,typ):
    conns.append((src,sslot,dst,dslot,typ))

# ---------- nodes ----------
# 1 LOADERS
add(1,"UNETLoader",[-1180,-380],[300,82],["flux-2-klein-4b-fp8.safetensors","default"],
    [],[("MODEL","MODEL")],title="Diffusion Model (4B=fast / 9B=quality)")
add(2,"CLIPLoader",[-1180,-240],[300,106],["qwen_3_4b.safetensors","flux2","default"],
    [],[("CLIP","CLIP")],title="Text Encoder (Qwen3)")
add(3,"VAELoader",[-1180,-70],[300,58],["flux2-vae.safetensors"],
    [],[("VAE","VAE")],title="VAE")

# 2 PROMPT
add(4,"CLIPTextEncode",[-820,-380],[380,200],
    ["a cinematic photo of a red apple on a rustic wooden table, soft window light, shallow depth of field, ultra-detailed, 35mm"],
    [("clip","CLIP")],[("CONDITIONING","CONDITIONING")],title="Positive Prompt",color="#232")
add(5,"FluxGuidance",[-820,-140],[380,58],[4],
    [("conditioning","CONDITIONING")],[("CONDITIONING","CONDITIONING")],title="Guidance (3-5)")

# 3 REFERENCE GROUPS (bypassed by default) -- mode 4 = bypass
def refgroup(base,y,img,t):
    li,sc,ve,rl=base,base+1,base+2,base+3
    add(li,"LoadImage",[-820,y],[300,314],[img,"image"],
        [],[("IMAGE","IMAGE"),("MASK","MASK")],mode=4,title=f"Ref {t} image",color="#322")
    add(sc,"ImageScaleToTotalPixels",[-490,y],[280,106],["lanczos",1.0,16],
        [("image","IMAGE")],[("IMAGE","IMAGE")],mode=4)
    add(ve,"VAEEncode",[-490,y+150],[210,46],[],
        [("pixels","IMAGE"),("vae","VAE")],[("LATENT","LATENT")],mode=4)
    add(rl,"ReferenceLatent",[-490,y+250],[210,66],[],
        [("conditioning","CONDITIONING"),("latent","LATENT")],[("CONDITIONING","CONDITIONING")],mode=4)
    connect(li,0,sc,0,"IMAGE"); connect(sc,0,ve,0,"IMAGE")
    connect(3,0,ve,1,"VAE"); connect(ve,0,rl,1,"LATENT")
    return rl
rl1=refgroup(30,120,"Cat.jpeg","1")
rl2=refgroup(40,560,"BEST_MAN.jpg","2")
rl3=refgroup(50,1000,"Architecture.png","3")

# chain conditioning: 5 -> rl1 -> rl2 -> rl3 -> BasicGuider
connect(5,0,30+3,0,"CONDITIONING")
connect(30+3,0,40+3,0,"CONDITIONING")
connect(40+3,0,50+3,0,"CONDITIONING")

# 4 SAMPLER
add(6,"EmptyFlux2LatentImage",[20,-380],[280,106],[1024,1024,1],
    [],[("LATENT","LATENT")],title="Canvas size")
add(10,"RandomNoise",[20,-240],[280,82],[12345,"randomize"],
    [],[("NOISE","NOISE")],title="Seed")
add(8,"KSamplerSelect",[20,-120],[280,58],["euler"],
    [],[("SAMPLER","SAMPLER")])
add(9,"Flux2Scheduler",[20,-30],[280,82],[20,1024,1024],
    [],[("SIGMAS","SIGMAS")],title="Scheduler (steps)")
add(7,"BasicGuider",[20,110],[280,46],[],
    [("model","MODEL"),("conditioning","CONDITIONING")],[("GUIDER","GUIDER")])
add(11,"SamplerCustomAdvanced",[360,-380],[300,150],[],
    [("noise","NOISE"),("guider","GUIDER"),("sampler","SAMPLER"),("sigmas","SIGMAS"),("latent_image","LATENT")],
    [("output","LATENT"),("denoised_output","LATENT")],title="Sampler")
add(12,"VAEDecode",[360,-180],[210,46],[],
    [("samples","LATENT"),("vae","VAE")],[("IMAGE","IMAGE")])
add(13,"SaveImage",[700,-380],[480,500],["FLUX2"],
    [("images","IMAGE")],[],title="Output (base)")

# 5 UPSCALE (optional, bypassed by default)
add(60,"UpscaleModelLoader",[700,180],[300,58],["4x-UltraSharp.pth"],
    [],[("UPSCALE_MODEL","UPSCALE_MODEL")],mode=4,title="Upscale model")
add(61,"ImageUpscaleWithModel",[700,290],[300,46],[],
    [("upscale_model","UPSCALE_MODEL"),("image","IMAGE")],[("IMAGE","IMAGE")],mode=4)
add(62,"ImageScaleToMaxDimension",[700,380],[300,82],["lanczos",3840],
    [("image","IMAGE")],[("IMAGE","IMAGE")],mode=4,title="Cap longest side -> 4K (3840)")
add(63,"SaveImage",[700,500],[480,400],["FLUX2_upscaled"],
    [("images","IMAGE")],[],mode=4,title="Upscaled output")
connect(60,0,61,0,"UPSCALE_MODEL")
connect(12,0,61,1,"IMAGE")
connect(61,0,62,0,"IMAGE")
connect(62,0,63,0,"IMAGE")

# wiring
connect(1,0,7,0,"MODEL")
connect(2,0,4,0,"CLIP")
connect(4,0,5,0,"CONDITIONING")
connect(50+3,0,7,1,"CONDITIONING")
connect(6,0,11,4,"LATENT")
connect(10,0,11,0,"NOISE")
connect(7,0,11,1,"GUIDER")
connect(8,0,11,2,"SAMPLER")
connect(9,0,11,3,"SIGMAS")
connect(11,0,12,0,"LATENT")
connect(3,0,12,1,"VAE")
connect(12,0,13,0,"IMAGE")

# Note node
note=("HOW TO USE  (Flux 2 Klein - 100% local & free)\n\n"
 "MODE 1 - TEXT TO IMAGE:\n  Leave all 3 Reference groups bypassed (they are red/disabled by default).\n  Type your prompt, hit Run.\n\n"
 "MODE 2 - IMAGE TO IMAGE:\n  Enable Reference 1 (select its 4 nodes, press Ctrl+B to un-bypass).\n  Load your image in 'Ref 1 image'. Prompt = what you want changed.\n\n"
 "MODE 3 - REFERENCE -> IMAGE:\n  Enable Reference 1, 2 (and 3) the same way, load a different image in each.\n  The model blends/uses all of them. Up to 3 wired here (Flux 2 supports more).\n\n"
 "UPSCALE TO 4K (group 5, optional):\n  Select the 4 green nodes, press Ctrl+B to enable. 4x model then caps the\n  longest side at 3840 = up to 4K, saved as FLUX2_upscaled. Off by default.\n\n"
 "TIPS:\n  - Guidance 3-5. Steps 20 (try 28-32 for more detail).\n  - For MAX quality switch Diffusion Model to flux-2-klein-base-9b-fp8\n    AND Text Encoder to qwen_3_8b_fp8mixed (slower, heavier).\n  - Change 'Canvas size' AND the width/height in 'Scheduler' to match (keep them equal).\n  - Seed widget: set to 'fixed' to reproduce, 'randomize' to explore.")
add(99,"Note",[-1180,120],[300,360],[note],[],[],color="#432")

# ---------- assign links ----------
for src,sslot,dst,dslot,typ in conns:
    lid[0]+=1; L=lid[0]
    NDEF[src]["outputs"][sslot]["links"].append(L)
    for inp in NDEF[dst]["inputs"]:
        if inp["name"]== [i["name"] for i in NDEF[dst]["inputs"]][dslot]:
            pass
    NDEF[dst]["inputs"][dslot]["link"]=L
    links.append([L,src,sslot,dst,dslot,typ])

# order field
for i,nd in enumerate(nodes): nd["order"]=i

groups=[
 {"id":1,"title":"1. LOADERS","bounding":[-1200,-440,340,400],"color":"#3f789e","font_size":24,"flags":{}},
 {"id":2,"title":"2. PROMPT","bounding":[-840,-440,400,320],"color":"#3f789e","font_size":24,"flags":{}},
 {"id":3,"title":"3. REFERENCE IMAGES  (bypassed = OFF. Ctrl+B to enable)","bounding":[-840,80,650,1240],"color":"#a1309b","font_size":24,"flags":{}},
 {"id":4,"title":"4. SAMPLER","bounding":[0,-440,680,640],"color":"#3f789e","font_size":24,"flags":{}},
 {"id":5,"title":"5. UPSCALE TO 4K  (optional - Ctrl+B to enable)","bounding":[680,140,520,800],"color":"#3f9b46","font_size":24,"flags":{}},
]

wf={"id":"flux2-allinone","revision":0,"last_node_id":99,"last_link_id":lid[0],
    "nodes":nodes,"links":links,"groups":groups,"config":{},
    "extra":{"ds":{"scale":0.62,"offset":[1300,560]}},"version":0.4}

open("FLUX2_AllInOne_T2I_I2I_Reference.json","w",encoding="utf-8").write(json.dumps(wf,indent=2))
print("written. nodes:",len(nodes),"links:",len(links))
