#!/bin/bash
# Crea esquemas y roles en RDS (una sola vez). La contraseña maestra la gestiona RDS en Secrets Manager:
# este script la lee y se la pasa a psql por variable de entorno, sin mostrarla ni guardarla.
source "$(dirname "$0")/comun.sh"
host_bd=$(endpoint_rds)
maestro=$(aws secretsmanager get-secret-value --secret-id "$(secreto_maestro_rds)" --query SecretString --output text)
app=$(aws secretsmanager get-secret-value --secret-id cofrial/app --query SecretString --output text)
iot=$(aws secretsmanager get-secret-value --secret-id cofrial/iot --query SecretString --output text)

docker run --rm -i \
    -e PGPASSWORD="$(echo "$maestro" | jq -r .password)" \
    -v "$REPO_DIR/infra/sql:/sql:ro" -v /etc/pki/rds-global-bundle.pem:/ca.pem:ro \
    public.ecr.aws/docker/library/postgres:16 psql \
    "host=$host_bd dbname=cofrial user=$(echo "$maestro" | jq -r .username) sslmode=verify-full sslrootcert=/ca.pem" \
    -v ON_ERROR_STOP=1 \
    -v pw_migrate="$(echo "$app" | jq -r .MIGRATE_PASSWORD)" \
    -v pw_app="$(echo "$app" | jq -r .DB_PASSWORD)" \
    -v pw_bi="$(echo "$app" | jq -r .BI_PASSWORD)" \
    -v pw_metabase="$(echo "$app" | jq -r .METABASE_DB_PASSWORD)" \
    -v pw_iot="$(echo "$iot" | jq -r .DB_PASSWORD)" \
    -f /sql/01_roles.sql
echo "Esquemas y roles creados en $host_bd"
