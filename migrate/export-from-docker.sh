#!/usr/bin/env bash
# Spousti se na STAVAJICIM stroji (Ubuntu, /opt/netbox-docker, docker compose).
# Vytvori archiv se vsemi daty NetBoxu, ktery se prenese na RHEL9:
#   databaze (vcetne historie zmen, behu skriptu, IP Fabric syncu),
#   media, skripty (commatrix, matice, ulozene snimky), /opt/commatrix,
#   konfigurace netbox-docker a env/netbox.env (SECRET_KEY, API pepper).
#
#   sudo ./export-from-docker.sh [/opt/netbox-docker]
set -euo pipefail
NBD=${1:-/opt/netbox-docker}
OUT=netbox-export-$(date +%Y%m%d-%H%M%S)
mkdir -p "$OUT"
cd "$NBD"

echo "== databaze"
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$OLDPWD/$OUT/netbox.dump"

echo "== media, skripty, reporty"
docker compose exec -T netbox tar -C /opt/netbox/netbox -czf - media scripts reports > "$OLDPWD/$OUT/files.tar.gz"

echo "== konfigurace"
cp env/netbox.env "$OLDPWD/$OUT/netbox.env"
tar -czf "$OLDPWD/$OUT/netbox-docker-config.tar.gz" configuration docker-compose*.yml Dockerfile* plugin_requirements.txt README.txt 2>/dev/null || true
[ -d /opt/commatrix ] && tar -C /opt -czf "$OLDPWD/$OUT/commatrix.tar.gz" commatrix

docker compose exec -T netbox /opt/netbox/venv/bin/pip freeze > "$OLDPWD/$OUT/pip-freeze.txt" 2>/dev/null \
  || docker compose exec -T netbox /usr/local/bin/uv pip list --python /opt/netbox/venv/bin/python > "$OLDPWD/$OUT/pip-freeze.txt" || true

cd "$OLDPWD/$OUT"
chmod 600 netbox.env
sha256sum ./* > SHA256SUMS
cd ..
tar -czf "$OUT.tar.gz" "$OUT" && rm -rf "$OUT"
echo
echo "Hotovo: $(pwd)/$OUT.tar.gz"
echo "Obsahuje hesla (netbox.env) - prenaset jen pres duveryhodne medium."
