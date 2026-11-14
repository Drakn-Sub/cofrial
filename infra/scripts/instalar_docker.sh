#!/bin/bash
# Arranque de un servidor Amazon Linux 2023 (user data): Docker, Compose, Buildx y la CA de RDS.
set -euo pipefail
dnf update -y
dnf install -y docker git jq
systemctl enable --now docker
mkdir -p /usr/local/lib/docker/cli-plugins
curl -sSL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
version=$(curl -sI https://github.com/docker/buildx/releases/latest | grep -i '^location' | sed 's#.*/tag/##' | tr -d '\r')
curl -sSL "https://github.com/docker/buildx/releases/download/${version}/buildx-${version}.linux-amd64" \
    -o /usr/local/lib/docker/cli-plugins/docker-buildx
chmod +x /usr/local/lib/docker/cli-plugins/docker-*
curl -sSo /etc/pki/rds-global-bundle.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
docker compose version && docker buildx version
