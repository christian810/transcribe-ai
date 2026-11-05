#!/usr/bin/env bash
set -Eeuo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
umask 077
if [[ ${EUID} -ne 0 ]]; then
  echo 'Ejecuta: sudo bash install.sh'; exit 1
fi
. /etc/os-release
[[ ${ID} == ubuntu ]] || { echo 'Este instalador requiere Ubuntu Server.'; exit 1; }
case "${VERSION_ID}" in 24.04|26.04) ;; *) echo "Versión ${VERSION_ID} no validada por este instalador; utiliza Docker Compose manualmente."; exit 1;; esac
for cmd in python3 curl; do
  if ! command -v "$cmd" >/dev/null; then
    apt-get update
    apt-get install -y python3 curl ca-certificates
    break
  fi
done
if ! command -v docker >/dev/null; then
  # No quitar paquetes ni reemplazar motores existentes automáticamente.
  for package in docker.io docker-compose docker-compose-v2 podman-docker containerd runc; do
    if dpkg-query -W -f='${Status}' "$package" 2>/dev/null | grep -q 'install ok installed'; then
      echo "Paquete existente ${package}. Revisa la migración de Docker antes de continuar."; exit 1
    fi
  done
  apt-get update
  apt-get install -y ca-certificates curl
  install -m 0755 -d /etc/apt/keyrings
  curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
    https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  arch=$(dpkg --print-architecture)
  cat > /etc/apt/sources.list.d/docker.sources <<SOURCES
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-${VERSION_CODENAME}}
Components: stable
Architectures: ${arch}
Signed-By: /etc/apt/keyrings/docker.asc
SOURCES
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
docker compose version >/dev/null || { echo 'Falta Docker Compose v2. Instálalo para tu motor de Docker existente.'; exit 1; }
systemctl enable --now docker
if [[ ! -f .env ]]; then cp .env.example .env; fi
python3 - <<'PY'
from pathlib import Path
import secrets
p = Path('.env')
s = p.read_text()
if 'APP_PASSWORD=\n' in s:
    s = s.replace('APP_PASSWORD=\n', 'APP_PASSWORD=' + secrets.token_urlsafe(24) + '\n')
p.write_text(s)
p.chmod(0o600)
PY
# Validar sin mostrar la configuración resuelta, que contiene secretos.
docker compose config --quiet
available_kb=$(df --output=avail . | tail -1)
[[ ${available_kb// /} -ge 10485760 ]] || { echo 'Se necesitan al menos 10 GiB libres para imagen, modelos y trabajos.'; exit 1; }
echo 'Construyendo y desplegando Transcribe AI…'
docker compose up -d --build --wait --wait-timeout 240
echo 'Servicio preparado en http://127.0.0.1:8000 mediante túnel SSH de PuTTY.'
echo 'Para consultar usuario y contraseña en esta terminal: sudo cat .env'
echo 'El primer audio descargará el modelo. No se necesita escritorio gráfico.'
