#!/bin/bash
# Levanta y revisa todo Cofrial con un solo comando. Se ejecuta en AWS CloudShell:
#
#     bash ~/cofrial/infra/scripts/levantar.sh
#
# Qué hace, en orden:
#   1. Revisa que las credenciales del laboratorio estén vigentes.
#   2. Enciende los 3 servidores (app-a, app-b, iot) si están apagados.
#   3. Enciende la base de datos RDS si está detenida y espera a que esté disponible.
#   4. Detiene los 2 servidores viejos de la auditoría (AWS Academy los enciende al iniciar el lab).
#   5. Levanta los contenedores en cada servidor y revisa que respondan.
#   6. Corre las 29 pruebas de seguridad y dice cuándo falla el camión CF-027.
# Se puede ejecutar las veces que se quiera: si algo ya está bien, no lo toca.
export AWS_DEFAULT_REGION=us-east-1
AQUI="$(cd "$(dirname "$0")" && pwd)"
ok()   { printf '  \033[32m✔\033[0m %s\n' "$1"; }
mal()  { printf '  \033[31m✘\033[0m %s\n' "$1"; }
paso() { printf '\n\033[1m%s\033[0m\n' "$1"; }

ssm() {  # ssm <id-instancia> "<comando>"  → imprime la salida
    local id est
    id=$(aws ssm send-command --instance-ids "$1" --document-name AWS-RunShellScript --timeout-seconds 900 \
         --parameters "$(jq -nc --arg c "$2" '{commands:[$c],executionTimeout:["900"]}')" \
         --query Command.CommandId --output text 2>/dev/null) || { echo "(no se pudo enviar el comando)"; return 1; }
    for _ in $(seq 1 180); do
        est=$(aws ssm get-command-invocation --command-id "$id" --instance-id "$1" --query Status --output text 2>/dev/null)
        case "$est" in Pending|InProgress|Delayed|"") sleep 5 ;; *) break ;; esac
    done
    aws ssm get-command-invocation --command-id "$id" --instance-id "$1" \
        --query '[StandardOutputContent,StandardErrorContent]' --output text 2>/dev/null
}
instancia() {
    aws ec2 describe-instances --filters "Name=tag:Name,Values=$1" "Name=instance-state-name,Values=pending,running,stopping,stopped" \
        --query 'Reservations[0].Instances[0].[InstanceId,State.Name]' --output text
}

paso "1. Credenciales del laboratorio"
if ! quien=$(aws sts get-caller-identity --query Arn --output text 2>/dev/null) || \
   ! aws ec2 describe-instances --max-items 1 >/dev/null 2>&1; then
    mal "Las credenciales no sirven. Inicia el laboratorio (Start Lab), entra a la consola con el botón AWS"
    mal "y reinicia CloudShell (Acciones → Reiniciar). Después vuelve a ejecutar este script."
    exit 1
fi
ok "Conectado como ${quien##*/}"

paso "2. Servidores"
declare -A ID
for nombre in cofrial-app-a cofrial-app-b cofrial-iot; do
    read -r id estado <<< "$(instancia $nombre)"
    ID[$nombre]=$id
    if [ "$estado" = "stopped" ]; then
        aws ec2 start-instances --instance-ids "$id" >/dev/null && ok "$nombre: encendiendo..."
    else
        ok "$nombre: $estado"
    fi
done
aws ec2 wait instance-running --instance-ids "${ID[cofrial-app-a]}" "${ID[cofrial-app-b]}" "${ID[cofrial-iot]}"
ok "Los 3 servidores están encendidos"

paso "3. Base de datos RDS"
estado=$(aws rds describe-db-instances --db-instance-identifier cofrial-db --query 'DBInstances[0].DBInstanceStatus' --output text)
if [ "$estado" = "stopped" ]; then
    aws rds start-db-instance --db-instance-identifier cofrial-db >/dev/null
    ok "Encendiendo la base de datos (puede tardar hasta 10 minutos)..."
fi
if [ "$estado" != "available" ]; then
    aws rds wait db-instance-available --db-instance-identifier cofrial-db && ok "Base de datos disponible" || mal "La base de datos no quedó disponible ($estado)"
else
    ok "Base de datos disponible"
fi

paso "4. Servidores viejos de la auditoría"
viejos=$(aws ec2 describe-instances --filters Name=tag:Estado,Values=reemplazado-auditoria-H2-H3 Name=instance-state-name,Values=pending,running \
         --query 'Reservations[].Instances[].InstanceId' --output text)
if [ -n "$viejos" ]; then
    aws ec2 stop-instances --instance-ids $viejos >/dev/null && ok "Estaban encendidos: los detuve ($viejos)"
else
    ok "Están detenidos, como corresponde"
fi

paso "5. Aplicación y sensores"
printf '  Esperando a que los servidores acepten comandos'
for _ in $(seq 1 36); do
    en_linea=$(aws ssm describe-instance-information --query "length(InstanceInformationList[?PingStatus=='Online'])" --output text 2>/dev/null)
    [ "${en_linea:-0}" -ge 3 ] && break; printf '.'; sleep 5
done; echo
for nombre in cofrial-app-a cofrial-app-b; do
    salida=$(ssm "${ID[$nombre]}" 'cd /opt/cofrial/infra && docker compose -f compose.app.yml --profile bi up -d >/dev/null 2>&1; sleep 8; curl -sk https://localhost/salud/')
    if echo "$salida" | grep -q '"ok"'; then ok "$nombre: tienda, CRM, torre y Metabase funcionando"; else mal "$nombre: no responde. Salida: $(echo "$salida" | tail -2)"; fi
done
salida=$(ssm "${ID[cofrial-iot]}" 'cd /opt/cofrial/infra && docker compose -f compose.iot.yml up -d >/dev/null 2>&1; sleep 35; docker logs --tail 1 $(docker ps -q --filter name=simulador | head -1) 2>&1')
if echo "$salida" | grep -q 'lecturas'; then ok "Simulador IoT: $(echo "$salida" | grep -oE 'ciclo [0-9]+: .*' | tail -1)"; else mal "Simulador IoT sin lecturas. Salida: $(echo "$salida" | tail -2)"; fi

paso "6. Pruebas de seguridad"
bash "$AQUI/pruebas_seguridad.sh" | tail -1

paso "7. Próxima falla del camión CF-027 (para grabar)"
bash "$AQUI/proxima_falla.sh"

paso "Listo. Direcciones:"
echo "  Tienda:    https://tienda.cofrial-temuco.duckdns.org"
echo "  Intranet:  https://crm.cofrial-temuco.duckdns.org"
echo "  Metabase:  https://bi.cofrial-temuco.duckdns.org/dashboard/2"
