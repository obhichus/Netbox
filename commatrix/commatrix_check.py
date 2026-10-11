#!/usr/bin/env python3
"""
Kontrola komunikacni matice proti realnemu stavu site v IP Fabric.

Pro kazdy radek matice spusti v IP Fabricu simulaci cesty (path lookup)
a porovna skutecny vysledek s ocekavanim. Vystupem je report CSV
a shrnuti na obrazovce.

Pouziti:
    python3 commatrix_check.py matrix.csv
    python3 commatrix_check.py matrix.csv --snapshot <id> --out report.csv

Konfigurace se cte ze souboru ipf.env ve stejnem adresari:
    IPF_URL=https://guided-demo.eu.ipfabric.io
    IPF_USER=jmeno
    IPF_PASS=heslo
    IPF_SNAPSHOT=$last

Format vstupni matice (CSV, hlavicka povinna):
    name,src,dst,proto,port,expected
    Web z DMZ,10.0.0.30,10.0.0.40,tcp,443,allow
    Telnet odkudkoli,10.0.0.30,10.0.0.40,tcp,23,deny
"""

import argparse
import csv
import json
import os
import sys
import http.cookiejar
import urllib.error
import urllib.request
from pathlib import Path

VERDIKT_OK = "OK"
VERDIKT_PORUSENI = "PORUSENI MATICE"
VERDIKT_CHYBI = "CHYBI PRAVIDLO"
VERDIKT_ROUTING = "NEDOSTUPNE (routing)"
VERDIKT_CASTECNE = "CASTECNE"
VERDIKT_CHYBA = "CHYBA DOTAZU"


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
    """Klient k IP Fabric API.

    Autentizace je cookie-based: /api/auth/login nastavi cookies,
    ktere pak nese kazdy dalsi pozadavek. Zadny Bearer token se nepouziva.
    """

    def __init__(self, base_url, user, password, timeout=60):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )
        self._login(user, password)

    def _request(self, metoda, cesta, telo=None, hlavicky=None):
        url = f"{self.base}{cesta}"
        data = json.dumps(telo).encode("utf-8") if telo is not None else None
        h = {"Content-Type": "application/json"}
        if hlavicky:
            h.update(hlavicky)
        req = urllib.request.Request(url, data=data, headers=h, method=metoda)
        with self.opener.open(req, timeout=self.timeout) as resp:
            telo_odpovedi = resp.read().decode("utf-8")
        return json.loads(telo_odpovedi) if telo_odpovedi else {}

    def _login(self, user, password):
        self._request("POST", "/api/auth/login",
                      {"username": user, "password": password})
        if not len(self.jar):
            raise RuntimeError("Prihlaseni selhalo, server nenastavil zadne cookies.")
        try:
            self._request("GET", "/api/users/me")
        except Exception as e:
            raise RuntimeError(f"Prihlaseni selhalo, overeni uzivatele neproslo: {e}")

    @property
    def _auth(self):
        return {}

    def snapshoty(self):
        return self._request("GET", "/api/snapshots")

    def path_lookup(self, snapshot, src, dst, proto, port):
        parameters = {
            "pathLookupType": "unicast",
            "networkMode": False,
            "startingPoint": src if "/" in src else f"{src}/32",
            "destinationPoint": dst if "/" in dst else f"{dst}/32",
            "type": "pathLookup",
            "groupBy": "siteName",
            "protocol": proto,
            "ttl": 128,
            "fragmentOffset": 0,
            "securedPath": True,
            "enableRegions": False,
            "srcRegions": ".*",
            "dstRegions": ".*",
            "otherOptions": {"applications": ".*", "tracked": False,
                             "category": "", "url": ""},
            "firstHopAlgorithm": {"type": "automatic"},
        }
        if proto == "tcp":
            parameters["l4Options"] = {"srcPorts": "1024-65535",
                                       "dstPorts": str(port), "flags": []}
        elif proto == "udp":
            parameters["l4Options"] = {"srcPorts": "1024-65535",
                                       "dstPorts": str(port)}
        elif proto == "icmp":
            parameters["l4Options"] = {"type": 0, "code": 0}
        telo = {"snapshot": snapshot, "parameters": parameters}
        return self._request("POST", "/api/graphs", telo, self._auth)


def soucet(topic):
    return sum(int(v) for v in (topic or {}).values())


def vyhodnot(odpoved, ocekavani):
    pl = odpoved.get("pathlookup", {})
    prochazi = pl.get("passingTraffic")
    topics = pl.get("eventsSummary", {}).get("topics", {})
    hopu = len(pl.get("decisions", {}) or {})

    acl = soucet(topics.get("ACL"))
    zonefw = soucet(topics.get("ZONEFW"))
    forwarding = soucet(topics.get("FORWARDING"))
    nat = soucet(topics.get("NAT44"))
    pbr = soucet(topics.get("PBR"))

    duvody = []
    if acl:
        duvody.append(f"ACL({acl})")
    if zonefw:
        duvody.append(f"ZONEFW({zonefw})")
    if forwarding:
        duvody.append(f"FORWARDING({forwarding})")
    if nat:
        duvody.append(f"NAT44({nat})")
    if pbr:
        duvody.append(f"PBR({pbr})")
    blokuje = ",".join(duvody) or "-"

    if prochazi == "all":
        skutecnost = "allow"
    elif prochazi == "none":
        skutecnost = "deny"
    else:
        skutecnost = str(prochazi)

    if prochazi not in ("all", "none"):
        verdikt = VERDIKT_CASTECNE
    elif ocekavani == "allow" and prochazi == "all":
        verdikt = VERDIKT_OK
    elif ocekavani == "deny" and prochazi == "none":
        verdikt = VERDIKT_OK
    elif ocekavani == "deny" and prochazi == "all":
        verdikt = VERDIKT_PORUSENI
    elif ocekavani == "allow" and prochazi == "none":
        if acl or zonefw:
            verdikt = VERDIKT_CHYBI
        else:
            verdikt = VERDIKT_ROUTING
    else:
        verdikt = VERDIKT_CASTECNE

    return skutecnost, verdikt, hopu, blokuje


