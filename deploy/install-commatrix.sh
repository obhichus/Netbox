#!/usr/bin/env bash
# Nahraje NetBox skripty a matice z /opt/netbox-offline/commatrix do NetBoxu
# (svazek netbox-scripts je spolecny pro web i worker) a zaregistruje je.
# Spoustet znovu po kazde zmene skriptu nebo matice.
set -euo pipefail
SRC=${1:-/opt/netbox-offline/commatrix}

# Jen tyto soubory jsou NetBox Scripts (Customization -> Scripts).
# Ostatni .py jsou nastroje pro hostitele nebo pro manage.py shell.
NETBOX_SCRIPTS="commatrix_v2.py commatrix_script.py fw_prehled_script.py"

shopt -s nullglob
for f in $NETBOX_SCRIPTS; do
  [ -f "$SRC/$f" ] && podman cp "$SRC/$f" "netbox:/opt/netbox/netbox/scripts/$f"
done
for f in "$SRC"/*.csv; do
  podman cp "$f" "netbox:/opt/netbox/netbox/scripts/$(basename "$f")"
done
# Vlastnikem musi byt netbox, jinak skript skonci na PermissionError.
podman exec -u root netbox chown -R netbox:root /opt/netbox/netbox/scripts

# Skripty v NetBoxu 4.x musi mit zaznam ScriptModule; vytvori se jen chybejici.
podman exec -i -e MODS="$NETBOX_SCRIPTS" netbox /opt/netbox/netbox/manage.py shell <<'PY'
import os
from extras.models import ScriptModule
for name in os.environ["MODS"].split():
    if not os.path.exists(f"/opt/netbox/netbox/scripts/{name}"):
        continue
    m, created = ScriptModule.objects.get_or_create(file_root="scripts", file_path=name)
    if not created:
        m.save()
    print(("zaregistrovan" if created else "aktualizovan"), name, "->", [s.name for s in m.scripts.all()])
PY

# Worker si drzi nactene moduly; bez restartu by bezela stara verze skriptu.
systemctl restart netbox.service netbox-worker.service
echo "Hotovo. Skripty: Customization -> Scripts. Matice: /opt/netbox/netbox/scripts/<soubor>.csv"
