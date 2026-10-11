#!/usr/bin/env bash
# Obnova ze zalohy vytvorene backup.sh nebo migrate/export-from-docker.sh.
#   sudo ./restore.sh /opt/netbox-offline/backups/20261011-021500
# POZOR: prepise vsechna data v NetBoxu.
set -euo pipefail
DIR=${1:?zadejte adresar zalohy}
[ -f "$DIR/netbox.dump" ] || { echo "v $DIR chybi netbox.dump"; exit 1; }
[ -f "$DIR/SHA256SUMS" ] && (cd "$DIR" && sha256sum --quiet -c SHA256SUMS)

read -r -p "Prepsat data NetBoxu zalohou $DIR? Napiste ANO: " ok
[ "$ok" = ANO ] || exit 1

systemctl stop netbox-worker.service netbox.service
podman exec netbox-postgres psql -q -U netbox -d postgres \
  -c "DROP DATABASE IF EXISTS netbox WITH (FORCE);" -c "CREATE DATABASE netbox OWNER netbox;"
podman exec -i netbox-postgres pg_restore -U netbox -d netbox --no-owner --role=netbox < "$DIR/netbox.dump"

systemctl start netbox.service
if [ -f "$DIR/files.tar.gz" ]; then
  podman exec -u root -i netbox tar -C /opt/netbox/netbox -xzf - < "$DIR/files.tar.gz"
  podman exec -u root netbox chown -R netbox:root /opt/netbox/netbox/media /opt/netbox/netbox/scripts /opt/netbox/netbox/reports
fi
# migrace dobehnou pri startu weboveho kontejneru (napr. pri presunu na novejsi verzi)
systemctl restart netbox.service
systemctl start netbox-worker.service
echo "Obnoveno. Prubeh startu: journalctl -fu netbox"
