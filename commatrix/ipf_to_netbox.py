#!/usr/bin/env python3
"""
Import inventare z IP Fabric do NetBoxu.

Prenasi lokality, vyrobce, typy zarizeni, role, platformy, zarizeni,
rozhrani, VRF, VLANy, prefixy a IP adresy. Je idempotentni -- co uz
v NetBoxu existuje, znovu nezaklada, takze se da poustet opakovane.

Pouziti:
    python3 ipf_to_netbox.py --dry-run          ukaze, co by udelal
    python3 ipf_to_netbox.py                    provede import
    python3 ipf_to_netbox.py --only sites,devices
    python3 ipf_to_netbox.py --snapshot <id>

Konfigurace v ipf.env ve stejnem adresari:
    IPF_URL, IPF_USER, IPF_PASS, IPF_SNAPSHOT
    NETBOX_URL, NETBOX_TOKEN

Sekce (poradi je zavazne, pozdejsi zavisi na drivejsich):
    sites, manufacturers, devicetypes, roles, platforms, devices,
    interfaces, vrfs, vlans, prefixes, ipaddresses
"""

import argparse
import http.cookiejar
import ipaddress
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

SEKCE = ["sites", "manufacturers", "devicetypes", "roles", "platforms",
         "devices", "interfaces", "vrfs", "vlans", "prefixes", "ipaddresses"]


def slug(text, maxlen=100):
    text = unicodedata.normalize("NFKD", str(text))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return (text or "x")[:maxlen]


def nacti_env(cesta):
    conf = {}
    if not cesta.exists():
        return conf
    for radek in cesta.read_text(encoding="utf-8").splitlines():
        radek = radek.strip()
        if not radek or radek.startswith("#") or "=" not in radek:
            continue
        k, v = radek.split("=", 1)
        conf[k.strip()] = v.strip()
    return conf


class IPFabric:
    def __init__(self, base_url, user, password, timeout=120):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self._req("POST", "/api/auth/login",
                  {"username": user, "password": password})
        if not len(self.jar):
            raise RuntimeError("Prihlaseni k IP Fabric selhalo.")
        self._req("GET", "/api/users/me")

    def _req(self, metoda, cesta, telo=None):
        url = f"{self.base}{cesta}"
        data = json.dumps(telo).encode("utf-8") if telo is not None else None
        r = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"},
            method=metoda)
        with self.opener.open(r, timeout=self.timeout) as resp:
            obsah = resp.read().decode("utf-8")
        return json.loads(obsah) if obsah else {}

    def tabulka(self, cesta, sloupce, snapshot, limit=10000):
        vysledek, start = [], 0
        while True:
            odpoved = self._req("POST", f"/api/tables/{cesta}", {
                "columns": sloupce, "snapshot": snapshot,
                "format": {"dataType": "json"},
                "pagination": {"limit": limit, "start": start}})
            data = odpoved.get("data", [])
            vysledek.extend(data)
            celkem = odpoved.get("_meta", {}).get("count", len(vysledek))
            start += len(data)
            if not data or start >= celkem:
                return vysledek


