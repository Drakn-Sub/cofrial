#!/bin/bash
# Prepara CloudShell la primera vez (o si se borró la carpeta ~/cofrial): descarga el repositorio
# usando el token de solo lectura guardado en Secrets Manager. El token no queda escrito en ningún archivo.
# No hace falta copiar este archivo: el bloque de comandos equivalente está en la guía de operación.
export AWS_DEFAULT_REGION=us-east-1
TK=$(aws secretsmanager get-secret-value --secret-id cofrial/github --query SecretString --output text | jq -r .token)
H="Authorization: Basic $(printf 'x-access-token:%s' "$TK" | base64 -w0)"; unset TK
if [ -d ~/cofrial/.git ]; then git -C ~/cofrial -c http.extraHeader="$H" pull -q
else git -c http.extraHeader="$H" clone -q --depth 1 https://github.com/Drakn-Sub/cofrial.git ~/cofrial; fi
unset H
git -C ~/cofrial log --oneline -1
