"""Reusable ComfyUI UI-workflow (version 0.4) builder."""
import json

class WF:
    def __init__(self):
        self.nodes=[]; self.links=[]; self.conns=[]; self.byid={}; self._lid=0; self.groups=[]
    def add(self,nid,typ,pos,size,widgets,ins,outs,mode=0,title=None,color=None):
        nd={"id":nid,"type":typ,"pos":list(pos),"size":list(size),"flags":{},"order":0,"mode":mode,
            "inputs":[{"name":a,"type":b,"link":None} for a,b in ins],
            "outputs":[{"name":a,"type":b,"links":[],"slot_index":i} for i,(a,b) in enumerate(outs)],
            "properties":{"Node name for S&R":typ},"widgets_values":widgets}
        if title: nd["title"]=title
        if color: nd["color"]=color; nd["bgcolor"]=color
        self.nodes.append(nd); self.byid[nid]=nd; return nd
    def connect(self,src,sslot,dst,dslot,typ): self.conns.append((src,sslot,dst,dslot,typ))
    def group(self,gid,title,bounding,color="#3f789e"):
        self.groups.append({"id":gid,"title":title,"bounding":list(bounding),"color":color,"font_size":24,"flags":{}})
    def finalize(self,path,wid="wf"):
        for src,ss,dst,ds,typ in self.conns:
            self._lid+=1; L=self._lid
            self.byid[src]["outputs"][ss]["links"].append(L)
            self.byid[dst]["inputs"][ds]["link"]=L
            self.links.append([L,src,ss,dst,ds,typ])
        for i,nd in enumerate(self.nodes): nd["order"]=i
        wf={"id":wid,"revision":0,"last_node_id":max(self.byid)+1,"last_link_id":self._lid,
            "nodes":self.nodes,"links":self.links,"groups":self.groups,"config":{},
            "extra":{"ds":{"scale":0.7,"offset":[400,300]}},"version":0.4}
        open(path,"w",encoding="utf-8").write(json.dumps(wf,indent=2))
        # validate
        lids={l[0] for l in self.links}; errs=[]
        for nd in self.nodes:
            for ip in nd["inputs"]:
                if ip["link"] is not None and ip["link"] not in lids: errs.append((nd["id"],"badin"))
        return {"nodes":len(self.nodes),"links":len(self.links),"errors":errs}
