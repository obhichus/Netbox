#!/usr/bin/env python3
"""
Zmapuje, co vsechno dana instance IP Fabric nabizi.

Pro kazdou tabulku zjisti, zda je pristupna, kolik ma zaznamu
a jake sloupce nabizi. Vysledek ulozi do CSV a volitelne stahne
i samotna data do JSON souboru.

Endpointy se zjistuji primarne z OpenAPI specifikace serveru;
kdyz neni dostupna, pouzije se vestaveny seznam znamych tabulek.

Pouziti:
    python3 ipf_discover.py
    python3 ipf_discover.py --dump data/          stahne i data
    python3 ipf_discover.py --snapshot <id>
    python3 ipf_discover.py --limit 500           kolik radku stahovat pri --dump

Konfigurace se cte z ipf.env ve stejnem adresari:
    IPF_URL, IPF_USER, IPF_PASS, volitelne IPF_SNAPSHOT
"""

import argparse
import csv
import http.cookiejar
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ZNAME_TABULKY = [
    "inventory/sites", "inventory/devices", "inventory/interfaces",
    "inventory/hosts", "inventory/networks", "inventory/part-numbers",
    "inventory/os-versions", "inventory/vendors", "inventory/families",
    "inventory/platforms", "inventory/models", "inventory/phones",
    "inventory/fans", "inventory/modules", "inventory/power-supplies",
    "addressing/managed-devs", "addressing/managed-ip-ipv4",
    "addressing/managed-ip-ipv6", "addressing/arp", "addressing/mac",
    "addressing/nat44", "addressing/ipv6-neighbor-discovery",
    "security/acl", "security/acl/global-policies",
    "security/zone-firewall/policies", "security/zone-firewall/interfaces",
    "security/dmvpn", "security/ipsec/tunnels", "security/ipsec/gateways",
    "security/secure-ports/devices", "security/secure-ports/interfaces",
    "routing/routes-ipv4", "routing/routes-ipv6", "routing/summary/protocols",
    "routing/protocols/bgp/neighbors", "routing/protocols/ospf/neighbors",
    "routing/protocols/eigrp/neighbors", "routing/protocols/is-is/neighbors",
    "routing/protocols/rip/neighbors", "routing/vrf/detail",
    "routing/vrf/summary", "routing/policies/pbr",
    "switching/vlan/device", "switching/vlan/device-summary",
    "switching/vlan/network-summary", "switching/stp/neighbors",
    "switching/stp/bridges", "switching/stp/vlans", "switching/stp/ports",
    "switching/mac/table", "switching/port-channel/member-status",
    "interfaces/transceivers", "interfaces/connectivity-matrix",
    "interfaces/counters/inbound", "interfaces/counters/outbound",
    "interfaces/tunnels/ipv4", "interfaces/tunnels/ipv6",
    "management/configuration", "management/changes", "management/snmp/summary",
    "management/snmp/communities", "management/aaa/servers",
    "management/aaa/lines", "management/aaa/users",
    "management/logging/summary", "management/logging/remote",
    "management/ntp/summary", "management/ntp/sources",
    "management/dns/resolver-settings", "management/dns/resolver-servers",
    "management/telnet-access", "management/licenses",
    "neighbors/all", "neighbors/unmanaged", "neighbors/unidirectional",
    "wireless/controllers", "wireless/access-points", "wireless/radios-detail",
    "wireless/clients", "wireless/ssid-summary",
    "mpls/l3-vpn/pe-routers", "mpls/l3-vpn/pe-vrfs", "mpls/ldp/neighbors",
    "mpls/rsvp/neighbors", "mpls/forwarding",
    "multicast/overview", "multicast/pim/neighbors", "multicast/mroute/overview",
    "fhrp/group-state", "fhrp/group-members", "fhrp/stproot-alignment",
    "load-balancing/virtual-servers", "load-balancing/virtual-servers/pools",
    "load-balancing/pools", "load-balancing/pools/members",
    "qos/policy-maps", "qos/shaping", "qos/policing", "qos/queuing",
    "sdwan/sites", "sdwan/links",
    "cloud/endpoints", "cloud/subnets", "cloud/virtual-machines",
    "platforms/cisco-fex/modules", "platforms/stack/members",
    "platforms/environment-fans", "platforms/environment-power-supplies",
    "port-channels/member-status", "port-channels/inbound-balancing/tables",
    "oam/unidirectional-link-detection/neighbors",
    "serial-ports/connected-devices",
    "dhcp/relay/interfaces", "dhcp/relay/global-stats/summary",
]


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
    def __init__(self, base_url, user, password, timeout=90):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.req("POST", "/api/auth/login",
                 {"username": user, "password": password})
        if not len(self.jar):
            raise RuntimeError("Prihlaseni selhalo.")
        self.req("GET", "/api/users/me")

    def req(self, metoda, cesta, telo=None):
        url = f"{self.base}{cesta}"
        data = json.dumps(telo).encode("utf-8") if telo is not None else None
        r = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"},
            method=metoda)
        with self.opener.open(r, timeout=self.timeout) as resp:
            obsah = resp.read().decode("utf-8")
        return json.loads(obsah) if obsah else {}

    def raw(self, metoda, cesta, telo=None):
        """Vrati (status, telo_jako_text) i pro chybove odpovedi."""
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


def sloupce_z_chyby(text):
    """Z chyby 'Invalid enum value. Expected a | b | c' vytahne seznam sloupcu."""
    m = re.search(r"Expected (.+?), received", text, re.S)
    if not m:
        return []
    return [c.strip().strip("'") for c in m.group(1).split("|")]


