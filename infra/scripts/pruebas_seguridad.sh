#!/bin/bash
# Pruebas de seguridad de Cofrial desde fuera (AWS CloudShell): sitio público y configuración de AWS.
# No necesita contraseñas: usa solo lo que ve un visitante y lecturas de la API de AWS.
#   bash pruebas_seguridad.sh [dominio]
D="${1:-cofrial-temuco.duckdns.org}"
T="tienda.$D"; C="crm.$D"
export AWS_DEFAULT_REGION=us-east-1
pasa=0; falla=0
prueba() {  # prueba "<descripción>" <0=pasa> "<detalle>"
    if [ "$2" = 0 ]; then printf '  \033[32m✔ PASA \033[0m %-52s %s\n' "$1" "$3"; pasa=$((pasa+1))
    else printf '  \033[31m✘ FALLA\033[0m %-52s %s\n' "$1" "$3"; falla=$((falla+1)); fi
}
codigo() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
si() { "$@" >/dev/null 2>&1 && echo 0 || echo 1; }

echo "== 1. Cifrado y cabeceras ($T)"
c=$(codigo "http://$T/"); prueba "HTTP redirige a HTTPS" "$([ "$c" = 301 ] && echo 0 || echo 1)" "http -> $c"
v=$(curl -s -o /dev/null -w '%{ssl_verify_result}' "https://$T/"); prueba "Certificado TLS válido (Let's Encrypt en ACM)" "$v" "verify=$v"
p=$(openssl s_client -connect "$T:443" -servername "$T" </dev/null 2>/dev/null | grep -m1 -oE 'TLSv1\.[0-9]')
prueba "Protocolo TLS 1.2 o superior" "$([[ "$p" =~ TLSv1\.[23] ]] && echo 0 || echo 1)" "$p"
h=$(curl -sI "https://$T/")
prueba "HSTS (Strict-Transport-Security)" "$(echo "$h" | grep -qi '^strict-transport-security: max-age=31536000' && echo 0 || echo 1)" "1 año + preload"
prueba "Anti-clickjacking (X-Frame-Options DENY)" "$(echo "$h" | grep -qi '^x-frame-options: deny' && echo 0 || echo 1)" ""
prueba "X-Content-Type-Options nosniff" "$(echo "$h" | grep -qi '^x-content-type-options: nosniff' && echo 0 || echo 1)" ""
s=$(echo "$h" | grep -i '^server:' | tr -d '\r')
prueba "El servidor no revela su versión" "$(echo "$s" | grep -qE '[0-9]+\.[0-9]+' && echo 1 || echo 0)" "${s:-sin cabecera Server}"
k=$(curl -sI "https://$T/accounts/login/" | grep -i '^set-cookie: csrftoken')
prueba "Cookies solo por HTTPS (Secure, SameSite)" "$(echo "$k" | grep -qi 'secure' && echo "$k" | grep -qi 'samesite=lax' && echo 0 || echo 1)" ""

echo "== 2. Superficie de ataque"
for ruta in /admin/ /dashboard/ /crm/ /ops/; do
    c=$(codigo "https://$T$ruta"); prueba "Ruta interna $ruta no existe en la tienda" "$([ "$c" = 404 ] && echo 0 || echo 1)" "$c"
done
c=$(codigo "https://$C/crm/"); prueba "CRM exige iniciar sesión" "$([ "$c" = 302 ] && echo 0 || echo 1)" "$c -> login"
c=$(codigo "https://$T/.env"); prueba "Archivos ocultos (.env) no expuestos" "$([ "$c" = 404 ] && echo 0 || echo 1)" "$c"

echo "== 3. Fuerza bruta en el inicio de sesión"
jar=$(mktemp); curl -s -c "$jar" -o /dev/null "https://$T/accounts/login/"
tok=$(awk '/csrftoken/{print $7}' "$jar"); codigos=""
for i in $(seq 1 8); do
    codigos+="$(curl -s -b "$jar" -o /dev/null -w '%{http_code}' -e "https://$T/accounts/login/" \
        --data-urlencode "csrfmiddlewaretoken=$tok" --data-urlencode "login-username=atacante@demo.cl" \
        --data-urlencode "login-password=clave-incorrecta-$i" -d "login_submit=1" "https://$T/accounts/login/") "
done
rm -f "$jar"
prueba "8 intentos seguidos terminan bloqueados" "$(echo "$codigos" | grep -qE '429|403' && echo 0 || echo 1)" "códigos: $codigos"

