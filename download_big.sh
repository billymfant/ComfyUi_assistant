#!/bin/bash
BASE="F:/ComfyUI/ComfyUI-Easy-Install/ComfyUI/models"
HF="https://huggingface.co"
dl () {
  local dest="$BASE/$3/$(basename "$2")"
  echo "=== $(date +%T) START $(basename "$2") -> $3 ==="
  curl.exe -L -C - --retry 8 --retry-delay 5 --connect-timeout 30 \
     --speed-limit 30000 --speed-time 30 -o "$dest" "$HF/$1/resolve/main/$2"
  echo "=== $(date +%T) END $(basename "$2") rc=$? size=$(ls -lh "$dest" 2>/dev/null | awk '{print $5}') ==="
}
dl "Comfy-Org/Qwen-Image_ComfyUI" "split_files/text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors" "text_encoders"
dl "unsloth/Qwen-Image-Edit-2511-GGUF" "qwen-image-edit-2511-Q4_K_M.gguf" "unet"
dl "Comfy-Org/z_image_turbo" "split_files/diffusion_models/z_image_turbo_bf16.safetensors" "diffusion_models"
echo "=== ALL BIG DOWNLOADS DONE $(date +%T) ==="
