"""Merge the 5 module workflows into one MASTER workflow.
Each module is offset into its own vertical band, wrapped in a big labelled group,
and (except module 0 = Flux 2) fully bypassed by default. Adds a standalone 4K
upscaler module. The user enables a module by selecting its group + Ctrl+B.
"""
import json, os

WF="F:/ComfyUI/ComfyUI-Easy-Install/ComfyUI/user/default/workflows/"
MODULES=[
 ("01_FLUX2_AllInOne_T2I_I2I_Reference.json","A) FLUX 2  -  Text->Image / Image->Image / Reference (DEFAULT: ON)","#1c3a5e",False),
 ("03_ZIMAGE_t2i.json","B) Z-IMAGE TURBO  -  fast Text->Image + best in-image text","#1c3a5e",True),
 ("04_QWEN_EDIT.json","C) QWEN-IMAGE-EDIT 2511  -  instruction image editing","#1c3a5e",True),
 ("05_ZIMAGE_controlnet.json","D) Z-IMAGE + CONTROLNET  -  pose / depth / edge control","#1c3a5e",True),
 ("02_IMAGE_to_TEXT_QwenVL.json","E) IMAGE->TEXT  -  caption / prompt-extract / VQA (Qwen3-VL)","#1c3a5e",True),
]
BAND=1800
allnodes=[]; alllinks=[]; groups=[]; gid=[0]
def newgroup(title,bb,color):
    gid[0]+=1; groups.append({"id":gid[0],"title":title,"bounding":bb,"color":color,"font_size":28,"flags":{}})

for i,(fn,title,color,bypass) in enumerate(MODULES):
    wf=json.load(open(WF+fn,encoding="utf-8"))
    base=(i+1)*1000; yoff=i*BAND
    xs=[]; ys=[]
    for n in wf["nodes"]:
        n["id"]+=base
        n["pos"]=[n["pos"][0], n["pos"][1]+yoff]
        if bypass and n["type"]!="Note": n["mode"]=4
        for ip in n.get("inputs",[]):
            if ip.get("link") is not None: ip["link"]+=base
        for op in n.get("outputs",[]):
            op["links"]=[l+base for l in (op.get("links") or [])]
        sx,sy=(n["size"] if isinstance(n["size"],list) else [220,120])
        xs+=[n["pos"][0], n["pos"][0]+sx]; ys+=[n["pos"][1], n["pos"][1]+sy]
        allnodes.append(n)
    for L in wf["links"]:
        alllinks.append([L[0]+base,L[1]+base,L[2],L[3]+base,L[4],L[5]])
    # module enclosing group
    newgroup(title,[min(xs)-50, min(ys)-150, (max(xs)-min(xs))+100, (max(ys)-min(ys))+220], color)

# ---- standalone 4K upscaler module ----
base=9000; yoff=len(MODULES)*BAND
nid=base
def add(typ,pos,size,widgets,ins,outs,mode=4,title=None,color=None):
    global nid
    nd={"id":nid,"type":typ,"pos":[pos[0],pos[1]+yoff],"size":size,"flags":{},"order":0,"mode":mode,
        "inputs":[{"name":a,"type":b,"link":None} for a,b in ins],
        "outputs":[{"name":a,"type":b,"links":[],"slot_index":k} for k,(a,b) in enumerate(outs)],
        "properties":{"Node name for S&R":typ},"widgets_values":widgets}
    if title: nd["title"]=title
    if color: nd["color"]=color; nd["bgcolor"]=color
    allnodes.append(nd); nid+=1; return nd["id"]
lid=[90000]
def link(s,ss,d,ds,t):
    lid[0]+=1
    for n in allnodes:
        if n["id"]==s: n["outputs"][ss]["links"].append(lid[0])
        if n["id"]==d: n["inputs"][ds]["link"]=lid[0]
    alllinks.append([lid[0],s,ss,d,ds,t]); return lid[0]
