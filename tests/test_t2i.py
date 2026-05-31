import json,urllib.request,time,uuid
BASE="http://127.0.0.1:8188"
prompt={
 "1":{"class_type":"UNETLoader","inputs":{"unet_name":"flux-2-klein-4b-fp8.safetensors","weight_dtype":"default"}},
 "2":{"class_type":"CLIPLoader","inputs":{"clip_name":"qwen_3_4b.safetensors","type":"flux2","device":"default"}},
 "3":{"class_type":"VAELoader","inputs":{"vae_name":"flux2-vae.safetensors"}},
 "4":{"class_type":"CLIPTextEncode","inputs":{"text":"a photo of a red apple on a rustic wooden table, soft studio lighting, sharp focus","clip":["2",0]}},
 "5":{"class_type":"FluxGuidance","inputs":{"conditioning":["4",0],"guidance":4.0}},
 "6":{"class_type":"EmptyFlux2LatentImage","inputs":{"width":1024,"height":1024,"batch_size":1}},
 "7":{"class_type":"BasicGuider","inputs":{"model":["1",0],"conditioning":["5",0]}},
 "8":{"class_type":"KSamplerSelect","inputs":{"sampler_name":"euler"}},
 "9":{"class_type":"Flux2Scheduler","inputs":{"steps":20,"width":1024,"height":1024}},
 "10":{"class_type":"RandomNoise","inputs":{"noise_seed":12345}},
 "11":{"class_type":"SamplerCustomAdvanced","inputs":{"noise":["10",0],"guider":["7",0],"sampler":["8",0],"sigmas":["9",0],"latent_image":["6",0]}},
 "12":{"class_type":"VAEDecode","inputs":{"samples":["11",0],"vae":["3",0]}},
 "13":{"class_type":"SaveImage","inputs":{"images":["12",0],"filename_prefix":"FLUX2_T2I_TEST"}}
}
cid=str(uuid.uuid4())
data=json.dumps({"prompt":prompt,"client_id":cid}).encode()
req=urllib.request.Request(BASE+"/prompt",data=data,headers={"Content-Type":"application/json"})
try:
    r=json.loads(urllib.request.urlopen(req).read())
except urllib.error.HTTPError as e:
    print("SUBMIT ERROR",e.code); print(e.read().decode()); raise SystemExit
pid=r["prompt_id"]; print("queued",pid)
t0=time.time()
while time.time()-t0<300:
    h=json.loads(urllib.request.urlopen(BASE+"/history/"+pid).read())
    if pid in h:
        st=h[pid]["status"]
        print("status:",st.get("status_str"),"completed:",st.get("completed"))
        outs=h[pid].get("outputs",{})
        for nid,o in outs.items():
            for im in o.get("images",[]):
                print("IMAGE:",im)
        print("ELAPSED %.1fs"%(time.time()-t0))
        break
    time.sleep(2)
else:
    print("TIMEOUT")
