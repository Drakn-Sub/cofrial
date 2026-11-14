#!/bin/bash
# Prepara un nodo de aplicación: código, variables de entorno desde Secrets Manager y certificado interno.
#   sudo DOMINIO=cofrial-inacap.duckdns.org bash preparar_nodo_app.sh [rama]
source "$(dirname "$0")/comun.sh"
DOMINIO="${DOMINIO:?Define DOMINIO, por ejemplo cofrial-inacap.duckdns.org}"
mkdir -p "$CONF_DIR/certs" && chmod 700 "$CONF_DIR"

host_bd=$(endpoint_rds)
bucket=$(aws s3api list-buckets --query "Buckets[?starts_with(Name,'cofrial-media-')].Name | [0]" --output text)
app=$(aws secretsmanager get-secret-value --secret-id cofrial/app --query SecretString --output text)
umask 077
{
    echo "$app" | jq -r 'to_entries[] | select(.key != "DB_HOST") | "\(.key)=\(.value)"'
    echo "DB_HOST=$host_bd"
    echo "DB_SSLMODE=verify-full"
    echo "DB_SSLROOTCERT=/certs/rds-global-bundle.pem"
    echo "DEBUG=0"
    echo "ALLOWED_HOSTS=tienda.$DOMINIO,crm.$DOMINIO,ops.$DOMINIO,localhost"
    echo "HOST_TIENDA=tienda.$DOMINIO"
    echo "HOST_CRM=crm.$DOMINIO"
    echo "HOST_OPS=ops.$DOMINIO"
    echo "MEDIA_BUCKET=$bucket"
    echo "AWS_REGION=us-east-1"
} > "$CONF_DIR/app.env"
{
    echo "MB_DB_TYPE=postgres"
    echo "MB_DB_HOST=$host_bd"
    echo "MB_DB_PORT=5432"
    echo "MB_DB_DBNAME=metabase"
    echo "MB_DB_USER=metabase_app"
    echo "MB_DB_PASS=$(echo "$app" | jq -r .METABASE_DB_PASSWORD)"
    echo "MB_DB_CONNECTION_URI=postgres://$host_bd:5432/metabase?sslmode=require"
    echo "MB_SITE_URL=https://bi.$DOMINIO"
} > "$CONF_DIR/metabase.env"

# Certificado interno para el tramo ALB → Nginx (re-cifrado). El certificado público lo presenta el balanceador.
if [ ! -f "$CONF_DIR/certs/interno.crt" ]; then
    openssl req -x509 -newkey rsa:2048 -nodes -days 365 -subj "/CN=cofrial-interno" \
        -keyout "$CONF_DIR/certs/interno.key" -out "$CONF_DIR/certs/interno.crt" 2>/dev/null
fi
chmod 600 "$CONF_DIR/certs/interno.key"
[ -f /etc/pki/rds-global-bundle.pem ] || curl -sSo /etc/pki/rds-global-bundle.pem https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

clonar_o_actualizar "${1:-main}"
echo "Nodo preparado. Variables en $CONF_DIR (solo root). Base de datos: $host_bd"
