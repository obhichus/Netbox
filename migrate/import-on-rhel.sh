#!/usr/bin/env bash
# Spousti se na RHEL9 PO deploy/install.sh. Nahraje archiv z export-from-docker.sh.
#   sudo ./import-on-rhel.sh netbox-export-<datum>.tar.gz
set -euo pipefail
ARCH=${1:?zadejte archiv netbox-export-*.tar.gz}
DEST=/opt/netbox-offline
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
tar -C "$WORK" -xzf "$ARCH"
DIR=$(find "$WORK" -mindepth 1 -maxdepth 1 -type d | head -1)
(cd "$DIR" && sha256sum --quiet -c SHA256SUMS)

# SECRET_KEY a API_TOKEN_PEPPER_* prevezmeme ze stareho stroje, aby platily API tokeny a sezeni.
for key in SECRET_KEY $(grep -o '^API_TOKEN_PEPPER_[0-9]*' "$DIR/netbox.env"); do
  val=$(grep "^$key=" "$DIR/netbox.env" | head -1 | cut -d= -f2-)
  [ -n "$val" ] || continue
  if grep -q "^$key=" "$DEST/env/netbox.env"; then
    python3 - "$DEST/env/netbox.env" "$key" "$val" <<'PY'
import sys
p, k, v = sys.argv[1:]
lines = open(p).read().splitlines()
open(p, "w").write("\n".join(f"{k}={v}" if l.startswith(k + "=") else l for l in lines) + "\n")
PY
  else
    echo "$key=$val" >> "$DEST/env/netbox.env"
  fi
done
echo "prevzat SECRET_KEY a API pepper ze stareho stroje"

if [ -f "$DIR/commatrix.tar.gz" ]; then
  mkdir -p "$DEST/commatrix-puvodni"
  tar -C "$DEST/commatrix-puvodni" -xzf "$DIR/commatrix.tar.gz"
  echo "puvodni /opt/commatrix je v $DEST/commatrix-puvodni"
fi
cp "$DIR"/netbox-docker-config.tar.gz "$DEST/backups/" 2>/dev/null || true

"$DEST/deploy/restore.sh" "$DIR"

echo
echo "Zkontrolujte rozdily v konfiguraci proti puvodni:"
echo "  tar -tzf $DEST/backups/netbox-docker-config.tar.gz"