def main():
    parser = argparse.ArgumentParser(description="Kontrola komunikacni matice proti IP Fabric")
    parser.add_argument("matrix", help="CSV soubor s komunikacni matici")
    parser.add_argument("--snapshot", help="ID snapshotu (jinak z ipf.env nebo $last)")
    parser.add_argument("--out", default="report.csv", help="vystupni CSV report")
    parser.add_argument("--env", default=None, help="cesta k ipf.env")
    args = parser.parse_args()

    adresar = Path(__file__).resolve().parent
    env_cesta = Path(args.env) if args.env else adresar / "ipf.env"
    conf = nacti_env(env_cesta)

    url = os.environ.get("IPF_URL") or conf.get("IPF_URL")
    user = os.environ.get("IPF_USER") or conf.get("IPF_USER")
    pwd = os.environ.get("IPF_PASS") or conf.get("IPF_PASS")
    snapshot = args.snapshot or os.environ.get("IPF_SNAPSHOT") or conf.get("IPF_SNAPSHOT") or "$last"

    if not (url and user and pwd):
        print(f"Chybi konfigurace. Vytvor {env_cesta} s IPF_URL, IPF_USER a IPF_PASS.", file=sys.stderr)
        return 2

    try:
        ipf = IPFabric(url, user, pwd)
    except Exception as e:
        print(f"Nelze se pripojit k IP Fabric: {e}", file=sys.stderr)
        return 2

    print(f"Pripojeno k {url}")
    print(f"Snapshot: {snapshot}")

    with open(args.matrix, newline="", encoding="utf-8") as f:
        radky = list(csv.DictReader(f))

    povinne = {"name", "src", "dst", "proto", "port", "expected"}
    if not radky or not povinne.issubset(set(radky[0].keys())):
        print(f"Matice musi mit sloupce: {', '.join(sorted(povinne))}", file=sys.stderr)
        return 2

    print(f"Radku matice: {len(radky)}\n")

    vysledky = []
    pocty = {}

    for i, r in enumerate(radky, 1):
        nazev = r["name"].strip()
        src = r["src"].strip()
        dst = r["dst"].strip()
        proto = r["proto"].strip().lower()
        port = r["port"].strip()
        ocekavani = r["expected"].strip().lower()

        try:
            odpoved = ipf.path_lookup(snapshot, src, dst, proto, port)
            skutecnost, verdikt, hopu, blokuje = vyhodnot(odpoved, ocekavani)
            chyba = ""
        except urllib.error.HTTPError as e:
            skutecnost, verdikt, hopu, blokuje = "", VERDIKT_CHYBA, 0, "-"
            try:
                detail = e.read().decode("utf-8")[:200].replace("\n", " ")
            except Exception:
                detail = ""
            chyba = f"HTTP {e.code} {detail}"
        except Exception as e:
            skutecnost, verdikt, hopu, blokuje = "", VERDIKT_CHYBA, 0, "-"
            chyba = str(e)[:120]

        pocty[verdikt] = pocty.get(verdikt, 0) + 1
        znacka = "OK  " if verdikt == VERDIKT_OK else "!!! "
        print(f"{znacka}[{i:3}/{len(radky)}] {nazev[:38]:38} {src:15} -> {dst:15} "
              f"{proto}/{port:5} ocek={ocekavani:5} skut={skutecnost:5} {verdikt} {blokuje} {chyba}")

        vysledky.append({
            "name": nazev, "src": src, "dst": dst, "proto": proto, "port": port,
            "expected": ocekavani, "actual": skutecnost, "verdict": verdikt,
            "hops": hopu, "blocked_by": blokuje, "error": chyba,
        })

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(vysledky[0].keys()))
        w.writeheader()
        w.writerows(vysledky)

    print("\n=== SHRNUTI ===")
    for k in (VERDIKT_OK, VERDIKT_PORUSENI, VERDIKT_CHYBI, VERDIKT_ROUTING,
              VERDIKT_CASTECNE, VERDIKT_CHYBA):
        if pocty.get(k):
            print(f"{k:24} {pocty[k]}")
    print(f"\nReport ulozen: {args.out}")

    problemy = pocty.get(VERDIKT_PORUSENI, 0) + pocty.get(VERDIKT_CHYBI, 0)
    return 1 if problemy else 0


if __name__ == "__main__":
    sys.exit(main())
