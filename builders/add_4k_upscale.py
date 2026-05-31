"""Inject a bypassable '4K UPSCALE' branch into an existing ComfyUI workflow JSON.
Finds the first SaveImage, taps its image source (the VAEDecode output), and adds
UpscaleModelLoader -> ImageUpscaleWithModel -> ImageScaleToMaxDimension(3840) -> SaveImage,
all bypassed (mode 4) by default. Usage: python add_4k_upscale.py in.json out.json PREFIX
"""
import json,sys

def inject(path,out,prefix):
    wf=json.load(open(path,encoding="utf-8"))
    nodes=wf["nodes"]; links=wf["links"]; byid={n["id"]:n for n in nodes}
    sv=[n for n in nodes if n["type"]=="SaveImage"][0]
    img_link=next(ip["link"] for ip in sv["inputs"] if ip["name"]=="images")
    src=next((L[1],L[2]) for L in links if L[0]==img_link)   # (src_node, src_slot)
    nid=max(byid)+1; lid=[wf.get("last_link_id",0)]
    def add(typ,pos,size,widgets,ins,outs,title=None,color=None):
        nonlocal nid
        nd={"id":nid,"type":typ,"pos":pos,"size":size,"flags":{},"order":len(nodes),"mode":4,
            "inputs":[{"name":a,"type":b,"link":None} for a,b in ins],
            "outputs":[{"name":a,"type":b,"links":[],"slot_index":i} for i,(a,b) in enumerate(outs)],
            "properties":{"Node name for S&R":typ},"widgets_values":widgets}
        if title: nd["title"]=title
        if color: nd["color"]=color; nd["bgcolor"]=color
        nodes.append(nd); byid[nid]=nd; nid+=1; return nd["id"]
    def link(s,ss,d,ds,t):
        lid[0]+=1; byid[s]["outputs"][ss]["links"].append(lid[0]); byid[d]["inputs"][ds]["link"]=lid[0]
        links.append([lid[0],s,ss,d,ds,t]); return lid[0]
    ys=max(n["pos"][1]+(n["size"][1] if isinstance(n["size"],list) else 150) for n in nodes)+90
    xs=min(n["pos"][0] for n in nodes)
    uml=add("UpscaleModelLoader",[xs,ys],[300,58],["4x-UltraSharp.pth"],[],[("UPSCALE_MODEL","UPSCALE_MODEL")],title="4K upscale model")
    iuw=add("ImageUpscaleWithModel",[xs+340,ys],[260,46],[],[("upscale_model","UPSCALE_MODEL"),("image","IMAGE")],[("IMAGE","IMAGE")],title="Upscale 4x")
    ism=add("ImageScaleToMaxDimension",[xs+640,ys],[280,82],["lanczos",3840],[("image","IMAGE")],[("IMAGE","IMAGE")],title="Cap longest side -> 4K (3840)")
    sv4=add("SaveImage",[xs+960,ys],[420,420],[prefix],[("images","IMAGE")],[],title="4K output")
    link(uml,0,iuw,0,"UPSCALE_MODEL"); link(src[0],src[1],iuw,1,"IMAGE")
    link(iuw,0,ism,0,"IMAGE"); link(ism,0,sv4,0,"IMAGE")
    wf["last_node_id"]=max(byid); wf["last_link_id"]=lid[0]
    gid=max([g["id"] for g in wf.get("groups",[])],default=0)+1
    wf.setdefault("groups",[]).append({"id":gid,"title":"4K UPSCALE  (select these 4 nodes, Ctrl+B to enable)",
        "bounding":[xs-20,ys-90,1420,580],"color":"#3f9b46","font_size":24,"flags":{}})
    json.dump(wf,open(out,"w",encoding="utf-8"),indent=2)
    print("injected 4K upscale into",out,"| nodes now",len(nodes))

if __name__=="__main__":
    inject(sys.argv[1],sys.argv[2],sys.argv[3])
