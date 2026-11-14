#!/bin/bash
# Construye y levanta los contenedores. Con --migrar aplica migraciones con el rol cofrial_migrate
# (Django en operación usa cofrial_app, que no puede crear ni borrar tablas).
#   sudo bash desplegar_app.sh [--migrar] [--bi]
source "$(dirname "$0")/comun.sh"
cd "$REPO_DIR/infra"
perfiles=""
for arg in "$@"; do [ "$arg" = "--bi" ] && perfiles="--profile bi"; done
docker compose -f compose.app.yml $perfiles build --pull
if [[ " $* " == *" --migrar "* ]]; then
    docker compose -f compose.app.yml run --rm django sh -c \
        'DB_USER=$MIGRATE_USER DB_PASSWORD=$MIGRATE_PASSWORD python manage.py migrate --noinput && \
         DB_USER=$MIGRATE_USER DB_PASSWORD=$MIGRATE_PASSWORD python manage.py oscar_populate_countries --no-shipping || true'
fi
docker compose -f compose.app.yml $perfiles up -d --remove-orphans
sleep 5
docker compose -f compose.app.yml ps
curl -sk https://localhost/salud/ && echo
