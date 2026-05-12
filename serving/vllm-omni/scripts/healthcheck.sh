#!/usr/bin/env bash
set -euo pipefail

PORT="${INFERENCE_PORT:-8091}"

curl -fsS "http://127.0.0.1:${PORT}/health" || curl -fsS "http://127.0.0.1:${PORT}/v1/models"
