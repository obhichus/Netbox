"""Zalozi prefixy z IP adres naimportovanych z IP Fabricu.

Kazdy radek tabulky adres nese sloupec `net` se svou podsiti. Endpoint
managed-networks nemame namapovany, takze prefixy odvodime odtud.
Nektere radky (hlavne IPv6) maji v `net` hostitelskou adresu s maskou,
proto se kazda hodnota nejdriv prevede na skutecnou sit.

Spoustet po ingesci:
    docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < /opt/commatrix/prefixy.py
"""
import ipaddress

from ipam.models import Prefix, VRF
from ipfabric_netbox.models import IPFabricData

nalezene = set()
neplatne = 0
for typ in ("/technology/addressing/managed-ip/ipv4", "/technology/addressing/managed-ip/ipv6"):
    for zaznam in IPFabricData.objects.filter(type=typ):
        hodnota = (zaznam.data.get("net") or "").strip()
        if not hodnota or "/" not in hodnota:
            continue
        try:
            sit = str(ipaddress.ip_network(hodnota, strict=False))
        except ValueError:
            neplatne += 1
            continue
        nalezene.add((sit, (zaznam.data.get("vrf") or "").strip()))

print(f"ruznych prefixu v datech: {len(nalezene)} | neprevoditelnych hodnot: {neplatne}")

vytvoreno = existovalo = chyba = 0
for sit, nazev_vrf in sorted(nalezene):
    vrf = VRF.objects.filter(name=nazev_vrf).first() if nazev_vrf else None
    if Prefix.objects.filter(prefix=sit, vrf=vrf).exists():
        existovalo += 1
        continue
    try:
        Prefix.objects.create(prefix=sit, vrf=vrf, status="active",
                              description="Odvozeno z IP Fabric snapshotu")
        vytvoreno += 1
    except Exception as e:
        chyba += 1
        if chyba <= 3:
            print(f"   chyba u {sit} ({nazev_vrf}): {e}")

print(f"vytvoreno: {vytvoreno} | uz existovalo: {existovalo} | chyb: {chyba}")
print(f"prefixu v NetBoxu celkem: {Prefix.objects.count()}")
