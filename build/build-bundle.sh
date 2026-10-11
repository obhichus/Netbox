#!/usr/bin/env bash
# Spousti se na stroji S INTERNETEM (Linux s podmanem nebo dockerem).
# Postavi obraz NetBoxu s pluginem IP Fabric, stahne PostgreSQL a Valkey
# a vse zabali do jednoho archivu, ktery se prenese na offline RHEL9.
#
#   ./build/build-bundle.sh            -> dist/netbox-offline-<datum>.tar.gz
#   CTR=docker ./build/build-bundle.sh -> totez pres docker
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT=$(pwd)
# shellcheck source=../versions.env
source versions.env

CTR=${CTR:-$(command -v podman >/dev/null && echo podman || echo docker)}
STAMP=$(date +%Y%m%d)
NAME=netbox-offline-${STAMP}
OUT=dist/${NAME}
rm -rf "$OUT" && mkdir -p "$OUT/images"

echo "== stahuji zakladni obrazy (${ARCH}) pres ${CTR}"
for img in "$NETBOX_BASE_IMAGE" "$POSTGRES_IMAGE" "$VALKEY_IMAGE" "$BATFISH_IMAGE"; do
  "$CTR" pull --platform "linux/${ARCH}" "$img"
done

echo "== stavim ${NETBOX_IMAGE}"
"$CTR" build --platform "linux/${ARCH}" \
  --build-arg "NETBOX_BASE_IMAGE=${NETBOX_BASE_IMAGE}" \
  -f build/Containerfile -t "$NETBOX_IMAGE" .

echo "== kontrola, ze plugin v obrazu je"
"$CTR" run --rm --entrypoint /opt/netbox/venv/bin/python "$NETBOX_IMAGE" \
  -c "import ipfabric_netbox, netbox_branching; print('ipfabric_netbox OK')"

echo "== ukladam obrazy"
save() { # $1 obraz, $2 soubor
  if [ "$CTR" = podman ]; then
    podman save --format docker-archive -o "$OUT/images/$2" "$1"
  else
    docker save -o "$OUT/images/$2" "$1"
  fi
}
save "$NETBOX_IMAGE"  netbox.tar
save "$POSTGRES_IMAGE" postgres.tar
save "$VALKEY_IMAGE"  valkey.tar
save "$BATFISH_IMAGE" batfish.tar

echo "== kopiruji konfiguraci a skripty"
cp -r versions.env README.md configuration env quadlet deploy migrate commatrix docs "$OUT/"

( cd "$OUT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS )
tar -C dist -czf "dist/${NAME}.tar.gz" "$NAME"
sha256sum "dist/${NAME}.tar.gz" > "dist/${NAME}.tar.gz.sha256"
rm -rf "$OUT"

echo
echo "Hotovo: $ROOT/dist/${NAME}.tar.gz"
echo "Preneste na RHEL9 i se souborem .sha256 a pokracujte podle README, krok 2."