class NetBox:
    def __init__(self, base_url, token, dry_run=False, timeout=60):
        self.base = base_url.rstrip("/")
        self.token = token
        self.dry_run = dry_run
        self.timeout = timeout
        self.vytvoreno = {}
        self.preskoceno = {}
        me = self._req("GET", "/api/users/tokens/provision/") if False else None

    def _req(self, metoda, cesta, telo=None):
        url = f"{self.base}{cesta}"
        data = json.dumps(telo).encode("utf-8") if telo is not None else None
        r = urllib.request.Request(url, data=data, method=metoda, headers={
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json"})
        with urllib.request.urlopen(r, timeout=self.timeout) as resp:
            obsah = resp.read().decode("utf-8")
        return json.loads(obsah) if obsah else {}

    def najdi(self, endpoint, **filtry):
        qs = "&".join(f"{k}={urllib.request.quote(str(v))}"
                      for k, v in filtry.items() if v is not None)
        odpoved = self._req("GET", f"/api/{endpoint}/?{qs}&limit=1")
        vysledky = odpoved.get("results", [])
        return vysledky[0] if vysledky else None

    def zaloz(self, endpoint, hledej, data):
        existujici = self.najdi(endpoint, **hledej)
        if existujici:
            self.preskoceno[endpoint] = self.preskoceno.get(endpoint, 0) + 1
            return existujici
        if self.dry_run:
            self.vytvoreno[endpoint] = self.vytvoreno.get(endpoint, 0) + 1
            return {"id": None, "_dry": True, **data}
        try:
            novy = self._req("POST", f"/api/{endpoint}/", data)
            self.vytvoreno[endpoint] = self.vytvoreno.get(endpoint, 0) + 1
            return novy
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8")[:300]
            print(f"    CHYBA {endpoint} {e.code}: {detail}")
            print(f"      data: {json.dumps(data, ensure_ascii=False)[:200]}")
            return None


def prefix_delka(net):
    if not net or "/" not in str(net):
        return None
    try:
        return ipaddress.ip_network(net, strict=False).prefixlen
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="Import inventare z IP Fabric do NetBoxu")
    ap.add_argument("--dry-run", action="store_true", help="nic nezapisuje")
    ap.add_argument("--snapshot", help="ID snapshotu")
    ap.add_argument("--only", help=f"jen vybrane sekce, carkou oddelene: {','.join(SEKCE)}")
    ap.add_argument("--env", default=None)
    args = ap.parse_args()

    adresar = Path(__file__).resolve().parent
    conf = nacti_env(Path(args.env) if args.env else adresar / "ipf.env")

    ipf_url = os.environ.get("IPF_URL") or conf.get("IPF_URL")
    ipf_user = os.environ.get("IPF_USER") or conf.get("IPF_USER")
    ipf_pass = os.environ.get("IPF_PASS") or conf.get("IPF_PASS")
    snapshot = args.snapshot or conf.get("IPF_SNAPSHOT") or "$last"
    nb_url = os.environ.get("NETBOX_URL") or conf.get("NETBOX_URL")
    nb_token = os.environ.get("NETBOX_TOKEN") or conf.get("NETBOX_TOKEN")

    if not all([ipf_url, ipf_user, ipf_pass, nb_url, nb_token]):
        print("Chybi konfigurace: IPF_URL, IPF_USER, IPF_PASS, NETBOX_URL, NETBOX_TOKEN",
              file=sys.stderr)
        return 2

    sekce = [s.strip() for s in args.only.split(",")] if args.only else SEKCE
    nezname = set(sekce) - set(SEKCE)
    if nezname:
        print(f"Neznama sekce: {', '.join(nezname)}", file=sys.stderr)
        return 2

    ipf = IPFabric(ipf_url, ipf_user, ipf_pass)
    nb = NetBox(nb_url, nb_token, dry_run=args.dry_run)

    print(f"IP Fabric: {ipf_url}  snapshot {snapshot}")
    print(f"NetBox:    {nb_url}")
    if args.dry_run:
        print("REZIM NASUCHO -- nic se nezapisuje\n")
    else:
        print()

    id_site, id_vyrobce, id_typ, id_role, id_platf = {}, {}, {}, {}, {}
    id_zarizeni, id_rozhrani, id_vrf = {}, {}, {}

    def nacti_site():
        for s in nb._req("GET", "/api/dcim/sites/?limit=1000").get("results", []):
            id_site[s["name"]] = s["id"]

    def nacti_zarizeni():
        odpoved = nb._req("GET", "/api/dcim/devices/?limit=1000")
        for d in odpoved.get("results", []):
            id_zarizeni[d["name"]] = d["id"]

    if "sites" in sekce:
        print("--- Lokality ---")
        for r in ipf.tabulka("inventory/sites", ["siteName", "devicesCount"], snapshot):
            jmeno = r["siteName"]
            o = nb.zaloz("dcim/sites", {"name": jmeno},
                         {"name": jmeno, "slug": slug(jmeno), "status": "active"})
            if o and o.get("id"):
                id_site[jmeno] = o["id"]
        print(f"    lokalit: {len(id_site)}")

    if not id_site and not args.dry_run:
        nacti_site()

    zarizeni_data = []
    if any(s in sekce for s in ("manufacturers", "devicetypes", "roles",
                                "platforms", "devices")):
        zarizeni_data = ipf.tabulka(
            "inventory/devices",
            ["hostname", "siteName", "vendor", "family", "model", "platform",
             "version", "sn", "devType", "loginIp"], snapshot)
        print(f"--- Zarizeni z IP Fabric: {len(zarizeni_data)} ---")

    if "manufacturers" in sekce:
        for vendor in sorted({(d.get("vendor") or "unknown") for d in zarizeni_data}):
            o = nb.zaloz("dcim/manufacturers", {"name": vendor},
                         {"name": vendor, "slug": slug(vendor)})
            if o and o.get("id"):
                id_vyrobce[vendor] = o["id"]
        print(f"    vyrobcu: {len(id_vyrobce)}")

    if not id_vyrobce and not args.dry_run:
        for m in nb._req("GET", "/api/dcim/manufacturers/?limit=1000").get("results", []):
            id_vyrobce[m["name"]] = m["id"]

    def model_zarizeni(d):
        return (d.get("model") or d.get("platform") or d.get("family") or "unknown")

    if "devicetypes" in sekce:
        dvojice = {(d.get("vendor") or "unknown", model_zarizeni(d))
                   for d in zarizeni_data}
        for vendor, model in sorted(dvojice):
            o = nb.zaloz("dcim/device-types",
                         {"model": model, "manufacturer_id": id_vyrobce.get(vendor)},
                         {"manufacturer": id_vyrobce.get(vendor), "model": model,
                          "slug": slug(f"{vendor}-{model}")})
            if o and o.get("id"):
                id_typ[(vendor, model)] = o["id"]
        print(f"    typu zarizeni: {len(id_typ)}")

    if not id_typ and not args.dry_run:
        for t in nb._req("GET", "/api/dcim/device-types/?limit=1000").get("results", []):
            id_typ[(t["manufacturer"]["name"], t["model"])] = t["id"]

    if "roles" in sekce:
        for devtype in sorted({(d.get("devType") or "unknown") for d in zarizeni_data}):
            o = nb.zaloz("dcim/device-roles", {"name": devtype},
                         {"name": devtype, "slug": slug(devtype), "color": "9e9e9e"})
            if o and o.get("id"):
                id_role[devtype] = o["id"]
        print(f"    roli: {len(id_role)}")

    if not id_role and not args.dry_run:
        for r in nb._req("GET", "/api/dcim/device-roles/?limit=1000").get("results", []):
            id_role[r["name"]] = r["id"]

    if "platforms" in sekce:
        for platf in sorted({(d.get("family") or "unknown") for d in zarizeni_data}):
            o = nb.zaloz("dcim/platforms", {"name": platf},
                         {"name": platf, "slug": slug(platf)})
            if o and o.get("id"):
                id_platf[platf] = o["id"]
        print(f"    platforem: {len(id_platf)}")

    if not id_platf and not args.dry_run:
        for p in nb._req("GET", "/api/dcim/platforms/?limit=1000").get("results", []):
            id_platf[p["name"]] = p["id"]

    if "devices" in sekce:
        print("--- Zarizeni ---")
        for d in zarizeni_data:
            jmeno = d.get("hostname")
            if not jmeno:
                continue
            vendor = d.get("vendor") or "unknown"
            model = model_zarizeni(d)
            telo = {
                "name": jmeno,
                "device_type": id_typ.get((vendor, model)),
                "role": id_role.get(d.get("devType") or "unknown"),
                "site": id_site.get(d.get("siteName")),
                "platform": id_platf.get(d.get("family") or "unknown"),
                "serial": (d.get("sn") or "")[:50],
                "status": "active",
                "comments": f"IP Fabric: {d.get('family')} {d.get('version')}",
            }
            if not (telo["device_type"] and telo["role"] and telo["site"]):
                print(f"    preskakuji {jmeno}: chybi typ, role nebo lokalita")
                continue
            o = nb.zaloz("dcim/devices", {"name": jmeno}, telo)
            if o and o.get("id"):
                id_zarizeni[jmeno] = o["id"]
        print(f"    zarizeni v NetBoxu: {len(id_zarizeni)}")

    if not id_zarizeni and not args.dry_run:
        nacti_zarizeni()

    if "interfaces" in sekce:
        print("--- Rozhrani ---")
        data = ipf.tabulka("inventory/interfaces",
                           ["hostname", "intName", "dscr", "mac", "mtu", "l1", "l2",
                            "speedValue", "primaryIp"], snapshot)
        print(f"    z IP Fabric: {len(data)}")
        for r in data:
            dev_id = id_zarizeni.get(r.get("hostname"))
            if not dev_id:
                continue
            mac = (r.get("mac") or "").strip() or None
            telo = {
                "device": dev_id,
                "name": r.get("intName"),
                "type": "other",
                "enabled": (r.get("l1") or "").lower() in ("up", "enabled"),
                "description": (r.get("dscr") or "")[:200],
            }
            if mac and re.fullmatch(r"[0-9a-fA-F:.\-]{12,17}", mac):
                telo["mac_address"] = mac
            if isinstance(r.get("mtu"), int):
                telo["mtu"] = r["mtu"]
            o = nb.zaloz("dcim/interfaces",
                         {"device_id": dev_id, "name": r.get("intName")}, telo)
            if o and o.get("id"):
                id_rozhrani[(r.get("hostname"), r.get("intName"))] = o["id"]
        print(f"    rozhrani v NetBoxu: {len(id_rozhrani)}")

    if "vrfs" in sekce:
        print("--- VRF ---")
        data = ipf.tabulka("vrf/detail", ["vrf", "rd", "hostname", "siteName"], snapshot)
        for vrf in sorted({r["vrf"] for r in data if r.get("vrf")}):
            rd = next((r.get("rd") for r in data if r.get("vrf") == vrf and r.get("rd")), None)
            o = nb.zaloz("ipam/vrfs", {"name": vrf},
                         {"name": vrf, "rd": (rd or "")[:21] or None})
            if o and o.get("id"):
                id_vrf[vrf] = o["id"]
        print(f"    VRF: {len(id_vrf)}")

    if not id_vrf and not args.dry_run:
        for v in nb._req("GET", "/api/ipam/vrfs/?limit=1000").get("results", []):
            id_vrf[v["name"]] = v["id"]

    if "vlans" in sekce:
        print("--- VLANy ---")
        data = ipf.tabulka("vlan/site-summary",
                           ["siteName", "vlanId", "vlanName", "dscr"], snapshot)
        pocet = 0
        for r in data:
            vid = r.get("vlanId")
            if not isinstance(vid, int):
                continue
            telo = {"vid": vid, "name": (r.get("vlanName") or f"VLAN{vid}")[:64],
                    "site": id_site.get(r.get("siteName")), "status": "active",
                    "description": (r.get("dscr") or "")[:200]}
            hledej = {"vid": vid}
            if telo["site"]:
                hledej["site_id"] = telo["site"]
            if nb.zaloz("ipam/vlans", hledej, telo):
                pocet += 1
        print(f"    VLAN zpracovano: {pocet}")

    ip_data = []
    if "prefixes" in sekce or "ipaddresses" in sekce:
        ip_data = ipf.tabulka("addressing/managed-devs",
                              ["hostname", "intName", "ip", "net", "vrf", "siteName"],
                              snapshot)
        print(f"--- IP zaznamu z IP Fabric: {len(ip_data)} ---")

    if "prefixes" in sekce:
        site_podle_net = {}
        for r in ip_data:
            if r.get("net"):
                site_podle_net.setdefault((r["net"], r.get("vrf")), r.get("siteName"))
        pocet = 0
        for (net, vrf), site_name in sorted(site_podle_net.items()):
            telo = {"prefix": net, "status": "active",
                    "vrf": id_vrf.get(vrf) if vrf else None,
                    "site": id_site.get(site_name)}
            hledej = {"prefix": net}
            if telo["vrf"]:
                hledej["vrf_id"] = telo["vrf"]
            if nb.zaloz("ipam/prefixes", hledej, telo):
                pocet += 1
        print(f"    prefixu zpracovano: {pocet}")

    if "ipaddresses" in sekce:
        print("--- IP adresy ---")
        pocet = 0
        for r in ip_data:
            ip = r.get("ip")
            if not ip:
                continue
            delka = prefix_delka(r.get("net")) or 32
            adresa = f"{ip}/{delka}"
            int_id = id_rozhrani.get((r.get("hostname"), r.get("intName")))
            telo = {"address": adresa, "status": "active",
                    "vrf": id_vrf.get(r.get("vrf")) if r.get("vrf") else None}
            if int_id:
                telo["assigned_object_type"] = "dcim.interface"
                telo["assigned_object_id"] = int_id
            hledej = {"address": adresa}
            if telo["vrf"]:
                hledej["vrf_id"] = telo["vrf"]
            if nb.zaloz("ipam/ip-addresses", hledej, telo):
                pocet += 1
        print(f"    IP adres zpracovano: {pocet}")

    print("\n=== SHRNUTI ===")
    print(f"{'endpoint':32} {'vytvoreno':>10} {'preskoceno':>11}")
    for ep in sorted(set(nb.vytvoreno) | set(nb.preskoceno)):
        print(f"{ep:32} {nb.vytvoreno.get(ep, 0):>10} {nb.preskoceno.get(ep, 0):>11}")
    if args.dry_run:
        print("\nBezelo nasucho, v NetBoxu se nic nezmenilo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
