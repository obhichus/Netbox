"""
Naplni snapshot v NetBoxu surovymi daty z IP Fabric.

Urceno pro zdroj typu REMOTE, kdy se plugin ipfabric_netbox k IP Fabricu
nepripojuje sam a ocekava, ze mu data nekdo nahraje. Tento skript je stahne
pres API a zalozi zaznamy IPFabricData se spravnym typem endpointu.
Vlastni mapovani na objekty NetBoxu pak dela plugin svymi transform mapy.

Spousteni zevnitr kontejneru netbox:
    docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < push_ipf_data.py

Prihlasovaci udaje se ctou z promennych prostredi kontejneru:
    IPF_URL, IPF_USER, IPF_PASS, IPF_SNAPSHOT

Volitelne:
    IPF_SOURCE_NAME   nazev zdroje v NetBoxu (vychozi "demo")
"""

import http.cookiejar
import json
import os
import hashlib as _hashlib
import collections as _collections
import re
import urllib.error
import urllib.request

from ipfabric_netbox.models import (
    IPFabricData,
    IPFabricEndpoint,
    IPFabricSnapshot,
    IPFabricSource,
)

MAPOVANI = {
    "/inventory/sites/overview": ["inventory/sites"],
    "/inventory/devices": ["inventory/devices"],
    "/technology/platforms/stack/members": ["platforms/stack/members"],
    "/technology/platforms/vss/chassis": ["platforms/vss/chassis",
                                          "platforms/virtual-chassis/members"],
    "/inventory/interfaces": ["inventory/interfaces"],
    "/inventory/part-numbers": ["inventory/pn", "inventory/part-numbers"],
    "/technology/vlans/site-summary": ["vlan/site-summary"],
    "/technology/routing/vrf/detail": ["vrf/detail"],
    "/technology/networks/managed-networks": ["networks/managed-networks",
                                              "networks/networks"],
    "/technology/addressing/managed-ip/ipv4": ["addressing/managed-devs"],
    "/technology/addressing/managed-ip/ipv6": ["addressing/ipv6-managed-devs",
                                               "addressing/managed-devs-ipv6",
                                               "addressing/ipv6-hosts"],
}


class IPFabric:
    def __init__(self, base_url, user, password, timeout=180):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.raw("POST", "/api/auth/login",
                 {"username": user, "password": password})
        if not len(self.jar):
            raise RuntimeError("Prihlaseni k IP Fabric selhalo.")

    def raw(self, metoda, cesta, telo=None):
        url = f"{self.base}{cesta}"
        data = json.dumps(telo).encode("utf-8") if telo is not None else None
        r = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"},
            method=metoda)
        try:
            with self.opener.open(r, timeout=self.timeout) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            try:
                return e.code, e.read().decode("utf-8")
            except Exception:
                return e.code, ""
        except Exception as e:
            return 0, str(e)

    def sloupce(self, tabulka, snapshot):
        st, telo = self.raw("POST", f"/api/tables/{tabulka}", {
            "columns": ["NEEXISTUJE"], "snapshot": snapshot,
            "format": {"dataType": "json"},
            "pagination": {"limit": 1, "start": 0}})
        if st != 422:
            return None
        m = re.search(r"Expected (.+?), received", telo, re.S)
        if not m:
            return None
        return [c.strip().strip("'") for c in m.group(1).split("|")]

    def data(self, tabulka, sloupce, snapshot, limit=10000):
        vysledek, start = [], 0
        while True:
            st, telo = self.raw("POST", f"/api/tables/{tabulka}", {
                "columns": sloupce, "snapshot": snapshot,
                "format": {"dataType": "json"},
                "pagination": {"limit": limit, "start": start}})
            if st != 200:
                raise RuntimeError(f"HTTP {st}: {telo[:200]}")
            odpoved = json.loads(telo)
            radky = odpoved.get("data", [])
            vysledek.extend(radky)
            celkem = odpoved.get("_meta", {}).get("count", len(vysledek))
            start += len(radky)
            if not radky or start >= celkem:
                return vysledek


TEXTOVE_SLOUPCE = {
    "sn", "snHw", "hostname", "hostnameOriginal", "hostnameProcessed", "domain",
    "fqdn", "siteName", "vendor", "family", "model", "platform", "version",
    "devType", "intName", "intNameAlias", "nameOriginal", "mac", "dscr",
    "vrf", "vlanName", "ip", "net", "loginIp", "media", "reason",
    "slug", "stpDomain", "pn", "name", "dscrProcessed", "partNumber",
    "description", "serialNumber",
}


def normalizuj(radek):
    """NetBox u textovych poli nesnasi None, chce prazdny retezec."""
    upraveny = {}
    for k, v in radek.items():
        if v is None and k in TEXTOVE_SLOUPCE:
            upraveny[k] = ""
        else:
            upraveny[k] = v
    return upraveny


url = os.environ.get("IPF_URL")
user = os.environ.get("IPF_USER")
pwd = os.environ.get("IPF_PASS")
snapshot_id = os.environ.get("IPF_SNAPSHOT") or "$last"
nazev_zdroje = os.environ.get("IPF_SOURCE_NAME") or "guided-demo.eu.ipfabric.io"

import json as _json
import pathlib

dump_dir = os.environ.get("IPF_DUMP_DIR")
load_dir = os.environ.get("IPF_LOAD_DIR")

if load_dir:
    load_dir = pathlib.Path(load_dir)
    if not load_dir.is_dir():
        raise SystemExit(f"Adresar {load_dir} neexistuje.")
elif not (url and user and pwd):
    raise SystemExit("Chybi IPF_URL, IPF_USER nebo IPF_PASS v prostredi kontejneru.")

