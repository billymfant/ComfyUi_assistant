"""Convert a ComfyUI UI-format workflow (v0.4, flat) to API/prompt format using
the live server's object_info, then POST it to /prompt and poll. This validates
that a saved workflow file actually executes — not just that links resolve.

Usage: run_ui_workflow.py <workflow.json>
"""
import json, sys, time, urllib.request, os
os.environ["no_proxy"] = "*"; os.environ["NO_PROXY"] = "*"
HOST = "http://127.0.0.1:8188"

wf = json.load(open(sys.argv[1], encoding="utf-8"))
nodes = {n["id"]: n for n in wf["nodes"]}
# link id -> (src_node, src_slot)
link_src = {l[0]: (l[1], l[2]) for l in wf["links"]}

def resolve_src(nid, slot):
    """Follow a link source through bypassed (mode 4) nodes, mimicking the UI's
    passthrough: a bypassed node forwards its first input of the same type as
    the requested output. Returns (node_id, slot) or None if the chain dangles."""
    n = nodes.get(nid)
    if n is None:
        return None
    if n.get("mode") not in (2, 4):
        return (nid, slot)
    want = n["outputs"][slot]["type"]
    for ip in n.get("inputs", []):
        if ip.get("type") == want and ip.get("link") is not None and ip["link"] in link_src:
            s0, s1 = link_src[ip["link"]]
            return resolve_src(s0, s1)
    return None

def obj_info(t):
    u = HOST + "/object_info/" + t
    return json.load(urllib.request.urlopen(u))[t]

cache = {}
def info(t):
    if t not in cache: cache[t] = obj_info(t)
    return cache[t]

prompt = {}
for nid, n in nodes.items():
    if n.get("mode") in (2, 4):       # muted / bypassed -> skip
        continue
    t = n["type"]
    if t in ("Note", "MarkdownNote", "Reroute"):
        continue
    d = info(t)
    order = list(d["input"].get("required", {})) + list(d["input"].get("optional", {}))
    req = d["input"].get("required", {}); opt = d["input"].get("optional", {})
    allin = {**req, **opt}
    ins = {}
    # connected inputs
    linked = {}
    for slot in n.get("inputs", []):
        if slot.get("link") is not None and slot["link"] in link_src:
            src = resolve_src(*link_src[slot["link"]])
            if src is not None:
                linked[slot["name"]] = [str(src[0]), src[1]]   # node id must be a string
    # widget inputs: those in `order` that are NOT a connected link, filled from widgets_values in order
    wv = n.get("widgets_values", []) or []
    CTRL = ("fixed", "randomize", "increment", "decrement")
    wi = 0
    for name in order:
        if name in linked:
            ins[name] = linked[name]
            continue
        spec = allin[name]
        # inputs that are pure connection types (no widget) and unconnected -> skip
        tspec = spec[0]
        is_widgety = isinstance(tspec, list) or tspec in ("INT","FLOAT","STRING","BOOLEAN","COMBO") or \
                     (len(spec) > 1 and isinstance(spec[1], dict) and "default" in spec[1])
        if not is_widgety:
            continue
        # skip a control_after_generate token (serialized after seed/noise_seed widgets)
        # unless this widget is a combo that legitimately contains it
        if wi < len(wv) and isinstance(wv[wi], str) and wv[wi] in CTRL and \
           not (isinstance(tspec, list) and wv[wi] in tspec):
            wi += 1
        if wi < len(wv):
            ins[name] = wv[wi]; wi += 1
        elif len(spec) > 1 and isinstance(spec[1], dict) and "default" in spec[1]:
            ins[name] = spec[1]["default"]
    # skip stray control_after_generate widget values (seed control) — consume if present
    prompt[str(nid)] = {"class_type": t, "inputs": ins}

# drop the extra "fixed"/"randomize" control tokens that aren't real inputs
for nid, p in prompt.items():
    p["inputs"] = {k: v for k, v in p["inputs"].items() if v not in ("fixed", "randomize", "increment", "decrement")}

data = json.dumps({"prompt": prompt}).encode()
try:
    r = urllib.request.urlopen(urllib.request.Request(HOST + "/prompt", data, {"Content-Type": "application/json"}))
    pid = json.load(r)["prompt_id"]
except urllib.error.HTTPError as e:
    print("VALIDATION ERROR:"); print(json.dumps(json.loads(e.read()), indent=1)[:2000]); sys.exit(1)
print("prompt_id:", pid, "| nodes:", len(prompt))
t0 = time.time()
while True:
    time.sleep(3)
    h = json.load(urllib.request.urlopen(HOST + "/history/" + pid))
    if pid in h:
        st = h[pid]["status"]
        if st.get("completed") or st.get("status_str") == "error":
            print(f"[{time.time()-t0:.0f}s] {st.get('status_str')}")
            for nid, o in h[pid].get("outputs", {}).items():
                for f in o.get("video", []) + o.get("images", []):
                    print("  OUT:", f.get("subfolder"), f.get("filename"))
            if st.get("status_str") == "error":
                for m in h[pid]["status"].get("messages", []):
                    if m[0] == "execution_error":
                        print("  ERR:", json.dumps(m[1])[:800])
            break
    if time.time() - t0 > 900:
        print("timeout"); break
