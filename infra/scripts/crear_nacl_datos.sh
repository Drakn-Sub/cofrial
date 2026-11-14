#!/bin/bash
# NACL de las subredes de datos (defensa en profundidad, además de los Security Groups).
# Solo deja entrar PostgreSQL (5432) desde las subredes de aplicación e IoT, y el tráfico
# entre las dos subredes de datos (replicación Multi-AZ de RDS). Todo lo demás se rechaza.
#   sudo bash crear_nacl_datos.sh          (idempotente)
#   sudo bash crear_nacl_datos.sh --revertir  (vuelve a la NACL por defecto de la VPC)
source "$(dirname "$0")/comun.sh"

vpc=$(aws ec2 describe-vpcs --filters Name=cidr,Values=10.20.0.0/16 --query 'Vpcs[0].VpcId' --output text)
subredes_datos=$(aws ec2 describe-subnets --filters Name=vpc-id,Values="$vpc" Name=cidr-block,Values=10.20.21.0/24,10.20.22.0/24 \
    --query 'Subnets[].SubnetId' --output text)

asociar() {  # asociar <nacl-id>: mueve cada subred de datos a esa NACL
    for subred in $subredes_datos; do
        asociacion=$(aws ec2 describe-network-acls --filters Name=association.subnet-id,Values="$subred" \
            --query "NetworkAcls[0].Associations[?SubnetId=='$subred'].NetworkAclAssociationId | [0]" --output text)
        aws ec2 replace-network-acl-association --association-id "$asociacion" --network-acl-id "$1" >/dev/null
        echo "  $subred -> $1"
    done
}

if [ "${1:-}" = "--revertir" ]; then
    asociar "$(aws ec2 describe-network-acls --filters Name=vpc-id,Values="$vpc" Name=default,Values=true \
        --query 'NetworkAcls[0].NetworkAclId' --output text)"
    exit 0
fi

nacl=$(aws ec2 describe-network-acls --filters Name=vpc-id,Values="$vpc" Name=tag:Name,Values=cofrial-nacl-datos \
    --query 'NetworkAcls[0].NetworkAclId' --output text)
if [ "$nacl" = "None" ]; then
    nacl=$(aws ec2 create-network-acl --vpc-id "$vpc" --query NetworkAcl.NetworkAclId --output text \
        --tag-specifications 'ResourceType=network-acl,Tags=[{Key=Name,Value=cofrial-nacl-datos},{Key=Proyecto,Value=cofrial}]')
    regla() {  # regla <in|out> <número> <protocolo> <desde> <hasta> <cidr>
        local sentido=--ingress
        [ "$1" = out ] && sentido=--egress
        if [ "$3" = "-1" ]; then
            aws ec2 create-network-acl-entry --network-acl-id "$nacl" $sentido --rule-number "$2" \
                --protocol -1 --cidr-block "$6" --rule-action allow
        else
            aws ec2 create-network-acl-entry --network-acl-id "$nacl" $sentido --rule-number "$2" \
                --protocol "$3" --port-range "From=$4,To=$5" --cidr-block "$6" --rule-action allow
        fi
    }
    # Entrada: PostgreSQL solo desde aplicación (a/b) e IoT; todo entre subredes de datos (replicación)
    regla in 100 6 5432 5432 10.20.11.0/24
    regla in 110 6 5432 5432 10.20.12.0/24
    regla in 120 6 5432 5432 10.20.31.0/24
    regla in 130 -1 0 0 10.20.21.0/24
    regla in 140 -1 0 0 10.20.22.0/24
    # Salida: respuestas (puertos efímeros) solo hacia esas mismas subredes
    regla out 100 6 1024 65535 10.20.11.0/24
    regla out 110 6 1024 65535 10.20.12.0/24
    regla out 120 6 1024 65535 10.20.31.0/24
    regla out 130 -1 0 0 10.20.21.0/24
    regla out 140 -1 0 0 10.20.22.0/24
    echo "NACL creada: $nacl"
fi
asociar "$nacl"
aws ec2 describe-network-acls --network-acl-ids "$nacl" \
    --query 'NetworkAcls[0].Entries[].[Egress,RuleNumber,RuleAction,Protocol,CidrBlock,PortRange.From,PortRange.To]' --output table
