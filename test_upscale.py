import json,urllib.request,time,uuid
BASE="http://127.0.0.1:8188"
def n(c,i): return {"class_type":c,"inputs":i}
p={
 "1":n("UNETLoader",{"unet_name":"flux-2-klein-4b-fp8.safetensors","weight_dtype":"default"}),
 "2":n("CLIPLoader",{"clip_name":"qwen_3_4b.safetensors","type":"flux2","device":"default"}),
 "3":n("VAELoader",{"vae_name":"flux2-vae.safetensors"}),
 "4":n("CLIPTextEncode",{"text":"a tiny astronaut exploring a mossy forest, morning light, highly detailed","clip":["2",0]}),
 "5":n("FluxGuidance",{"conditioning":["4",0],"guidance":4.0}),
 "6":n("EmptyFlux2LatentImage",{"width":1024,"height":1024,"batch_size":1}),
 "7":n("BasicGuider",{"model":["1",0],"conditioning":["5",0]}),
 "8":n("KSamplerSelect",{"sampler_name":"euler"}),
 "9":n("Flux2Scheduler",{"steps":20,"width":1024,"height":1024}),
 "10":n("RandomNoise",{"noise_seed":555}),
 "11":n("SamplerCustomAdvanced",{"noise":["10",0],"guider":["7",0],"sampler":["8",0],"sigmas":["9",0],"latent_image":["6",0]}),
 "12":n("VAEDecode",{"samples":["11",0],"vae":["3",0]}),
 "60":n("UpscaleModelLoader",{"model_name":"4x-UltraSharp.pth"}),
 "61":n("ImageUpscaleWithModel",{"upscale_model":["60",0],"image":["12",0]}),
 "62":n("ImageScaleBy",{"image":["61",0],"upscale_method":"lanczos","scale_by":0.5}),
 "63":n("SaveImage",{"images":["62",0],"filename_prefix":"FLUX2_UPSCALE_TEST"}),
}
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
            for im in o.get("images",[]): print("IMAGE:",im)
        print("ELAPSED %.1fs"%(time.time()-t0)); break
    time.sleep(2)
else: print("TIMEOUT")
