#!/bin/bash
set -e
BASE="F:/ComfyUI/ComfyUI-Easy-Install/ComfyUI/models"
HF="https://huggingface.co"
dl () { # repo path destdir
  local url="$HF/$1/resolve/main/$2"
  local dest="$BASE/$3/$(basename "$2")"
  echo "=== $(date +%T) downloading $(basename "$2") -> $3 ==="
  curl.exe -L -C - --retry 3 --retry-delay 5 -s -o "$dest" "$url"
  echo "    done: $(ls -lh "$dest" | awk '{print $5}')"
}
mkdir -p "$BASE/controlnet"
dl "Comfy-Org/Qwen-Image_ComfyUI" "split_files/vae/qwen_image_vae.safetensors" "vae"
dl "Comfy-Org/z_image_turbo" "split_files/vae/ae.safetensors" "vae"
dl "alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union-2.1" "Z-Image-Turbo-Fun-Controlnet-Union-2.1.safetensors" "controlnet"
dl "Comfy-Org/Qwen-Image_ComfyUI" "split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors" "text_encoders"
dl "unsloth/Qwen-Image-Edit-2511-GGUF" "qwen-image-edit-2511-Q4_K_M.gguf" "unet"
dl "Comfy-Org/z_image_turbo" "split_files/diffusion_models/z_image_turbo_bf16.safetensors" "diffusion_models"
echo "=== ALL DOWNLOADS COMPLETE $(date +%T) ==="
