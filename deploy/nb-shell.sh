#!/usr/bin/env bash
# Spusti Python soubor v NetBox shellu (nahrada za "docker compose exec -T netbox manage.py shell < soubor").
#   ./nb-shell.sh /opt/commatrix/primarni_ip.py
#   ./nb-shell.sh /opt/commatrix/push_ipf_data.py IPF_SNAPSHOT=22443e66-2430-4a55-b953-d7601b3f5148
#   ./nb-shell.sh /opt/commatrix/push_ipf_data.py IPF_LOAD_DIR=/opt/netbox/netbox/scripts/snapshot-22443e66
set -euo pipefail
f=${1:?zadejte soubor .py}; shift
envs=()
for kv in "$@"; do envs+=(-e "$kv"); done
exec podman exec -i "${envs[@]}" netbox /opt/netbox/netbox/manage.py shell < "$f"
