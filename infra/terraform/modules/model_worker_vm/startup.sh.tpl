#!/usr/bin/env bash
set -euxo pipefail

export DEBIAN_FRONTEND=noninteractive

install -d -m 0755 /opt/poc-sst-soa/bin
install -d -m 0755 /opt/poc-sst-soa/config
install -d -m 0755 /opt/poc-sst-soa/logs
install -d -m 0755 /opt/poc-sst-soa/models

apt-get update
apt-get install -y ca-certificates curl gnupg jq git docker.io python3

systemctl enable --now docker

if [[ "${install_gpu_driver}" == "true" ]] && ! command -v nvidia-smi >/dev/null 2>&1; then
  install -d -m 0755 /opt/google/cuda-installer
  curl -fSsL https://storage.googleapis.com/compute-gpu-installation-us/installer/latest/cuda_installer.pyz \
    --output /opt/google/cuda-installer/cuda_installer.pyz
  python3 /opt/google/cuda-installer/cuda_installer.pyz install_driver --installation-mode=repo --installation-branch=lts || true
fi

if ! command -v nvidia-ctk >/dev/null 2>&1; then
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

  curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    > /etc/apt/sources.list.d/nvidia-container-toolkit.list

  apt-get update
  apt-get install -y nvidia-container-toolkit
fi

nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

for user in ubuntu jupyter; do
  if id "$user" >/dev/null 2>&1; then
    usermod -aG docker "$user"
  fi
done

cat >/opt/poc-sst-soa/config/runtime.env <<EOF
INFERENCE_PORT=${inference_port}
VLLM_OMNI_IMAGE=vllm/vllm-omni:latest
HF_HOME=/models/huggingface
EOF

cat >/opt/poc-sst-soa/bin/healthcheck.sh <<'EOF_HEALTHCHECK'
${healthcheck_script}
EOF_HEALTHCHECK

cat >/opt/poc-sst-soa/bin/start_qwen_0_6b.sh <<'EOF_START_QWEN_0_6B'
${start_qwen_0_6b}
EOF_START_QWEN_0_6B

cat >/opt/poc-sst-soa/bin/start_qwen_1_7b.sh <<'EOF_START_QWEN_1_7B'
${start_qwen_1_7b}
EOF_START_QWEN_1_7B

cat >/opt/poc-sst-soa/bin/start_voxtral.sh <<'EOF_START_VOXTRAL'
${start_voxtral_script}
EOF_START_VOXTRAL

cat >/opt/poc-sst-soa/bin/stop_server.sh <<'EOF_STOP_SERVER'
${stop_server_script}
EOF_STOP_SERVER

chmod +x /opt/poc-sst-soa/bin/*.sh

nvidia-smi >/opt/poc-sst-soa/logs/nvidia-smi-startup.log 2>&1 || true
docker info >/opt/poc-sst-soa/logs/docker-info-startup.log 2>&1 || true
