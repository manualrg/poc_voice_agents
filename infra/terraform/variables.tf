variable "project_id" {
  description = "GCP project ID where the PoC infrastructure is created."
  type        = string
}

variable "region" {
  description = "GCP region for regional resources."
  type        = string
  default     = "europe-west4"
}

variable "zone" {
  description = "GCP zone for the model worker VM."
  type        = string
  default     = "europe-west4-a"
}

variable "name_prefix" {
  description = "Prefix used for all PoC resources."
  type        = string
  default     = "poc-voice"
}

variable "network_name" {
  description = "Name for the VPC network. Leave null to derive it from name_prefix."
  type        = string
  default     = null
}

variable "subnet_cidr" {
  description = "CIDR range for the PoC subnet."
  type        = string
  default     = "10.40.0.0/24"
}

variable "machine_type" {
  description = "Compute Engine machine type for the model worker VM."
  type        = string
  default     = "n1-standard-8"
}

variable "gpu_type" {
  description = "GPU accelerator type for the model worker VM."
  type        = string
  default     = "nvidia-tesla-t4"
}

variable "gpu_count" {
  description = "Number of GPUs for machine types that need explicit guest accelerators."
  type        = number
  default     = 1

  validation {
    condition     = var.gpu_count >= 0
    error_message = "gpu_count must be 0 or greater."
  }
}

variable "attach_gpu_accelerator" {
  description = "Whether to attach gpu_type/gpu_count as an explicit guest accelerator. Keep true for N1+T4 and false for accelerator-optimized A2/G2 machine types."
  type        = bool
  default     = true
}

variable "boot_disk_size_gb" {
  description = "Boot disk size in GB."
  type        = number
  default     = 200
}

variable "boot_disk_type" {
  description = "Boot disk type."
  type        = string
  default     = "pd-balanced"
}

variable "boot_image_project" {
  description = "Project containing the boot image family."
  type        = string
  default     = "deeplearning-platform-release"
}

variable "boot_image_family" {
  description = "Boot image family for the worker VM."
  type        = string
  default     = "common-cu129-ubuntu-2204-nvidia-580"
}

variable "install_gpu_driver" {
  description = "Whether the startup script should install NVIDIA GPU drivers with Google's installer."
  type        = bool
  default     = false
}

variable "inference_port" {
  description = "Local model-serving port on the worker VM."
  type        = number
  default     = 8091
}

variable "assign_external_ip" {
  description = "Whether to assign an ephemeral external IP for outbound internet access."
  type        = bool
  default     = true
}

variable "iap_ssh_source_ranges" {
  description = "Source ranges allowed for IAP TCP forwarding to SSH."
  type        = list(string)
  default     = ["35.235.240.0/20"]
}

variable "deletion_protection" {
  description = "Whether deletion protection is enabled on the worker VM."
  type        = bool
  default     = false
}

variable "labels" {
  description = "Labels applied to created resources."
  type        = map(string)
  default = {
    app = "poc-voice"
    env = "dev"
  }
}
