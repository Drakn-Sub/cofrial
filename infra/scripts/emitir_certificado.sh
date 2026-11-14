#!/bin/bash
# Certificado comodín gratuito de Let's Encrypt validado por DNS en DuckDNS, importado a ACM.
# La llave privada se genera y se importa desde el servidor: nunca pasa por otro equipo.
#   sudo DOMINIO=cofrial-temuco.duckdns.org bash emitir_certificado.sh
source "$(dirname "$0")/comun.sh"
DOMINIO="${DOMINIO:?Define DOMINIO}"
dir="$CONF_DIR/acme"; mkdir -p "$dir" && chmod 700 "$dir"
token=$(secreto cofrial/duckdns token)
docker run --rm -v "$dir:/acme.sh" -e DuckDNS_Token="$token" neilpang/acme.sh \
    --issue --dns dns_duckdns --dnssleep 60 -d "*.$DOMINIO" --server letsencrypt --keylength 2048
c="$dir/*.$DOMINIO"
arn=$(aws acm list-certificates --query "CertificateSummaryList[?DomainName=='*.$DOMINIO'].CertificateArn | [0]" --output text)
extra=(); [ "$arn" != "None" ] && extra=(--certificate-arn "$arn")  # renovación: reemplaza el mismo certificado
aws acm import-certificate "${extra[@]}" --certificate "fileb://$c/*.$DOMINIO.cer" \
    --private-key "fileb://$c/*.$DOMINIO.key" --certificate-chain "fileb://$c/ca.cer" \
    --query CertificateArn --output text
