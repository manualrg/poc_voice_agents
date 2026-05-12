output "worker_name" {
  description = "Name of the model worker VM."
  value       = module.model_worker_vm.name
}

output "worker_zone" {
  description = "Zone of the model worker VM."
  value       = var.zone
}

output "worker_internal_ip" {
  description = "Internal IP address of the model worker VM."
  value       = module.model_worker_vm.internal_ip
}

output "worker_external_ip" {
  description = "External IP address of the model worker VM, if assigned."
  value       = module.model_worker_vm.external_ip
}

output "ssh_iap_command" {
  description = "Command for opening an SSH session through IAP."
  value       = "gcloud compute ssh ${module.model_worker_vm.name} --zone ${var.zone} --tunnel-through-iap"
}

output "ssh_tunnel_command" {
  description = "Command for forwarding localhost inference traffic to the worker."
  value       = "gcloud compute ssh ${module.model_worker_vm.name} --zone ${var.zone} --tunnel-through-iap -- -L ${var.inference_port}:localhost:${var.inference_port}"
}

output "local_api_base_url" {
  description = "Local API URL after opening the SSH tunnel."
  value       = "http://localhost:${var.inference_port}"
}
