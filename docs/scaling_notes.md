# Scaling Notes

The first implementation uses one model worker VM. The Terraform module is named
`model_worker_vm` so GPU choice and worker count can change later without
renaming the infrastructure boundary.

## Current shape

- One VM.
- One active model at a time.
- Manual stop/start to switch models.
- Private API access through an SSH/IAP tunnel.

## Scale-up path

The current default uses an N1 VM with one T4 GPU:

```hcl
machine_type           = "n1-standard-8"
gpu_type               = "nvidia-tesla-t4"
gpu_count              = 1
attach_gpu_accelerator = true
```

If T4 is too tight for Voxtral or Qwen 1.7B, the next step is A100 40GB:

```hcl
machine_type = "a2-highgpu-1g"
gpu_type     = "nvidia-tesla-a100"
gpu_count    = 1
attach_gpu_accelerator = false
```

If A100 40GB is not enough, use `a2-ultragpu-1g` with A100 80GB, subject to
quota and cost.

## Scale-out path

Add multiple workers by wrapping `model_worker_vm` with `for_each` or `count`.
Each worker should run a single active model profile.

Future additions can include:

- Instance templates.
- Managed instance groups.
- A private load balancer.
- A small API gateway that routes model aliases to workers.

## Public access path

Do not expose inference publicly in the first PoC. If public access is needed
later, add authentication and a gateway before opening ingress to model workers.
