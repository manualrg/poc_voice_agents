output "name" {
  description = "VM name."
  value       = google_compute_instance.this.name
}

output "self_link" {
  description = "VM self link."
  value       = google_compute_instance.this.self_link
}

output "internal_ip" {
  description = "VM internal IP."
  value       = google_compute_instance.this.network_interface[0].network_ip
}

output "external_ip" {
  description = "VM external IP, if assigned."
  value       = try(google_compute_instance.this.network_interface[0].access_config[0].nat_ip, null)
}
