import json,urllib.request,time,uuid
BASE="http://127.0.0.1:8188"
def n(c,i): return {"class_type":c,"inputs":i}
prompt={
 "1":n("UNETLoader",{"unet_name":"flux-2-klein-4b-fp8.safetensors","weight_dtype":"default"}),
 "2":n("CLIPLoader",{"clip_name":"qwen_3_4b.safetensors","type":"flux2","device":"default"}),
 "3":n("VAELoader",{"vae_name":"flux2-vae.safetensors"}),
 "4":n("CLIPTextEncode",{"text":"a product photo combining the two reference subjects on a marble pedestal, studio lighting","clip":["2",0]}),
 "5":n("FluxGuidance",{"conditioning":["4",0],"guidance":4.0}),
 "30":n("LoadImage",{"image":"Cat.jpeg"}),
 "31":n("ImageScaleToTotalPixels",{"image":["30",0],"upscale_method":"lanczos","megapixels":1.0,"resolution_steps":16}),
 "32":n("VAEEncode",{"pixels":["31",0],"vae":["3",0]}),
 "33":n("ReferenceLatent",{"conditioning":["5",0],"latent":["32",0]}),
 "40":n("LoadImage",{"image":"CatVector.png"}),
 "41":n("ImageScaleToTotalPixels",{"image":["40",0],"upscale_method":"lanczos","megapixels":1.0,"resolution_steps":16}),
 "42":n("VAEEncode",{"pixels":["41",0],"vae":["3",0]}),
 "43":n("ReferenceLatent",{"conditioning":["33",0],"latent":["42",0]}),
 "6":n("EmptyFlux2LatentImage",{"width":1024,"height":1024,"batch_size":1}),
 "7":n("BasicGuider",{"model":["1",0],"conditioning":["43",0]}),
 "8":n("KSamplerSelect",{"sampler_name":"euler"}),
 "9":n("Flux2Scheduler",{"steps":20,"width":1024,"height":1024}),
 "10":n("RandomNoise",{"noise_seed":2024}),
 "11":n("SamplerCustomAdvanced",{"noise":["10",0],"guider":["7",0],"sampler":["8",0],"sigmas":["9",0],"latent_image":["6",0]}),
 "12":n("VAEDecode",{"samples":["11",0],"vae":["3",0]}),
 "13":n("SaveImage",{"images":["12",0],"filename_prefix":"FLUX2_2REF_TEST"}),
}
data=json.dumps({"prompt":prompt,"client_id":str(uuid.uuid4())}).encode()
req=urllib.request.Request(BASE+"/prompt",data=data,headers={"Content-Type":"application/json"})
try: r=json.loads(urllib.request.urlopen(req).read())
except urllib.error.HTTPError as e: print("ERR",e.code,e.read().decode()); raise SystemExit
pid=r["prompt_id"]; print("queued",pid); t0=time.time()
while time.time()-t0<300:
    h=json.loads(urllib.request.urlopen(BASE+"/history/"+pid).read())
    if pid in h:
        print("status:",h[pid]["status"].get("status_str"))
        for _,o in h[pid].get("outputs",{}).items():
            for im in o.get("images",[]): print("IMAGE:",im)
        print("ELAPSED %.1fs"%(time.time()-t0)); break
    time.sleep(2)
else: print("TIMEOUT")
