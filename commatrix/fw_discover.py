"""Zjisti, ktere tabulky bezpecnostnich pravidel IP Fabric nabizi.

Pouziva stejny trik jako push_ipf_data.py: posle dotaz s neexistujicim
sloupcem, API odpovi 422 a v chybove hlasce vypise platne sloupce.

Spousteni na hostiteli:
    set -a; . /opt/commatrix/ipf.env; set +a
    python3 /opt/commatrix/fw_discover.py
"""

import http.cookiejar
import json
import os
import re
import urllib.error
import urllib.request

KANDIDATI = [
    "security/acl",
    "security/acl/interface",
    "security/acl/global",
    "security/acl/rules",
    "security/policies",
    "security/rules",
    "security/zone-firewall/policies",
    "security/zone-firewall/interfaces",
    "security/firewall/policies",
    "security/firewall/rules",
    "security/nat/rules",
    "security/nat44/rules",
    "security/nat44",
    "security/dmz",
    "security/secure-ports/users",
    "security/ipsec/tunnels",
    "security/ipsec/gateways",
]


class IPFabric:
    def __init__(self, base_url, user, password, timeout=120):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.raw("POST", "/api/auth/login",
                 {"username": user, "password": password})
        if not len(self.jar):
            raise SystemExit("Prihlaseni k IP Fabric selhalo.")

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
            return None, st
        m = re.search(r"Expected (.+?), received", telo, re.S)
        if not m:
            return None, st
        return [c.strip().strip("'") for c in m.group(1).split("|")], st

    def vzorek(self, tabulka, sloupce, snapshot, limit=3):
        st, telo = self.raw("POST", f"/api/tables/{tabulka}", {
            "columns": sloupce, "snapshot": snapshot,
            "format": {"dataType": "json"},
            "pagination": {"limit": limit, "start": 0}})
        if st != 200:
            return [], 0
        odpoved = json.loads(telo)
        return odpoved.get("data", []), odpoved.get("_meta", {}).get("count", 0)


def nacti_env(cesta="/opt/commatrix/ipf.env"):
    """Precte KEY=VALUE primo ze souboru, bez expanze shellem."""
    hodnoty = {}
    try:
        with open(cesta, encoding="utf-8") as f:
            for radek in f:
                radek = radek.strip()
                if not radek or radek.startswith("#") or "=" not in radek:
                    continue
                klic, _, hodnota = radek.partition("=")
                hodnota = hodnota.strip()
                if len(hodnota) >= 2 and hodnota[0] == hodnota[-1] and hodnota[0] in "\"'":
                    hodnota = hodnota[1:-1]
                hodnoty[klic.strip()] = hodnota
    except FileNotFoundError:
        pass
    return hodnoty


_ze_souboru = nacti_env()
url = _ze_souboru.get("IPF_URL") or os.environ.get("IPF_URL")
user = _ze_souboru.get("IPF_USER") or os.environ.get("IPF_USER")
pwd = _ze_souboru.get("IPF_PASS") or os.environ.get("IPF_PASS")
snapshot = os.environ.get("IPF_FW_SNAPSHOT") or "22443e66-2430-4a55-b953-d7601b3f5148"

if not (url and user and pwd):
    raise SystemExit("Chybi IPF_URL, IPF_USER nebo IPF_PASS v prostredi.")

ipf = IPFabric(url, user, pwd)
print(f"Pripojeno k {url}")
print(f"Snapshot: {snapshot}\n")

nalezene = []
for tabulka in KANDIDATI:
    sl, st = ipf.sloupce(tabulka, snapshot)
    if not sl:
        print(f"  -    {tabulka:<40} HTTP {st}")
        continue
    radky, pocet = ipf.vzorek(tabulka, sl, snapshot)
    print(f"  OK   {tabulka:<40} sloupcu {len(sl):>3}   radku {pocet}")
    nalezene.append((tabulka, sl, radky, pocet))

print("\n" + "=" * 70)
for tabulka, sl, radky, pocet in nalezene:
    if not pocet:
        continue
    print(f"\n=== {tabulka}   ({pocet} radku)")
    print("sloupce:", ", ".join(sl))
    if radky:
        print("ukazka prvniho radku:")
        for k, v in radky[0].items():
            if v not in (None, "", [], {}):
                print(f"    {k:<24} {str(v)[:70]}")
