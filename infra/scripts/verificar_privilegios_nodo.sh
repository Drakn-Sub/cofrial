#!/bin/bash
# Ejecuta verificar_privilegios.py contra RDS desde un nodo de aplicación (evidencia de mínimo privilegio).
# Las contraseñas se leen de /etc/cofrial/app.env y de Secrets Manager; nunca se imprimen.
#   sudo bash verificar_privilegios_nodo.sh
source "$(dirname "$0")/comun.sh"
valor() { grep "^$1=" "$CONF_DIR/app.env" | cut -d= -f2-; }
PW_APP=$(valor DB_PASSWORD) PW_BI=$(valor BI_PASSWORD) PW_IOT=$(secreto cofrial/iot DB_PASSWORD) \
docker run --rm -e PW_APP -e PW_BI -e PW_IOT \
    -e DB_HOST="$(endpoint_rds)" -e DB_SSLMODE=verify-full -e DB_SSLROOTCERT=/certs/rds-global-bundle.pem \
    -v /etc/pki/rds-global-bundle.pem:/certs/rds-global-bundle.pem:ro \
    -v "$REPO_DIR/infra/scripts/verificar_privilegios.py:/verificar_privilegios.py:ro" \
    --entrypoint python cofrial-django:local /verificar_privilegios.py
