# Flux 2 [Klein] — All-in-One Image Workflow

A single ComfyUI workflow that does **text-to-image**, **image-to-image**, and **image-reference-to-image**, 100% local and free, using the Flux 2 Klein models you already have installed.

**File:** `FLUX2_AllInOne_T2I_I2I_Reference.json`
(also installed in ComfyUI → Workflows sidebar)

## Load it
- ComfyUI → top menu **Workflow → Open** → pick `FLUX2_AllInOne_T2I_I2I_Reference.json`
- Or just **drag the .json file** onto the ComfyUI canvas.

## The 3 modes (controlled by how many Reference groups you enable)

| Mode | What to do |
|------|-----------|
| **1. Text → Image** | Default state. All 3 Reference groups are bypassed (red). Type a prompt → **Run**. |
| **2. Image → Image** | Enable **Reference 1**: click its 4 nodes (or the purple group), press **Ctrl+B** to un-bypass. Load your image in *Ref 1 image*. Prompt = the change you want. |
| **3. Reference → Image** | Enable Reference 1 **and** 2 (and 3), load a different image in each. The model uses/blends them all. |

> Un-bypass = select node(s) and press **Ctrl+B**. Bypassed nodes look faded/red.

## Settings worth knowing
- **Guidance** (FluxGuidance node): 3–5. Higher = follows prompt harder.
- **Steps** (Flux2Scheduler): 20 default; 28–32 for more detail.
- **Canvas size** (EmptyFlux2LatentImage) and **width/height in Flux2Scheduler must match** — keep them equal. Try 1024×1024, 1152×896, 896×1152.
- **Seed** (RandomNoise): `fixed` to reproduce a result, `randomize` to explore.

## Speed vs. quality
- Default = `flux-2-klein-4b-fp8` + `qwen_3_4b` → ~20–30s per image on your RTX 4080 SUPER. Great quality.
- **Max quality:** in the loaders, switch the diffusion model to `flux-2-klein-base-9b-fp8` **and** the text encoder to `qwen_3_8b_fp8mixed`. Slower / heavier on VRAM, sharper results.

## Why this design
Flux 2 is natively a generation **and** editing model. Reference images are injected with `ReferenceLatent` nodes chained on the prompt conditioning — bypassing one passes the prompt straight through, so any combination of references works from the same graph. Klein is guidance-distilled, so it uses `BasicGuider` (no negative prompt / CFG needed) with the resolution-aware `Flux2Scheduler` for correct results.

All three modes were tested live against your server before delivery.
