import json,urllib.request,time,uuid
BASE="http://127.0.0.1:8188"
def n(c,i): return {"class_type":c,"inputs":i}
imgs=["ebd14b4b-f194-482e-95e7-09a809c671bf.png",
      "c2b6a3e0-a1a9-442d-a6e7-ea9de7c7fde9.png",
      "df6419bd-8289-4849-aada-176878e11d01.png"]
prompt=("A striking high-fashion editorial photograph of a single model, fusing the aesthetics of the "
        "reference images: translucent iridescent holographic garments, digital glitch fragmentation "
        "dispersing the body into streaming pixels, clear plastic and wire elements wrapping the form, "
        "sculptural dynamic pose, minimalist soft-grey studio backdrop, cinematic rim lighting, "
        "ultra detailed, photorealistic, shot on 35mm")
W,H=896,1152
p={
 "1":n("UNETLoader",{"unet_name":"flux-2-klein-4b-fp8.safetensors","weight_dtype":"default"}),
 "2":n("CLIPLoader",{"clip_name":"qwen_3_4b.safetensors","type":"flux2","device":"default"}),
 "3":n("VAELoader",{"vae_name":"flux2-vae.safetensors"}),
 "4":n("CLIPTextEncode",{"text":prompt,"clip":["2",0]}),
 "5":n("FluxGuidance",{"conditioning":["4",0],"guidance":4.0}),
 "6":n("EmptyFlux2LatentImage",{"width":W,"height":H,"batch_size":1}),
 "8":n("KSamplerSelect",{"sampler_name":"euler"}),
 "9":n("Flux2Scheduler",{"steps":28,"width":W,"height":H}),
 "10":n("RandomNoise",{"noise_seed":88421}),
}
# build 3 reference chains: LoadImage -> crop 6% UI chrome -> scale 1MP -> VAEEncode -> ReferenceLatent
cond="5"
nid=30
for img in imgs:
    li,cr,sc,ve,rl=nid,nid+1,nid+2,nid+3,nid+4
    p[str(li)]=n("LoadImage",{"image":img})
    # crop using ImageCrop? use simple: ImageScaleToTotalPixels then nothing; instead crop via 'ImageCrop' if exists -> use LayerUtility? keep simple: scale only
    p[str(sc)]=n("ImageScaleToTotalPixels",{"image":[str(li),0],"upscale_method":"lanczos","megapixels":1.0,"resolution_steps":16})
    p[str(ve)]=n("VAEEncode",{"pixels":[str(sc),0],"vae":["3",0]})
    p[str(rl)]=n("ReferenceLatent",{"conditioning":[cond,0],"latent":[str(ve),0]})
    cond=str(rl); nid+=10
p["7"]=n("BasicGuider",{"model":["1",0],"conditioning":[cond,0]})
p["11"]=n("SamplerCustomAdvanced",{"noise":["10",0],"guider":["7",0],"sampler":["8",0],"sigmas":["9",0],"latent_image":["6",0]})
p["12"]=n("VAEDecode",{"samples":["11",0],"vae":["3",0]})
p["13"]=n("SaveImage",{"images":["12",0],"filename_prefix":"FLUX2_FUSION3"})
data=json.dumps({"prompt":p,"client_id":str(uuid.uuid4())}).encode()
req=urllib.request.Request(BASE+"/prompt",data=data,headers={"Content-Type":"application/json"})
try: r=json.loads(urllib.request.urlopen(req).read())
except urllib.error.HTTPError as e: print("ERR",e.code,e.read().decode()); raise SystemExit
pid=r["prompt_id"]; print("queued",pid); t0=time.time()
while time.time()-t0<300:
    h=json.loads(urllib.request.urlopen(BASE+"/history/"+pid).read())
    if pid in h:
        print("status:",h[pid]["status"].get("status_str"))
        for _,o in h[pid].get("outputs",{}).items():
            for im in o.get("images",[]): print("IMAGE:",im["filename"])
        print("ELAPSED %.1fs"%(time.time()-t0)); break
    time.sleep(2)
else: print("TIMEOUT")
