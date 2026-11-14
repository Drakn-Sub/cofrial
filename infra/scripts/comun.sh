#!/bin/bash
# Funciones compartidas por los scripts de despliegue. Se ejecutan como root en los nodos.
# Ningún secreto se escribe en el repositorio: todos se leen desde Secrets Manager con LabInstanceProfile.
set -euo pipefail
export AWS_DEFAULT_REGION=us-east-1
REPO_DIR=/opt/cofrial
CONF_DIR=/etc/cofrial

secreto() {  # secreto <nombre> <clave>
    aws secretsmanager get-secret-value --secret-id "$1" --query SecretString --output text | jq -r ".$2"
}

endpoint_rds() {
    aws rds describe-db-instances --db-instance-identifier cofrial-db \
        --query 'DBInstances[0].Endpoint.Address' --output text
}

secreto_maestro_rds() {
    aws rds describe-db-instances --db-instance-identifier cofrial-db \
        --query 'DBInstances[0].MasterUserSecret.SecretArn' --output text
}

clonar_o_actualizar() {  # usa el token de solo lectura guardado en Secrets Manager (cofrial/github)
    local token rama="${1:-main}"
    token=$(secreto cofrial/github token)
    local cabecera="Authorization: Basic $(printf 'x-access-token:%s' "$token" | base64 -w0)"
    if [ -d "$REPO_DIR/.git" ]; then
        git -C "$REPO_DIR" -c http.extraHeader="$cabecera" fetch --depth 1 origin "$rama"
        git -C "$REPO_DIR" checkout -q -B "$rama" FETCH_HEAD
    else
        git -c http.extraHeader="$cabecera" clone --depth 1 --branch "$rama" https://github.com/Drakn-Sub/cofrial.git "$REPO_DIR"
    fi
    git -C "$REPO_DIR" log --oneline -1
}