def endpointy_z_oas(ipf):
    for cesta in ("/api/oas", "/api/openapi.json", "/api/oas/openapi.json",
                  "/api/v1/oas"):
        status, telo = ipf.raw("GET", cesta)
        if status != 200 or not telo:
            continue
        try:
            spec = json.loads(telo)
        except Exception:
            continue
        cesty = spec.get("paths", {})
        tabulky = sorted(
            p[len("/tables/"):] for p in cesty
            if p.startswith("/tables/") and "post" in cesty[p]
        )
        if tabulky:
            return tabulky, cesta
    return [], None


def main():
    ap = argparse.ArgumentParser(description="Zmapuje tabulky IP Fabric")
    ap.add_argument("--snapshot", help="ID snapshotu")
    ap.add_argument("--out", default="ipf_prehled.csv", help="vystupni CSV")
    ap.add_argument("--dump", metavar="ADRESAR",
                    help="stahnout i data do JSON souboru v tomto adresari")
    ap.add_argument("--limit", type=int, default=1000,
                    help="max radku na tabulku pri --dump")
    ap.add_argument("--env", default=None)
    args = ap.parse_args()

    adresar = Path(__file__).resolve().parent
    conf = nacti_env(Path(args.env) if args.env else adresar / "ipf.env")

    url = os.environ.get("IPF_URL") or conf.get("IPF_URL")
    user = os.environ.get("IPF_USER") or conf.get("IPF_USER")
    pwd = os.environ.get("IPF_PASS") or conf.get("IPF_PASS")
    snapshot = args.snapshot or conf.get("IPF_SNAPSHOT") or "$last"

    if not (url and user and pwd):
        print("Chybi IPF_URL, IPF_USER nebo IPF_PASS.", file=sys.stderr)
        return 2

    ipf = IPFabric(url, user, pwd)
    print(f"Pripojeno k {url}")

    try:
        snaps = ipf.req("GET", "/api/snapshots")
        print(f"Snapshotu: {len(snaps)}")
        for sn in snaps:
            print(f"  {sn.get('id')}  {sn.get('name')}  ({sn.get('status')})")
    except Exception as e:
        print(f"Snapshoty nelze nacist: {e}")

    print(f"Pouzity snapshot: {snapshot}\n")

    tabulky, zdroj = endpointy_z_oas(ipf)
    if tabulky:
        print(f"Seznam tabulek z OpenAPI ({zdroj}): {len(tabulky)}\n")
    else:
        tabulky = ZNAME_TABULKY
        print(f"OpenAPI nedostupna, pouzivam vestaveny seznam: {len(tabulky)}\n")

    if args.dump:
        Path(args.dump).mkdir(parents=True, exist_ok=True)

    vysledky = []
    dostupne = 0

    for i, t in enumerate(tabulky, 1):
        ep = f"/api/tables/{t}"
        status, telo = ipf.raw("POST", ep, {
            "columns": ["NEEXISTUJE"], "snapshot": snapshot,
            "format": {"dataType": "json"},
            "pagination": {"limit": 1, "start": 0}})

        sloupce = sloupce_z_chyby(telo) if status == 422 else []

        if status == 404:
            stav, pocet = "neexistuje", ""
        elif status == 403:
            stav, pocet = "zakazano", ""
        elif not sloupce:
            stav, pocet = f"HTTP {status}", ""
        else:
            prvni = sloupce[0] if sloupce[0] != "id" or len(sloupce) == 1 else sloupce[1]
            st2, telo2 = ipf.raw("POST", ep, {
                "columns": [prvni], "snapshot": snapshot,
                "format": {"dataType": "json"},
                "pagination": {"limit": 1, "start": 0}})
            if st2 == 200:
                pocet = json.loads(telo2).get("_meta", {}).get("count", "")
                stav = "ok"
                dostupne += 1
            else:
                stav, pocet = f"HTTP {st2}", ""

        print(f"[{i:3}/{len(tabulky)}] {stav:12} {str(pocet):>8}  {t}")

        vysledky.append({
            "table": t, "endpoint": ep, "status": stav, "count": pocet,
            "n_columns": len(sloupce), "columns": " ".join(sloupce),
        })

        if args.dump and stav == "ok" and pocet:
            st3, telo3 = ipf.raw("POST", ep, {
                "columns": sloupce, "snapshot": snapshot,
                "format": {"dataType": "json"},
                "pagination": {"limit": args.limit, "start": 0}})
            if st3 == 200:
                soubor = Path(args.dump) / (t.replace("/", "__") + ".json")
                soubor.write_text(
                    json.dumps(json.loads(telo3).get("data", []),
                               indent=2, ensure_ascii=False),
                    encoding="utf-8")

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(vysledky[0].keys()))
        w.writeheader()
        w.writerows(vysledky)

    s_daty = [v for v in vysledky if v["status"] == "ok" and v["count"]]
    print(f"\n=== SHRNUTI ===")
    print(f"Zkouseno tabulek:   {len(vysledky)}")
    print(f"Dostupnych:         {dostupne}")
    print(f"S daty:             {len(s_daty)}")
    print(f"\nNejvetsi tabulky:")
    for v in sorted(s_daty, key=lambda x: int(x["count"]), reverse=True)[:20]:
        print(f"  {str(v['count']):>8}  {v['table']}")
    print(f"\nPrehled ulozen: {args.out}")
    if args.dump:
        print(f"Data ulozena do: {args.dump}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
