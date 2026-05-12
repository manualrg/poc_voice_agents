# vLLM-Omni TTS

These scripts start one TTS model at a time on the worker VM. Stop the current
container before starting a different model.

The scripts expect Docker with GPU runtime support and use the
`vllm/vllm-omni:latest` image by default.

## Environment

Optional variables:

```bash
export HF_TOKEN="..."
export INFERENCE_PORT=8091
export VLLM_OMNI_IMAGE=vllm/vllm-omni:latest
```

## Commands

```bash
./scripts/start_voxtral.sh
./scripts/stop_server.sh
./scripts/start_qwen_0_6b.sh
./scripts/healthcheck.sh
```

The API is intended to be reached through an SSH/IAP tunnel from your laptop:

```bash
gcloud compute ssh <worker-name> --zone <zone> --tunnel-through-iap -- -L 8091:localhost:8091
```
