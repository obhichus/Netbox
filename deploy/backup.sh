#!/usr/bin/env bash
# Zaloha: databaze + media + skripty do /opt/netbox-offline/backups/<datum>/
# Do cronu napr.:  15 2 * * * root /opt/netbox-offline/deploy/backup.sh
set -euo pipefail
DIR=/opt/netbox-offline/backups/$(date +%Y%m%d-%H%M%S)
mkdir -p "$DIR"
podman exec netbox-postgres pg_dump -U netbox -d netbox -Fc > "$DIR/netbox.dump"
podman exec netbox tar -C /opt/netbox/netbox -czf - media scripts reports > "$DIR/files.tar.gz"
cp /opt/netbox-offline/env/netbox.env "$DIR/netbox.env" && chmod 600 "$DIR/netbox.env"
( cd "$DIR" && sha256sum netbox.dump files.tar.gz > SHA256SUMS )
echo "zaloha: $DIR ($(du -sh "$DIR" | cut -f1))"
# drzet poslednich 14 zaloh
ls -1dt /opt/netbox-offline/backups/*/ | tail -n +15 | xargs -r rm -rf
