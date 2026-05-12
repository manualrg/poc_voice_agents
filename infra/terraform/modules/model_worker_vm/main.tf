resource "google_compute_instance" "this" {
  name                      = var.name
  zone                      = var.zone
  machine_type              = var.machine_type
  tags                      = var.network_tags
  labels                    = var.labels
  allow_stopping_for_update = true
  deletion_protection       = var.deletion_protection

  boot_disk {
    initialize_params {
      image = var.boot_image
      size  = var.boot_disk_size_gb
      type  = var.boot_disk_type
    }
  }

  dynamic "guest_accelerator" {
    for_each = var.attach_gpu_accelerator && var.gpu_count > 0 ? [1] : []

    content {
      type  = var.gpu_type
      count = var.gpu_count
    }
  }

  network_interface {
    subnetwork = var.subnetwork_self_link

    dynamic "access_config" {
      for_each = var.assign_external_ip ? [1] : []
      content {}
    }
  }

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "TERMINATE"
    provisioning_model  = "STANDARD"
  }

  service_account {
    email  = var.service_account_email
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }

  metadata = {
    poc-inference-port = tostring(var.inference_port)
  }

  metadata_startup_script = var.startup_script

  shielded_instance_config {
    enable_secure_boot          = false
    enable_vtpm                 = true
    enable_integrity_monitoring = true
  }
}
