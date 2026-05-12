[Unit]
Description=vLLM-Omni TTS model server
After=docker.service network-online.target
Wants=network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
EnvironmentFile=-/opt/poc-sst-soa/config/runtime.env
ExecStart=/opt/poc-sst-soa/bin/start_${model_profile}.sh
ExecStop=/opt/poc-sst-soa/bin/stop_server.sh
TimeoutStartSec=1800
TimeoutStopSec=120

[Install]
WantedBy=multi-user.target
