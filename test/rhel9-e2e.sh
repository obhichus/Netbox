#!/bin/bash
# Test instalacniho balicku na RHEL9-kompatibilnim systemu (Rocky Linux 9 se systemd) v kontejneru.
# Pouziti (stroj s dockerem a internetem): ./test/rhel9-e2e.sh dist/netbox-offline-YYYYMMDD
#   1. spusti Rocky 9 se systemd, nainstaluje container-tools (jako z DVD RHEL9)
#   2. ODPOJI sit a pak postupuje presne podle README: cat casti, sha256sum -c, tar, install.sh
#   3. overi NetBox, pluginy, skripty matice, superuzivatele, zalohu a konfigurator IP Fabricu
set -euo pipefail
BASE=${1:?cesta k balicku bez pripony, napr. dist/netbox-offline-20261011}
DIST=$(cd "$(dirname "$BASE")" && pwd); NAME=$(basename "$BASE")
IMG=${EL9_IMAGE:-docker.io/rockylinux/rockylinux:9-ubi-init}
C=rhel9-test
say() { echo; echo "=== $*"; }
x() { docker exec "$C" bash -lc "$*"; }
dump() {
  echo "=== SELHALO - logy"
  docker exec "$C" bash -c 'systemctl --no-pager --plain list-units "netbox*"; podman ps -a;
    for u in netbox netbox-worker netbox-postgres netbox-redis; do echo "--- $u"; journalctl -u $u --no-pager -n 80; done' || true
}
trap dump ERR

docker rm -f "$C" >/dev/null 2>&1 || true
docker volume rm -f rhel9-containers >/dev/null 2>&1 || true
say "start $IMG"
docker run -d --name "$C" --hostname rhel9 --privileged --cgroupns=host \
  -v /sys/fs/cgroup:/sys/fs/cgroup:rw -v rhel9-containers:/var/lib/containers \
  -v "$DIST":/media/balik:ro --tmpfs /run --tmpfs /tmp "$IMG" >/dev/null
for _ in $(seq 30); do x 'systemctl is-system-running 2>/dev/null' | grep -qE 'running|degraded' && break; sleep 2; done
x 'cat /etc/redhat-release'

say "dnf install container-tools (na RHEL9 z DVD)"
x 'dnf -y -q install container-tools firewalld tar hostname procps-ng && systemctl enable --now firewalld && podman --version'

say "odpojuji sit, dal uz offline"
for n in $(docker inspect -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}} {{end}}' "$C"); do
  docker network disconnect "$n" "$C"
done
x '! curl -s -m 5 https://registry-1.docker.io >/dev/null' && echo "offline OK"

say "postup z README"
x "mkdir -p /root/instalace && cd /root/instalace && cp /media/balik/$NAME.tar.gz.part-* /media/balik/$NAME.sha256 . \
   && cat $NAME.tar.gz.part-* > $NAME.tar.gz \
   && sha256sum -c $NAME.sha256 && tar xzf $NAME.tar.gz"
x "cd /root/instalace/$NAME && ./deploy/install.sh"

say "kontroly"
x 'systemctl --no-pager --plain list-units "netbox*" batfish.service'
x 'curl -sf -o /dev/null -w "login HTTP %{http_code}\n" http://127.0.0.1:8000/login/'
x 'firewall-cmd --list-ports | grep -q 8000/tcp && echo "firewalld 8000 OK"'
x 'podman exec netbox /opt/netbox/netbox/manage.py shell -c "
from django.conf import settings; from extras.models import ScriptModule
print(\"PLUGINY\", settings.PLUGINS)
print(\"SKRIPTY\", sorted(n for m in ScriptModule.objects.all() for n in m.scripts.values_list(\"name\", flat=True)))
" 2>/dev/null | grep -E "PLUGINY|SKRIPTY"'
x 'podman exec netbox /opt/netbox/netbox/manage.py shell -c "
from django.contrib.auth import get_user_model; U=get_user_model()
U.objects.filter(username=\"admin\").exists() or U.objects.create_superuser(\"admin\",\"a@b.c\",\"test-heslo-123\"); print(\"SUPERUSER OK\")
" 2>/dev/null | grep OK'

say "zaloha"
x '/opt/netbox-offline/deploy/backup.sh && ls -la /opt/netbox-offline/backups | tail -3'

say "konfigurator IP Fabricu (verze 7.5, server neni dostupny -> ocekavany kod 2)"
x 'printf "IPF_URL=https://ipfabric.test.invalid\nIPF_VERSION=7.5\nIPF_CA=\nIPF_SOURCE_NAME=test\nIPF_SOURCE_TYPE=remote\n" > /opt/netbox-offline/env/ipfabric.conf'
set +e; x '/opt/netbox-offline/deploy/configure-ipfabric.py --apply'; rc=$?; set -e
[ "$rc" = 2 ] || { echo "konfigurator: neocekavany kod $rc"; exit 1; }
x 'grep -h ^Image= /etc/containers/systemd/netbox.container /etc/containers/systemd/netbox-worker.container'
x 'podman exec netbox /opt/netbox/venv/bin/python -c "import ipfabric; print(\"SDK v bezicim NetBoxu\", ipfabric.__version__)"' | tee /dev/stderr | grep -q " 7\.5\."
x 'curl -sf -o /dev/null -w "login po prepnuti HTTP %{http_code}\n" http://127.0.0.1:8000/login/'

say "VSE OK"