li=add("LoadImage",[0,0],[330,330],["example.png","image"],[],[("IMAGE","IMAGE"),("MASK","MASK")],title="Any image to upscale")
um=add("UpscaleModelLoader",[370,0],[300,58],["4x-UltraSharp.pth"],[],[("UPSCALE_MODEL","UPSCALE_MODEL")],title="4K upscale model")
iu=add("ImageUpscaleWithModel",[370,100],[260,46],[],[("upscale_model","UPSCALE_MODEL"),("image","IMAGE")],[("IMAGE","IMAGE")],title="Upscale 4x")
sm=add("ImageScaleToMaxDimension",[680,0],[280,82],["lanczos",3840],[("image","IMAGE")],[("IMAGE","IMAGE")],title="Cap longest side -> 4K")
sv=add("SaveImage",[980,0],[460,460],["MASTER_4K"],[("images","IMAGE")],[],title="4K output")
link(um,0,iu,0,"UPSCALE_MODEL"); link(li,0,iu,1,"IMAGE"); link(iu,0,sm,0,"IMAGE"); link(sm,0,sv,0,"IMAGE")
newgroup("F) 4K UPSCALER  -  upscale ANY image up to 4K (independent)",[-50,yoff-150,1600,720],"#1c5e2e")

# header note
note=("########  MASTER WORKFLOW  ########\n\n"
 "Every capability in ONE file, as separate MODULES (the big coloured boxes).\n\n"
 "HOW TO USE:\n"
 "  1. Only Module A (Flux 2) is ON by default. Everything else is bypassed.\n"
 "  2. To use another module: click its big group title to select it,\n"
 "     then press Ctrl+B to ENABLE it. Press Ctrl+B again to turn it OFF.\n"
 "  3. Turn OFF the module you are done with so two heavy models don't run\n"
 "     at once (16GB). Each module has its own Save node + prompt.\n"
 "  4. Module F (4K upscaler) is standalone - load any image, enable, run.\n\n"
 "MODULES:\n"
 "  A Flux 2     - best quality t2i / i2i / multi-reference (+4K group inside)\n"
 "  B Z-Image    - fastest t2i, best text-in-image (+4K group inside)\n"
 "  C Qwen-Edit  - 'change/remove/edit' instructions (heavy 20B, +4K inside)\n"
 "  D ControlNet - lock pose/depth/edges (+4K group inside)\n"
 "  E Image->Text- describe an image / extract a prompt -> paste into A or B\n"
 "  F 4K Upscaler- upscale any image up to 3840px\n\n"
 "Each generating module ALSO has its own '4K UPSCALE' sub-group (green) -\n"
 "enable it the same way (Ctrl+B) to save a 4K version of that module's output.")
allnodes.append({"id":99999,"type":"Note","pos":[-1700,-250],"size":[640,620],"flags":{},"order":0,"mode":0,
    "inputs":[],"outputs":[],"properties":{},"widgets_values":[note],"color":"#5e4a1c","bgcolor":"#5e4a1c","title":"READ ME"})

master={"id":"master","revision":0,"last_node_id":100000,"last_link_id":lid[0],
        "nodes":allnodes,"links":alllinks,"groups":groups,"config":{},
        "extra":{"ds":{"scale":0.35,"offset":[1900,400]}},"version":0.4}
out=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"workflows","00_MASTER_WORKFLOW.json")
json.dump(master,open(out,"w",encoding="utf-8"),indent=2)

# validate
byid={n["id"]:n for n in allnodes}; lids={l[0] for l in alllinks}; errs=0
for n in allnodes:
    for ip in n.get("inputs",[]):
        if ip.get("link") is not None and ip["link"] not in lids: errs+=1
for L in alllinks:
    d=byid.get(L[3])
    if not d or L[4]>=len(d["inputs"]) or d["inputs"][L[4]]["link"]!=L[0]: errs+=1
print("MASTER nodes",len(allnodes),"links",len(alllinks),"groups",len(groups),"ERRORS",errs)
