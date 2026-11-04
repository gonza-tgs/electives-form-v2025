#!/usr/bin/env bash
# Descarga un backup de la base de electivos desde la VPS a esta cuenta.
# Después hay que subirlo a mano al Drive del colegio: contiene datos de estudiantes.
#
# Uso: scripts/descargar_backup.sh [carpeta]    (por defecto ~/backups/electivos)
#
# Para restaurar en un Postgres 17 vacío, con una base "electivos" ya creada:
#   CREATE ROLE electivos_owner NOLOGIN;
#   CREATE ROLE electivos_app NOLOGIN;
#   pg_restore -U electivos -d electivos --exit-on-error < archivo.dump
#   ALTER ROLE electivos_app LOGIN PASSWORD '...';
set -euo pipefail

VPS=root@gonz4-vps
SERVICE=electivos-db-xtr5q3
DIR="${1:-$HOME/backups/electivos}"
FILE="$DIR/electivos-$(date +%Y%m%d-%H%M).dump"

umask 077
mkdir -p "$DIR"

ssh "$VPS" "docker exec \$(docker ps -q --filter name=$SERVICE) pg_dump -U electivos -d electivos -Fc" > "$FILE.tmp"

# Un archivo truncado o corrupto no se puede listar: falla aquí y no queda como backup válido.
TABLAS=$(ssh "$VPS" "docker exec -i \$(docker ps -q --filter name=$SERVICE) pg_restore --list" < "$FILE.tmp" | grep -c ' TABLE DATA public ')
[ "$TABLAS" -eq 6 ] || { echo "Backup inválido: $TABLAS tablas con datos, se esperaban 6. Quedó en $FILE.tmp" >&2; exit 1; }

mv "$FILE.tmp" "$FILE"
echo "Backup listo: $FILE ($(du -h "$FILE" | cut -f1), $TABLAS tablas)"
