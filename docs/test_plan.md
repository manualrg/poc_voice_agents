# Test Plan

## Local Terraform formatting

From `infra/terraform`:

```bash
terraform fmt -check -recursive
```

## Terraform initialization and validation

`terraform validate` requires `terraform init` first because this environment
uses a module. Run both only after explicit permission:

```bash
terraform init
terraform validate
```

## Pre-deploy checks

Confirm before deployment:

- Active GCP project is the intended project.
- Compute Engine API is enabled.
- IAP API is enabled.
- Target zone supports N1+T4.
- Project has quota for one NVIDIA T4 GPU in `europe-west4`.
- For the default T4 deployment, use `europe-west4-a`, `europe-west4-b`, or
  `europe-west4-c`.

Commands that inspect or change GCP deployment state require explicit
permission before running.

## Post-deploy VM checks

After Terraform apply and SSH permission:

```bash
nvidia-smi
docker info
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
```

Expected result:

- `nvidia-smi` shows one NVIDIA T4.
- Docker runtime is available.
- Docker can access the GPU.

The default Deep Learning VM image includes NVIDIA driver and CUDA components.

## TTS smoke test: Voxtral

On the VM:

```bash
export HF_TOKEN="your-hugging-face-token-if-needed"
sudo -E /opt/poc-sst-soa/bin/start_voxtral.sh
sudo /opt/poc-sst-soa/bin/healthcheck.sh
```

From the laptop, with the SSH tunnel open:

```bash
curl -sS http://localhost:8091/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistralai/Voxtral-4B-TTS-2603",
    "input": "This is a short deployment smoke test.",
    "voice": "casual_male",
    "response_format": "wav"
  }' \
  --output voxtral_smoke.wav
```

Expected result:

- Request returns HTTP 200.
- `voxtral_smoke.wav` is created and playable.

## TTS smoke test: Qwen 0.6B

On the VM:

```bash
sudo /opt/poc-sst-soa/bin/stop_server.sh
export HF_TOKEN="your-hugging-face-token-if-needed"
sudo -E /opt/poc-sst-soa/bin/start_qwen_0_6b.sh
sudo /opt/poc-sst-soa/bin/healthcheck.sh
```

Run the matching vLLM-Omni Qwen request shape for the selected task type and
reference audio. Confirm the same local endpoint stays stable:

```text
http://localhost:8091/v1/audio/speech
```

Expected result:

- Qwen starts successfully on the same VM.
- The same endpoint accepts the Qwen request.
- A WAV file is returned.

## Optional Qwen 1.7B check

Run only after the 0.6B profile works:

```bash
sudo /opt/poc-sst-soa/bin/stop_server.sh
export HF_TOKEN="your-hugging-face-token-if-needed"
sudo -E /opt/poc-sst-soa/bin/start_qwen_1_7b.sh
sudo /opt/poc-sst-soa/bin/healthcheck.sh
```

Expected result:

- The model starts without GPU out-of-memory errors.
- A short speech request completes.

## Cleanup checks

When idle:

- Stop the running container.
- Stop the VM to reduce cost.
- Destroy Terraform-managed resources only after explicit permission.
