#!/usr/bin/env bash
# LTX-2.3 dev-fp8 download ONLY (Linux cloud). No ComfyUI run.
# Usage:
#   COMFY_ROOT=/workspace/ComfyUI ./install_ltx23_dev_fp8_download.sh
#   SKIP_UPSCALER=1 ./install_ltx23_dev_fp8_download.sh

set -euo pipefail
COMFY_ROOT="${COMFY_ROOT:-/workspace/ComfyUI}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SKIP_UPSCALER="${SKIP_UPSCALER:-0}"
SKIP_VAE="${SKIP_VAE:-0}"

CKPT="$COMFY_ROOT/models/checkpoints"
TE="$COMFY_ROOT/models/text_encoders"
LORA="$COMFY_ROOT/models/loras"
UP="$COMFY_ROOT/models/latent_upscale_models"
VAE="$COMFY_ROOT/models/vae"

mkdir -p "$CKPT" "$TE" "$LORA" "$UP" "$VAE"

dl() {
  local url="$1" out="$2" min_mb="$3"
  if [[ -f "$out" ]]; then
    local sz=$(( $(stat -c%s "$out" 2>/dev/null || stat -f%z "$out") / 1024 / 1024 ))
    if (( sz >= min_mb )); then
      echo "[skip] $(basename "$out") (${sz}MB)"
      return
    fi
    rm -f "$out"
  fi
  echo "[download] $(basename "$out")"
  curl -fL --retry 3 --continue-at - -o "${out}.part" "$url"
  mv "${out}.part" "$out"
}

dl "https://huggingface.co/Lightricks/LTX-2.3-fp8/resolve/main/ltx-2.3-22b-dev-fp8.safetensors" \
  "$CKPT/ltx-2.3-22b-dev-fp8.safetensors" 20000

dl "https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors" \
  "$TE/gemma_3_12B_it_fp4_mixed.safetensors" 8000

if [[ "$SKIP_UPSCALER" != "1" ]]; then
  dl "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-spatial-upscaler-x2-1.0.safetensors" \
    "$UP/ltx-2.3-spatial-upscaler-x2-1.0.safetensors" 50
fi

if [[ "$SKIP_VAE" != "1" ]]; then
  dl "https://huggingface.co/Kijai/LTX2.3_comfy/resolve/main/vae/taeltx2_3.safetensors" \
    "$VAE/taeltx2_3.safetensors" 10
fi

SRC="$REPO_ROOT/distill_loras/ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors"
DST="$LORA/ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors"
if [[ -f "$SRC" ]]; then
  cp -f "$SRC" "$DST"
  echo "[copy] distill LoRA -> $DST"
else
  echo "[warn] missing $SRC — download official LoRA or copy manually"
fi

echo "Done. Sync workflows: cp -r $REPO_ROOT/workflows/ltx云GPU $COMFY_ROOT/user/default/workflows/"
