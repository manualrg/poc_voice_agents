# Deployment Runbook



## Permission policy

Ask for explicit permission before running every cloud-mutating or
deployment-affecting command:

```bash
gcloud services enable compute.googleapis.com iap.googleapis.com
gcloud auth application-default login
terraform init
terraform plan
terraform apply
terraform destroy
gcloud compute ssh
gcloud compute instances start
gcloud compute instances stop
```

## Requirements

Check whether required tools are installed locally:

- Terraform `>= 1.6`.
- Google Cloud CLI.

Check versions
```bash
gcloud --version
terraform --version
```

Authenticate with GCP only after explicit permission:

```bash
gcloud auth login
gcloud auth application-default login
```


Enable required APIs only after explicit permission:

```bash
gcloud services enable compute.googleapis.com iap.googleapis.com
```

## Configure variables

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set:

```hcl
project_id = "your-gcp-project-id"
```

The default VM is:

```hcl
region = "europe-west4"
zone   = "europe-west4-a"

machine_type      = "n1-standard-8"
gpu_type          = "nvidia-tesla-t4"
gpu_count         = 1
attach_gpu_accelerator = true
boot_disk_size_gb = 200
boot_image_project = "deeplearning-platform-release"
boot_image_family  = "common-cu129-ubuntu-2204-nvidia-580"
install_gpu_driver = false
inference_port    = 8091
```

The default uses an N1 machine type with one attached NVIDIA T4 GPU. N1
instances do not include GPUs in the machine type, so
`attach_gpu_accelerator` must stay `true`.

The default image is the current documented Deep Learning VM Base GPU image:
`common-cu129-ubuntu-2204-nvidia-580`, which includes Ubuntu 22.04, CUDA 12.9,
and NVIDIA driver 580.

Google's GPU location table lists `N1+T4` in `europe-west4-a`,
`europe-west4-b`, and `europe-west4-c`. If one zone has no capacity, try another
zone in the same region before changing the machine shape.

## Format locally

This command does not deploy infrastructure and does not require Terraform
module/provider installation:

```bash
terraform fmt -check -recursive
```

## Initialize and validate

Terraform must be initialized before `terraform validate` can inspect the local
root module and provider schemas. `terraform init` does not create cloud
resources, but it is still permission-gated for this PoC.

Run only after explicit permission:

```bash
terraform init
terraform validate
```

## Deploy

Run only after explicit permission:

```bash
terraform plan
terraform apply
```

Terraform outputs the SSH and tunnel commands.

If this workspace was previously initialized from the old `envs/dev` layout,
the repo includes `moved` blocks that remap existing state from
`module.deployment.*` to the flattened root layout. Keep `moved.tf` until one
successful `terraform apply` has completed after the flattening migration.

## Connect

Open an SSH session only after explicit permission:

```bash
gcloud compute ssh <worker-name> --zone <zone> --tunnel-through-iap
```

Open the local API tunnel only after explicit permission:

```bash
gcloud compute ssh <worker-name> --zone <zone> --tunnel-through-iap -- -L 8091:localhost:8091
```

The API is then reachable from the laptop at:

```text
http://localhost:8091
```

## Serving scripts on the VM

Terraform renders the local `serving/vllm-omni/scripts` files into the VM
startup script. After startup completes, they are available under:

```text
/opt/poc-sst-soa/bin
```

## Start one model

On the VM:

```bash
export HF_TOKEN="your-hugging-face-token-if-needed"
sudo -E /opt/poc-sst-soa/bin/start_voxtral.sh
```

To switch models:

```bash
sudo /opt/poc-sst-soa/bin/stop_server.sh
sudo -E /opt/poc-sst-soa/bin/start_qwen_0_6b.sh
```

## Cleanup

Stop or destroy resources only after explicit permission:

```bash
gcloud compute instances stop <worker-name> --zone <zone>
terraform destroy
```
