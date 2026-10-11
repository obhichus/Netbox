"""Doplni zarizenim primarni IPv4 podle sloupce loginIp z IP Fabricu.

Plugin to neumi, protoze pri vypnute globalni jedinecnosti selhava na
odebirani teze adresy jinemu zarizeni. Spoustet po kazde ingesci:
    docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < /opt/commatrix/primarni_ip.py
"""
from dcim.models import Device
from ipfabric_netbox.models import IPFabricData

podle_serialu = {}
for d in IPFabricData.objects.filter(type="/inventory/devices"):
    ip = (d.data.get("loginIp") or d.data.get("loginIpv4") or "").strip()
    if ip:
        podle_serialu[d.data.get("nb_serial")] = ip.split("/")[0]

nastaveno = beze_zmeny = nenalezeno = bez_adresy = 0
for dev in Device.objects.prefetch_related("interfaces__ip_addresses"):
    ip = podle_serialu.get(dev.serial)
    if not ip:
        bez_adresy += 1
        continue
    nalezena = None
    for rozhrani in dev.interfaces.all():
        for adresa in rozhrani.ip_addresses.all():
            if str(adresa.address.ip) == ip:
                nalezena = adresa
                break
        if nalezena:
            break
    if not nalezena:
        nenalezeno += 1
    elif dev.primary_ip4_id == nalezena.pk:
        beze_zmeny += 1
    else:
        dev.primary_ip4 = nalezena
        dev.save(update_fields=["primary_ip4"])
        nastaveno += 1

print(f"nastaveno:   {nastaveno}")
print(f"beze zmeny:  {beze_zmeny}")
print(f"adresa v datech, ale ne na rozhrani: {nenalezeno}")
print(f"bez loginIp v datech: {bez_adresy}")
doplneno_jedina = 0
for dev in Device.objects.filter(primary_ip4__isnull=True).prefetch_related("interfaces__ip_addresses"):
    adresy = [a for i in dev.interfaces.all() for a in i.ip_addresses.all() if a.address.version == 4]
    if len(adresy) == 1:
        dev.primary_ip4 = adresy[0]
        dev.save(update_fields=["primary_ip4"])
        doplneno_jedina += 1
print(f"doplneno podle jedine adresy: {doplneno_jedina}")
print(f"celkem s primarni IPv4: {Device.objects.filter(primary_ip4__isnull=False).count()} z {Device.objects.count()}")
