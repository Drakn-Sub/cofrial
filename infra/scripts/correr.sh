#!/bin/bash
# Ejecuta un comando en un servidor de Cofrial desde CloudShell, sin SSH (usa SSM).
# Se carga una vez por sesión de CloudShell:
#
#     . ~/cofrial/infra/scripts/correr.sh
#
# Después:   correr $A 'comando'        (servidor de aplicación A)
#            correr $B 'comando'        (servidor de aplicación B)
#            correr $I 'comando' 20     (servidor IoT, muestra solo las últimas 20 líneas)
export AWS_DEFAULT_REGION=us-east-1
_id() {
    aws ec2 describe-instances --filters "Name=tag:Name,Values=$1" Name=instance-state-name,Values=running \
        --query 'Reservations[0].Instances[0].InstanceId' --output text
}
A=$(_id cofrial-app-a); B=$(_id cofrial-app-b); I=$(_id cofrial-iot)
echo "Servidores: A=$A  B=$B  IoT=$I"

correr() {  # correr <id> '<comando>' [líneas]
    local id est
    id=$(aws ssm send-command --instance-ids "$1" --document-name AWS-RunShellScript --timeout-seconds 900 \
         --parameters "$(jq -nc --arg c "$2" '{commands:[$c],executionTimeout:["900"]}')" \
         --query Command.CommandId --output text) || return 1
    while :; do
        est=$(aws ssm get-command-invocation --command-id "$id" --instance-id "$1" --query Status --output text 2>/dev/null)
        case "$est" in Pending|InProgress|Delayed|"") sleep 3 ;; *) break ;; esac
    done
    aws ssm get-command-invocation --command-id "$id" --instance-id "$1" \
        --query '[StandardOutputContent,StandardErrorContent]' --output text | tail -n "${3:-40}"
    echo "($est)"
}
