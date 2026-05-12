# Terraform Deployment

This Terraform project creates the GCP foundation for one model-serving VM.
There is a single PoC environment; run Terraform from this folder directly.

It creates:

- VPC and subnet.
- IAP SSH firewall rule.
- Worker service account.
- One configurable GPU VM through `modules/model_worker_vm`.

The inference port is not exposed publicly. Use an SSH/IAP tunnel from your
laptop when testing.

## Command policy

Ask for explicit permission before running any cloud deployment command:

```bash
gcloud services enable
gcloud auth application-default login
terraform init
terraform plan
terraform apply
terraform destroy
gcloud compute ssh
gcloud compute instances start
gcloud compute instances stop
```

Local formatting does not deploy infrastructure:

```bash
terraform fmt -check -recursive
```

Validation requires initialization first because this Terraform configuration
uses a local module. `terraform init` does not deploy resources, but it is still
permission-gated for this PoC:

```bash
terraform init
terraform validate
```

## Configure

```bash
cp terraform.tfvars.example terraform.tfvars
```

Then set:

```hcl
project_id = "your-gcp-project-id"
```
