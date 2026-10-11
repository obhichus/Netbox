#!/usr/bin/env bash
# Instalace NetBoxu + IP Fabric pluginu na RHEL9 BEZ internetu.
# Spousti se jako root z rozbaleneho balicku:
#
#   tar xzf netbox-offline-<datum>.tar.gz && cd netbox-offline-<datum>
#   sudo ./deploy/install.sh
#
# Opakovane spusteni je bezpecne: existujici hesla, konfigurace a data se neprepisuji,
# jen se nahraji nove obrazy a restartuji sluzby (tak se dela i upgrade).
set -euo pipefail

SRC=$(cd "$(dirname "$0")/.." && pwd)
DEST=/opt/netbox-offline
QUADLET_DIR=/etc/containers/systemd

say() { printf '\n== %s\n' "$*"; }
die() { printf 'CHYBA: %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || die "spustte jako root (sudo)"
command -v podman >/dev/null || die "chybi podman: dnf install container-tools (z instalacniho DVD/ISO RHEL9, viz README)"

PODMAN_VER=$(podman version --format '{{.Client.Version}}')
if [ "$(printf '%s\n4.4.0\n' "$PODMAN_VER" | sort -V | head -1)" != "4.4.0" ]; then
  die "podman $PODMAN_VER je moc stary, quadlet potrebuje 4.4+ (RHEL 9.2 a novejsi)"
fi

# shellcheck source=../versions.env
source "$SRC/versions.env"

say "kontrola integrity balicku"
if [ -f "$SRC/SHA256SUMS" ]; then
  (cd "$SRC" && sha256sum --quiet -c SHA256SUMS) || die "kontrolni soucty nesedi, balicek je poskozeny"
else
  echo "SHA256SUMS chybi (spousteno z gitu?), preskakuji"
fi

say "nahravam obrazy do podmanu"
for t in "$SRC"/images/*.tar; do
  [ -e "$t" ] || die "v $SRC/images nejsou zadne obrazy - postavte balicek pres build/build-bundle.sh"
  podman load -i "$t"
done
for img in "$NETBOX_IMAGE" "$POSTGRES_IMAGE" "$VALKEY_IMAGE" "$BATFISH_IMAGE"; do
  podman image exists "$img" || die "obraz $img se nenahral"
done

say "kopiruji soubory do $DEST"
mkdir -p "$DEST"/{env,configuration,backups}
cp -r "$SRC"/{versions.env,deploy,migrate,commatrix,docs,quadlet} "$DEST"/
cp "$SRC"/README.md "$DEST"/ 2>/dev/null || true
cp "$SRC"/env/*.example "$DEST"/env/
for f in "$SRC"/configuration/*.py; do
  # konfigurace upravena na serveru ma prednost pred verzi z balicku
  [ -e "$DEST/configuration/$(basename "$f")" ] || cp "$f" "$DEST/configuration/"
done

# Skripty a dokumentace pocitaji s /opt/commatrix (tak to bylo na puvodnim stroji).
[ -e /opt/commatrix ] || ln -s "$DEST/commatrix" /opt/commatrix
if [ ! -e "$DEST/commatrix/ipf.env" ]; then
  cp "$DEST/commatrix/ipf.env.example" "$DEST/commatrix/ipf.env"
  chmod 600 "$DEST/commatrix/ipf.env"
fi

say "hesla a env soubory"
rnd() { local s; s=$(head -c 1024 /dev/urandom | LC_ALL=C tr -dc 'A-Za-z0-9'); printf '%s' "${s:0:$1}"; }
render() { # $1 vzor, $2 cil
  [ -e "$2" ] && { echo "ponechavam existujici $2"; return; }
  sed -e "s|@DB_PASSWORD@|$DB_PASSWORD|g" \
      -e "s|@REDIS_PASSWORD@|$REDIS_PASSWORD|g" \
      -e "s|@REDIS_CACHE_PASSWORD@|$REDIS_CACHE_PASSWORD|g" \
      -e "s|@SECRET_KEY@|$SECRET_KEY|g" \
      -e "s|@API_TOKEN_PEPPER@|$API_TOKEN_PEPPER|g" "$1" > "$2"
  chmod 600 "$2"
  echo "vytvoreno $2"
}
envval() { sed -n "s/^$1=//p" "$DEST/env/netbox.env" 2>/dev/null | head -1; }
# Pri opakovanem behu se hesla berou z existujiciho netbox.env, aby vsechny soubory sedely.
DB_PASSWORD=$(envval DB_PASSWORD);                 DB_PASSWORD=${DB_PASSWORD:-$(rnd 32)}
REDIS_PASSWORD=$(envval REDIS_PASSWORD);           REDIS_PASSWORD=${REDIS_PASSWORD:-$(rnd 32)}
REDIS_CACHE_PASSWORD=$(envval REDIS_CACHE_PASSWORD); REDIS_CACHE_PASSWORD=${REDIS_CACHE_PASSWORD:-$(rnd 32)}
SECRET_KEY=$(rnd 60)
API_TOKEN_PEPPER=$(rnd 50)
render "$DEST/env/netbox.env.example"        "$DEST/env/netbox.env"
render "$DEST/env/postgres.env.example"      "$DEST/env/postgres.env"
render "$DEST/env/valkey.conf.example"       "$DEST/env/valkey.conf"
render "$DEST/env/valkey-cache.conf.example" "$DEST/env/valkey-cache.conf"
# kontejner valkey bezi pod vlastnim uzivatelem a musi konfiguraci precist
chmod 644 "$DEST/env/valkey.conf" "$DEST/env/valkey-cache.conf"

say "systemd jednotky (quadlet) do $QUADLET_DIR"
mkdir -p "$QUADLET_DIR"
for q in "$SRC"/quadlet/*; do
  sed -e "s|@NETBOX_IMAGE@|$NETBOX_IMAGE|g" \
      -e "s|@POSTGRES_IMAGE@|$POSTGRES_IMAGE|g" \
      -e "s|@VALKEY_IMAGE@|$VALKEY_IMAGE|g" \
      -e "s|@BATFISH_IMAGE@|$BATFISH_IMAGE|g" \
      -e "s|@NETBOX_PORT@|$NETBOX_PORT|g" "$q" > "$QUADLET_DIR/$(basename "$q")"
done
systemctl daemon-reload
systemctl list-unit-files 'netbox*' --no-legend | grep -q '^netbox.service' \
  || die "quadlet nevygeneroval netbox.service; zkuste: /usr/libexec/podman/quadlet -dryrun"

if systemctl is-active --quiet firewalld; then
  say "firewalld: oteviram port $NETBOX_PORT/tcp"
  firewall-cmd --quiet --permanent --add-port="${NETBOX_PORT}/tcp"
  # Batfish API jen kdyz se k nemu pristupuje z jineho stroje (pybatfish z notebooku):
  # firewall-cmd --permanent --add-port=9996-9997/tcp --add-port=8888/tcp
  firewall-cmd --quiet --reload
fi

say "startuji sluzby (prvni start dela migrace databaze, muze trvat i 10 minut)"
systemctl restart netbox-postgres netbox-redis netbox-redis-cache
systemctl restart netbox.service
systemctl restart netbox-worker.service
systemctl restart batfish.service

for _ in $(seq 1 120); do
  if [ "$(podman healthcheck run netbox >/dev/null 2>&1 && echo ok)" = ok ]; then
    break
  fi
  sleep 10
done
podman healthcheck run netbox >/dev/null 2>&1 || die "NetBox neni zdravy, viz: journalctl -u netbox -n 200"

say "skripty komunikacni matice"
"$DEST/deploy/install-commatrix.sh"

cat <<EOF

Hotovo. NetBox bezi na http://$(hostname -f 2>/dev/null || hostname):${NETBOX_PORT}/

Dalsi kroky:
  - novy server:       $DEST/deploy/create-superuser.sh
  - presun dat ze stareho stroje: $DEST/migrate/import-on-rhel.sh <archiv>
  - stav:              systemctl status 'netbox*'   |   podman ps
EOF
