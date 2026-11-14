#!/bin/bash
# Dice cuándo empieza la próxima falla de frío del camión CF-027 (para grabar ese momento).
# Se ejecuta en AWS CloudShell:  bash ~/cofrial/infra/scripts/proxima_falla.sh
#
# El simulador avanza un "ciclo" cada 30 s y cuenta desde que arrancó su contenedor.
# CF-027 falla en los ciclos 20 a 39 de cada bloque de 120 (minutos 10 a 20 de cada hora del simulador).
export AWS_DEFAULT_REGION=us-east-1
iot=$(aws ec2 describe-instances --filters Name=tag:Name,Values=cofrial-iot Name=instance-state-name,Values=running \
      --query 'Reservations[0].Instances[0].InstanceId' --output text)
id=$(aws ssm send-command --instance-ids "$iot" --document-name AWS-RunShellScript \
     --parameters 'commands=["docker logs --tail 1 $(docker ps -q --filter name=simulador | head -1) 2>&1"]' \
     --query Command.CommandId --output text)
sleep 4
linea=$(aws ssm get-command-invocation --command-id "$id" --instance-id "$iot" --query StandardOutputContent --output text)
ciclo=$(echo "$linea" | grep -oE 'ciclo [0-9]+' | grep -oE '[0-9]+')
if [ -z "$ciclo" ]; then echo "No pude leer el simulador. Última línea: $linea"; exit 1; fi
pos=$((ciclo % 120))
ahora=$(TZ=America/Santiago date +%s)
if [ $pos -lt 20 ]; then
    faltan=$(( (20 - pos) * 30 ))
    echo "CF-027 está bien. La falla empieza en $((faltan / 60)) min $((faltan % 60)) s, a las $(TZ=America/Santiago date -d @$((ahora + faltan)) +%H:%M)."
elif [ $pos -lt 40 ]; then
    queda=$(( (40 - pos) * 30 ))
    echo "CF-027 ESTÁ EN FALLA AHORA. El equipo de frío vuelve en $((queda / 60)) min $((queda % 60)) s."
else
    faltan=$(( (140 - pos) * 30 ))
    echo "CF-027 está bien. La próxima falla empieza en $((faltan / 60)) min, a las $(TZ=America/Santiago date -d @$((ahora + faltan)) +%H:%M)."
fi
echo "La alerta aparece en la torre 1 a 2 minutos después de que empieza la falla (dos lecturas fuera de rango)."
