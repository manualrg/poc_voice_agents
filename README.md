# poc-sst-soa

Deployment-only foundation for a GCP text-to-speech PoC.

This repository provisions a single configurable GPU model worker VM and provides
the runtime scripts needed to serve one vLLM-Omni TTS model at a time.

## What is included

- Terraform for a private-by-default GCP VM deployment.
- A reusable `model_worker_vm` Terraform module.
- vLLM-Omni start/stop/healthcheck scripts for:
  - `mistralai/Voxtral-4B-TTS-2603`
  - `Qwen/Qwen3-TTS-12Hz-0.6B-Base`
  - `Qwen/Qwen3-TTS-12Hz-1.7B-Base`
- Deployment and validation docs.

## What is intentionally excluded

- STT models such as Parakeet.
- Frontend UI.
- Notebooks.
- Sample analysis tooling.
- Experiment tracking and generated PoC artifacts.

## Default deployment shape

- GCP Compute Engine VM.
- `n1-standard-8`.
- 1x attached NVIDIA T4 16GB GPU.
- Default zone: `europe-west4-a`.
- Deep Learning VM Base GPU image with Ubuntu 22.04, CUDA 12.9, and NVIDIA 580.
- 200 GB balanced persistent disk.
- Inference service on port `8091`.
- No public inference ingress rule.
- SSH access through IAP.


## Instructions

The document describes the infrastructure deployment process [docs/deployment_runbook.md](docs/deployment_runbook.md). Important, read the document before running any cloud deployment command.

Terraform is intentionally single-environment for this PoC. Run it from `infra/terraform`.