echo "== 4. Configuración de AWS"
q() { aws ec2 describe-instances --filters "Name=tag:Name,Values=cofrial-app-a,cofrial-app-b,cofrial-iot" \
      Name=instance-state-name,Values=running --query "$1" --output text; }
ips=$(q 'Reservations[].Instances[].PublicIpAddress'); prueba "Servidores sin IP pública" "$([ -z "$ips" ] && echo 0 || echo 1)" "${ips:-ninguna}"
tk=$(q 'Reservations[].Instances[].MetadataOptions.HttpTokens' | tr '\t' ' ')
prueba "IMDSv2 obligatorio (anti-SSRF)" "$(echo "$tk" | grep -qv optional && [ -n "$tk" ] && echo 0 || echo 1)" "$tk"
vols=$(q 'Reservations[].Instances[].BlockDeviceMappings[].Ebs.VolumeId')
enc=$(aws ec2 describe-volumes --volume-ids $vols --query 'Volumes[].Encrypted' --output text | tr '\t' ' ')
prueba "Discos EBS cifrados" "$(echo "$enc" | grep -q False && echo 1 || echo 0)" "$enc"
llaves=$(q 'Reservations[].Instances[].KeyName'); prueba "Sin llaves SSH en los servidores (acceso por SSM)" "$([ -z "$llaves" ] || [ "$llaves" = None ] && echo 0 || echo 1)" "${llaves:-ninguna}"
ssh=$(aws ec2 describe-security-groups --filters Name=ip-permission.from-port,Values=22 Name=ip-permission.cidr,Values=0.0.0.0/0 \
      --query 'SecurityGroups[].GroupName' --output text)
prueba "Ningún Security Group con SSH abierto a internet" "$([ -z "$ssh" ] && echo 0 || echo 1)" "${ssh:-ninguno}"
r=$(aws rds describe-db-instances --db-instance-identifier cofrial-db \
    --query 'DBInstances[0].[PubliclyAccessible,StorageEncrypted,MultiAZ,BackupRetentionPeriod,DeletionProtection]' --output text)
read -r pub cif multi resp _ <<< "$r"
prueba "RDS no accesible desde internet" "$([ "$pub" = False ] && echo 0 || echo 1)" "PubliclyAccessible=$pub"
prueba "RDS cifrada y Multi-AZ" "$([ "$cif" = True ] && [ "$multi" = True ] && echo 0 || echo 1)" "cifrada=$cif multiAZ=$multi"
prueba "Respaldos automáticos de RDS" "$([ "${resp:-0}" -ge 7 ] && echo 0 || echo 1)" "$resp días"
b=$(aws s3api list-buckets --query "Buckets[?starts_with(Name,'cofrial-media-')].Name | [0]" --output text)
pab=$(aws s3api get-public-access-block --bucket "$b" --query 'PublicAccessBlockConfiguration.[BlockPublicAcls,IgnorePublicAcls,BlockPublicPolicy,RestrictPublicBuckets]' --output text)
prueba "S3: bloqueo de acceso público completo" "$(echo "$pab" | grep -q False && echo 1 || echo 0)" "$b"
prueba "S3: rechaza conexiones sin TLS (política)" "$(si sh -c "aws s3api get-bucket-policy --bucket $b --output text | grep -q SecureTransport")" ""
c=$(codigo "https://$b.s3.amazonaws.com/image_not_found.jpg"); prueba "S3: archivo sin URL firmada -> denegado" "$([ "$c" = 403 ] && echo 0 || echo 1)" "$c"
n=$(aws secretsmanager list-secrets --query "length(SecretList[?starts_with(Name,'cofrial/') || starts_with(Name,'rds!')])" --output text)
prueba "Credenciales en Secrets Manager (no en el código)" "$([ "${n:-0}" -ge 4 ] && echo 0 || echo 1)" "$n secretos"
nacl=$(aws ec2 describe-network-acls --filters Name=tag:Name,Values=cofrial-nacl-datos --query 'length(NetworkAcls[0].Associations)' --output text)
prueba "NACL restrictiva en subredes de datos" "$([ "$nacl" = 2 ] && echo 0 || echo 1)" "$nacl subredes asociadas"
viejos=$(aws ec2 describe-instances --filters Name=tag:Estado,Values=reemplazado-auditoria-H2-H3 --query 'Reservations[].Instances[].State.Name' --output text | tr '\t' ' ')
prueba "Servidores inseguros de la auditoría detenidos" "$(echo "$viejos" | grep -q running && echo 1 || echo 0)" "$viejos"

echo
echo "Resultado: $pasa pruebas pasan, $falla fallan  ($(date '+%d-%m-%Y %H:%M'))"
