#!/usr/bin/env bash
# Zabali hotovy offline balicek (dist/netbox-offline-<datum>.tar.gz z build-bundle.sh) do RPM pro RHEL9.
#
#   ./build/build-rpm.sh dist/netbox-offline-20261011.tar.gz
#
# Vysledek: dist/netbox-offline-<verze NetBoxu>-<datum>.el9.x86_64.rpm
# Na RHEL9 (root):  dnf install ./netbox-offline-*.rpm  &&  netbox-offline-install
#
# RPM jen rozbali balicek do /opt/netbox-offline-balik a prida prikaz netbox-offline-install.
# Samotnou instalaci (nahrani obrazu, hesla, sluzby) dela az ten prikaz, ne RPM: trva minuty
# a ptat se na nic nemusi, ale v transakci dnf by se spatne hledala chyba.
# Potrebuje rpmbuild (Ubuntu: apt install rpm; RHEL: dnf install rpm-build).
set -euo pipefail

TGZ=${1:?cesta k dist/netbox-offline-<datum>.tar.gz}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
command -v rpmbuild >/dev/null || { echo "chybi rpmbuild (apt install rpm / dnf install rpm-build)"; exit 1; }
# shellcheck source=../versions.env
source "$ROOT/versions.env"

NAME=$(basename "$TGZ" .tar.gz)            # netbox-offline-20261011
DATUM=${NAME##*-}
NB_VER=$(sed -n 's/^NETBOX_IMAGE=.*:\([0-9.]*\).*/\1/p' "$ROOT/versions.env")
TOP=$(mktemp -d)
trap 'rm -rf "$TOP"' EXIT
mkdir -p "$TOP"/{BUILD,RPMS,SOURCES,SPECS,SRPMS,BUILDROOT}

echo "== rozbaluji $TGZ"
mkdir -p "$TOP/src"
tar -C "$TOP/src" -xzf "$TGZ"
[ -d "$TOP/src/$NAME/images" ] || { echo "v archivu chybi $NAME/images"; exit 1; }

cat > "$TOP/SPECS/netbox-offline.spec" <<EOF
Name:           netbox-offline
Version:        ${NB_VER}
Release:        ${DATUM}%{?dist}
Summary:        NetBox s pluginem IP Fabric a kontrolou komunikacni matice (offline, podman)
License:        Apache-2.0 and others
BuildArch:      x86_64
AutoReqProv:    no
Requires:       podman >= 4.4
Requires:       tar
Requires:       python3
Requires:       coreutils

# obsah jsou hotove obrazy kontejneru, nic se nekompiluje ani nestripuje
%global debug_package %{nil}
%global __os_install_post %{nil}
%global _build_id_links none
%global _binary_payload w3.zstdio

%description
Offline instalacni balicek NetBoxu ${NB_VER} s pluginy ipfabric_netbox a netbox_branching,
PostgreSQL, Valkey a Batfish jako podman kontejnery se systemd quadlety, skripty kontroly
komunikacni matice a konfigurator napojeni na IP Fabric.

Po instalaci RPM spustte jako root:  netbox-offline-install
Navod: /opt/netbox-offline-balik/INSTALACE.md

%install
mkdir -p %{buildroot}/opt/netbox-offline-balik %{buildroot}%{_sbindir}
cp -a ${TOP}/src/${NAME}/. %{buildroot}/opt/netbox-offline-balik/
cat > %{buildroot}%{_sbindir}/netbox-offline-install <<'SH'
#!/bin/sh
exec /opt/netbox-offline-balik/deploy/install.sh "\$@"
SH
cat > %{buildroot}%{_sbindir}/netbox-ipfabric-config <<'SH'
#!/bin/sh
exec /opt/netbox-offline/deploy/configure-ipfabric.py "\$@"
SH
chmod 755 %{buildroot}%{_sbindir}/netbox-offline-install %{buildroot}%{_sbindir}/netbox-ipfabric-config

%post
cat <<'MSG'

NetBox offline balicek je rozbaleny v /opt/netbox-offline-balik.
Instalace a spusteni sluzeb (jako root):   netbox-offline-install
Napojeni na IP Fabric (po instalaci):       netbox-ipfabric-config
Navod krok za krokem: /opt/netbox-offline-balik/INSTALACE.md

MSG

%files
/opt/netbox-offline-balik
%{_sbindir}/netbox-offline-install
%{_sbindir}/netbox-ipfabric-config
EOF

echo "== rpmbuild (zstd, chvili to trva)"
rpmbuild --quiet --define "_topdir $TOP" --define "dist .el9" -bb "$TOP/SPECS/netbox-offline.spec"
RPM=$(find "$TOP/RPMS" -name '*.rpm' | head -1)
mkdir -p "$ROOT/dist"
mv "$RPM" "$ROOT/dist/"
OUT="$ROOT/dist/$(basename "$RPM")"
( cd "$ROOT/dist" && sha256sum "$(basename "$OUT")" > "$(basename "$OUT").sha256" )
ls -la "$OUT"
echo "Hotovo: $OUT"
