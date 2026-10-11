#!/usr/bin/env bash
# Spousti se na stroji S INTERNETEM (Linux s podmanem nebo dockerem).
# Postavi obraz NetBoxu s pluginem IP Fabric, stahne PostgreSQL a Valkey
# a vse zabali do jednoho archivu, ktery se prenese na offline RHEL9.
#
#   ./build/build-bundle.sh            -> dist/netbox-offline-<datum>.tar.gz
#   CTR=docker ./build/build-bundle.sh -> totez pres docker
#
# Za firemni proxy s TLS inspekci: BUILD_CA_CERT=/cesta/k/ca.crt ./build/build-bundle.sh
# (certifikat se pouzije jen pri stavbe, do vysledneho obrazu se nedostane).
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
pull() { # Docker Hub omezuje pocet stazeni (429), proto opakovani a pripadne lokalni kopie
  local img=$1 i
  for i in 1 2 3 4; do
    "$CTR" pull --platform "linux/${ARCH}" "$img" && return 0
    sleep $((i * 30))
  done
  if "$CTR" image inspect "$img" >/dev/null 2>&1; then
    echo "VAROVANI: $img nejde stahnout, pouzivam lokalni kopii"
    return 0
  fi
  echo "CHYBA: $img nejde stahnout" >&2
  return 1
}
for img in "$NETBOX_BASE_IMAGE" "$POSTGRES_IMAGE" "$VALKEY_IMAGE" "$BATFISH_IMAGE"; do
  pull "$img"
done

echo "== stavim ${NETBOX_IMAGE}"
BUILD_ARGS=(--platform "linux/${ARCH}" --build-arg "NETBOX_BASE_IMAGE=${NETBOX_BASE_IMAGE}")
CONTAINERFILE=build/Containerfile
if [ -n "${HTTPS_PROXY:-}" ]; then
  BUILD_ARGS+=(--network host --build-arg "HTTPS_PROXY=${HTTPS_PROXY}" --build-arg "HTTP_PROXY=${HTTP_PROXY:-}" --build-arg "NO_PROXY=${NO_PROXY:-}")
fi
if [ -n "${BUILD_CA_CERT:-}" ]; then
  cp "$BUILD_CA_CERT" build/.build-ca.crt
  CONTAINERFILE=build/.Containerfile.ca
  sed 's#^RUN /usr/local/bin/uv pip install#COPY build/.build-ca.crt /tmp/build-ca.crt\nRUN SSL_CERT_FILE=/tmp/build-ca.crt /usr/local/bin/uv pip install#' \
    build/Containerfile > "$CONTAINERFILE"
  echo "RUN rm -f /tmp/build-ca.crt" >> "$CONTAINERFILE"
  trap 'rm -f build/.build-ca.crt build/.Containerfile.ca' EXIT
fi
"$CTR" build "${BUILD_ARGS[@]}" -f "$CONTAINERFILE" -t "$NETBOX_IMAGE" .

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
rm -rf "$OUT"
# GitHub Release bere soubory do 2 GB, proto se archiv deli na casti po 1900 MB.
# Na RHEL9 se slozi:  cat netbox-offline-*.tar.gz.part-* > netbox-offline-<datum>.tar.gz
( cd dist && split -b 1900M -d "${NAME}.tar.gz" "${NAME}.tar.gz.part-" \
  && sha256sum "${NAME}.tar.gz" "${NAME}.tar.gz.part-"* > "${NAME}.sha256" )

echo
echo "Hotovo: $ROOT/dist/${NAME}.tar.gz (a casti .part-NN pro GitHub Release)"
echo "Preneste na RHEL9 i se souborem ${NAME}.sha256 a pokracujte podle README, kapitola Postup."
