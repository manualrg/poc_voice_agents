locals {
  network_name = coalesce(var.network_name, "${var.name_prefix}-vpc")
  subnet_name  = "${var.name_prefix}-subnet"
  worker_name  = "${var.name_prefix}-worker"
  worker_tag   = "${var.name_prefix}-worker"
}

data "google_compute_image" "worker_os" {
  family  = var.boot_image_family
  project = var.boot_image_project
}

resource "google_compute_network" "this" {
  name                    = local.network_name
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "this" {
  name                     = local.subnet_name
  ip_cidr_range            = var.subnet_cidr
  region                   = var.region
  network                  = google_compute_network.this.id
  private_ip_google_access = true
}

resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "${var.name_prefix}-allow-iap-ssh"
  network = google_compute_network.this.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = var.iap_ssh_source_ranges
  target_tags   = [local.worker_tag]
}

resource "google_service_account" "worker" {
  account_id   = "${replace(var.name_prefix, "-", "")}-worker"
  display_name = "PoC SST SOA model worker"
}

resource "google_project_iam_member" "worker_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

resource "google_project_iam_member" "worker_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.worker.email}"
}

module "model_worker_vm" {
  source = "./modules/model_worker_vm"

  name                   = local.worker_name
  zone                   = var.zone
  machine_type           = var.machine_type
  gpu_type               = var.gpu_type
  gpu_count              = var.gpu_count
  attach_gpu_accelerator = var.attach_gpu_accelerator
  boot_disk_size_gb      = var.boot_disk_size_gb
  boot_disk_type         = var.boot_disk_type
  boot_image             = data.google_compute_image.worker_os.self_link
  subnetwork_self_link   = google_compute_subnetwork.this.self_link
  assign_external_ip     = var.assign_external_ip
  service_account_email  = google_service_account.worker.email
  network_tags           = [local.worker_tag]
  labels                 = var.labels
  inference_port         = var.inference_port
  deletion_protection    = var.deletion_protection

  startup_script = templatefile("${path.module}/modules/model_worker_vm/startup.sh.tpl", {
    inference_port       = var.inference_port
    install_gpu_driver   = var.install_gpu_driver
    healthcheck_script   = file("${path.module}/../../serving/vllm-omni/scripts/healthcheck.sh")
    start_qwen_0_6b      = file("${path.module}/../../serving/vllm-omni/scripts/start_qwen_0_6b.sh")
    start_qwen_1_7b      = file("${path.module}/../../serving/vllm-omni/scripts/start_qwen_1_7b.sh")
    start_voxtral_script = file("${path.module}/../../serving/vllm-omni/scripts/start_voxtral.sh")
    stop_server_script   = file("${path.module}/../../serving/vllm-omni/scripts/stop_server.sh")
  })
}
