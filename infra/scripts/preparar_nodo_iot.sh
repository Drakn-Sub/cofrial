#!/bin/bash
# Prepara y levanta el simulador IoT con el rol iot_ingest.
#   sudo bash preparar_nodo_iot.sh [rama]
source "$(dirname "$0")/comun.sh"
mkdir -p "$CONF_DIR" && chmod 700 "$CONF_DIR"
umask 077
aws secretsmanager get-secret-value --secret-id cofrial/iot --query SecretString --output text \
    | jq -r 'to_entries[] | select(.key != "DB_HOST") | "\(.key)=\(.value)"' > "$CONF_DIR/iot.env"
echo "DB_HOST=$(endpoint_rds)" >> "$CONF_DIR/iot.env"
[ -f /etc/pki/rds-global-bundle.pem ] || curl -sSo /etc/pki/rds-global-bundle.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem
clonar_o_actualizar "${1:-main}"
cd "$REPO_DIR/infra" && docker compose -f compose.iot.yml up -d --build
sleep 8 && docker compose -f compose.iot.yml logs --tail 5 simulador
