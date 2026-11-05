#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
[[ ${EUID} -eq 0 ]] || { echo 'Ejecuta: sudo bash update.sh'; exit 1; }
[[ -d .git ]] || { echo 'No hay repositorio Git. Clona el repositorio antes de usar este script.'; exit 1; }
repo_owner=$(stat -c %U .git)
git_repo() { runuser -u "$repo_owner" -- git -C "$PWD" "$@"; }
[[ -z $(git_repo status --porcelain --untracked-files=normal) ]] || { echo 'Hay cambios locales. Revísalos antes de actualizar.'; exit 1; }
umask 077
mkdir -p backups
stamp=$(date -u +%Y%m%dT%H%M%SZ)
# Detener antes de copiar SQLite y evitar una copia incoherente de WAL/documentos.
docker compose stop
restart_on_error() { docker compose up -d || true; }
trap restart_on_error ERR
cp .env "backups/env-${stamp}"
docker compose run --rm --no-deps -T --entrypoint python transcribe -c \
  'import sys,tarfile; t=tarfile.open(fileobj=sys.stdout.buffer,mode="w|gz"); t.add("/data",arcname="data"); t.close()' > "backups/data-${stamp}.tar.gz"
git_repo rev-parse HEAD > "backups/commit-${stamp}"
# Nunca fuerza ni borra cambios, nunca elimina volúmenes.
git_repo pull --ff-only
docker compose config --quiet
docker compose build
docker compose up -d --wait --wait-timeout 240
trap - ERR
echo "Actualizado. Copia privada en backups/${stamp} (datos, configuración y commit)."