if dump_dir:
    dump_dir = pathlib.Path(dump_dir)
    dump_dir.mkdir(parents=True, exist_ok=True)

zdroj = IPFabricSource.objects.get(name=nazev_zdroje)
print(f"Zdroj: {zdroj.name} (typ {zdroj.type})")
if zdroj.type != "remote":
    print("VAROVANI: zdroj neni typu remote, ingesce data z IPFabricData nepouzije.")

snapshot = IPFabricSnapshot.objects.filter(source=zdroj).first()
if not snapshot:
    raise SystemExit("Zdroj nema zadny snapshot. Zaloz ho nejdriv v UI pluginu.")
print(f"Snapshot v NetBoxu: {snapshot.name} ({snapshot.snapshot_id})")
print(f"Snapshot v IP Fabric: {snapshot_id}\n")

if load_dir:
    ipf = None
    print(f"Ctu ulozeny snapshot z {load_dir}\n")
else:
    ipf = IPFabric(url, user, pwd)
    print(f"Pripojeno k {url}\n")

smazano = IPFabricData.objects.filter(snapshot_data=snapshot).count()
IPFabricData.objects.filter(snapshot_data=snapshot).delete()
if smazano:
    print(f"Smazano {smazano} starych zaznamu.\n")

celkem_ulozeno = 0
prehled = []

for endpoint in IPFabricEndpoint.objects.all().order_by("pk"):
    ep = endpoint.endpoint
    kandidati = MAPOVANI.get(ep, [])
    if not kandidati:
        print(f"{ep:48} PRESKOCENO (neznama tabulka)")
        prehled.append((ep, "-", "neznama tabulka", 0))
        continue

    nazev_souboru = ep.strip("/").replace("/", "_") + ".json"

    if load_dir:
        soubor = load_dir / nazev_souboru
        if not soubor.exists():
            print(f"{ep:48} CHYBI SOUBOR ({nazev_souboru})")
            prehled.append((ep, nazev_souboru, "chybi soubor", 0))
            continue
        ulozene = _json.loads(soubor.read_text(encoding="utf-8"))
        tabulka = ulozene.get("tabulka", "-")
        radky = ulozene.get("radky", [])
    else:
        tabulka, sloupce = None, None
        for k in kandidati:
            sl = ipf.sloupce(k, snapshot_id)
            if sl:
                tabulka, sloupce = k, sl
                break

        if not tabulka:
            print(f"{ep:48} NEDOSTUPNE ({', '.join(kandidati)})")
            prehled.append((ep, kandidati[0], "nedostupne", 0))
            continue

        try:
            radky = ipf.data(tabulka, sloupce, snapshot_id)
        except Exception as e:
            print(f"{ep:48} CHYBA: {e}")
            prehled.append((ep, tabulka, f"chyba: {e}", 0))
            continue

    radky = [normalizuj(r) for r in radky]

    for r in radky:
        sn = (r.get("sn") or "").strip()
        r["nb_serial"] = sn if 0 < len(sn) < 50 else (
            "ipf-" + _hashlib.sha1((sn or repr(sorted(r.items()))).encode()).hexdigest()[:12])

    if ep == "/inventory/devices":
        vyskyt = _collections.Counter(
            ((r.get("siteName") or ""), (r.get("hostname") or "")) for r in radky)
        for r in radky:
            host = (r.get("hostname") or "").strip()
            klic = ((r.get("siteName") or ""), (r.get("hostname") or ""))
            if vyskyt[klic] > 1 or len(host) > 64:
                otisk = _hashlib.sha1((r.get("sn") or host).encode()).hexdigest()[:8]
                r["nb_name"] = f"{host[:53]} ({otisk})"
            else:
                r["nb_name"] = host

    if ep == "/technology/vlans/site-summary":
        pred = len(radky)
        radky = [r for r in radky if str(r.get("vlanId") or "0").lstrip("-").isdigit()
                 and int(r.get("vlanId") or 0) >= 1]
        if pred != len(radky):
            print(f"{'':48} vynechano {pred - len(radky)} VLAN s neplatnym ID")

    if dump_dir:
        (dump_dir / nazev_souboru).write_text(
            _json.dumps({"endpoint": ep, "tabulka": tabulka,
                         "snapshot": snapshot_id, "radky": radky},
                        ensure_ascii=False),
            encoding="utf-8",
        )

    if radky:
        IPFabricData.objects.bulk_create(
            [IPFabricData(snapshot_data=snapshot, type=ep, data=r) for r in radky],
            batch_size=2000,
        )
    celkem_ulozeno += len(radky)
    print(f"{ep:48} {tabulka:34} {len(radky):>6} zaznamu")
    prehled.append((ep, tabulka, "ok", len(radky)))

    if ep == "/inventory/sites/overview" and radky:
        lokality = sorted({r.get("siteName") for r in radky if r.get("siteName")})
        snapshot.data = dict(snapshot.data or {})
        snapshot.data["sites"] = lokality
        snapshot.save()
        print(f"{'':48} do snapshotu zapsano {len(lokality)} lokalit")

print(f"\nCelkem ulozeno zaznamu: {celkem_ulozeno}")
print(f"IPFabricData pro snapshot: {IPFabricData.objects.filter(snapshot_data=snapshot).count()}")

print("\n=== PREHLED ===")
for ep, tab, stav, pocet in prehled:
    print(f"{stav:16} {str(pocet):>6}  {ep}  ->  {tab}")

print("\nHotovo. Ted v UI pluginu spust ingesci (IP Fabric -> Syncs -> Adhoc Ingestion).")
