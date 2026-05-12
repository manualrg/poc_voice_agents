#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${SCRIPT_DIR}/stop_server.sh"

CONTAINER_NAME="${CONTAINER_NAME:-vllm-omni-tts}"
IMAGE="${VLLM_OMNI_IMAGE:-vllm/vllm-omni:latest}"
PORT="${INFERENCE_PORT:-8091}"
HF_CACHE_DIR="${HF_CACHE_DIR:-/opt/poc-sst-soa/models/huggingface}"

mkdir -p "${HF_CACHE_DIR}"

docker run -d \
  --name "${CONTAINER_NAME}" \
  --gpus all \
  --ipc=host \
  --shm-size=16g \
  -p "127.0.0.1:${PORT}:${PORT}" \
  -e HF_TOKEN="${HF_TOKEN:-}" \
  -e HF_HOME=/models/huggingface \
  -v "${HF_CACHE_DIR}:/models/huggingface" \
  "${IMAGE}" \
  vllm serve mistralai/Voxtral-4B-TTS-2603 \
    --omni \
    --host 0.0.0.0 \
    --port "${PORT}"
