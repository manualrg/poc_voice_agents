variable "name" {
  description = "Name of the model worker VM."
  type        = string
}

variable "zone" {
  description = "GCP zone for the VM."
  type        = string
}

variable "machine_type" {
  description = "Compute Engine machine type."
  type        = string
}

variable "gpu_type" {
  description = "GPU accelerator type."
  type        = string
}

variable "gpu_count" {
  description = "Number of GPUs to attach when attach_gpu_accelerator is true."
  type        = number
}

variable "attach_gpu_accelerator" {
  description = "Whether to attach gpu_type/gpu_count as an explicit guest accelerator."
  type        = bool
}

variable "boot_disk_size_gb" {
  description = "Boot disk size in GB."
  type        = number
}

variable "boot_disk_type" {
  description = "Boot disk type."
  type        = string
}

variable "boot_image" {
  description = "Boot image self link."
  type        = string
}

variable "subnetwork_self_link" {
  description = "Subnetwork self link."
  type        = string
}

variable "assign_external_ip" {
  description = "Whether to assign an ephemeral external IP."
  type        = bool
}

variable "service_account_email" {
  description = "Service account email attached to the VM."
  type        = string
}

variable "network_tags" {
  description = "Network tags for firewall targeting."
  type        = list(string)
  default     = []
}

variable "labels" {
  description = "Labels applied to the VM."
  type        = map(string)
  default     = {}
}

variable "startup_script" {
  description = "Startup script rendered by the root module."
  type        = string
}

variable "inference_port" {
  description = "Local inference port."
  type        = number
}

variable "deletion_protection" {
  description = "Whether deletion protection is enabled."
  type        = bool
  default     = false
}
