import json,urllib.request,time,uuid
BASE="http://127.0.0.1:8188"
def n(c,i): return {"class_type":c,"inputs":i}
p={
 "1":n("LoadImage",{"image":"FLUX2_FUSION3_00001_.png"}),
 "2":n("UpscaleModelLoader",{"model_name":"4x-UltraSharp.pth"}),
 "3":n("ImageUpscaleWithModel",{"upscale_model":["2",0],"image":["1",0]}),
 "4":n("ImageScaleBy",{"image":["3",0],"upscale_method":"lanczos","scale_by":0.5}),
 "5":n("SaveImage",{"images":["4",0],"filename_prefix":"FLUX2_FUSION3_2K"}),
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
            for im in o.get("images",[]): print("IMAGE:",im["filename"])
        print("ELAPSED %.1fs"%(time.time()-t0)); break
    time.sleep(2)
else: print("TIMEOUT")
