"""Prevede bezpecnostni pravidla z IP Fabric na kandidatni komunikacni matici.

Z kazdeho dostatecne konkretniho pravidla udela radek matice. Pravidla
s obecnym zdrojem nebo cilem (0.0.0.0/0), bez portu nebo bez protokolu
prevest nelze - ta se jen spocitaji a vypisi duvody.

Spousteni na hostiteli:
    python3 /opt/commatrix/fw_na_matici.py
"""

import collections
import csv
import ipaddress
import json
import os
import sys

sys.path.insert(0, "/opt/commatrix")
from fw_discover import IPFabric, nacti_env

TABULKY = ["security/acl", "security/zone-firewall/policies"]
VYSTUP = "/opt/commatrix/matice-z-firewallu.csv"
MAX_RADKU = int(os.environ.get("FW_MAX_RADKU", "150"))

PROTOKOLY = {"6": "tcp", "17": "udp", "1": "icmp",
             "tcp": "tcp", "udp": "udp", "icmp": "icmp"}


def prvni(hodnota):
    """Z listu vrati prvni prvek, jinak hodnotu samotnou."""
    if isinstance(hodnota, list):
        return hodnota[0] if hodnota else None
    return hodnota


def hostitel(cidr):
    """Z CIDR vrati reprezentativni adresu, nebo None u obecneho rozsahu."""
    if not cidr:
        return None
    text = str(cidr).strip()
    if text in ("0.0.0.0/0", "::/0", "any", "0.0.0.0"):
        return None
    try:
        sit = ipaddress.ip_network(text, strict=False)
    except ValueError:
        try:
            return str(ipaddress.ip_address(text))
        except ValueError:
            return None
    if sit.version != 4:
        return None
    if sit.prefixlen == 32:
        return str(sit.network_address)
    try:
        return str(next(sit.hosts()))
    except StopIteration:
        return str(sit.network_address)


def protokol(hodnota):
    p = prvni(hodnota)
    if p is None:
        return None
    return PROTOKOLY.get(str(p).strip().lower())


def port(radek):
    for klic in ("dstPorts", "tcpDst", "udpDst", "l4Dst"):
        hodnota = prvni(radek.get(klic))
        if hodnota in (None, "", "any"):
            continue
        text = str(hodnota).strip()
        if text.isdigit():
            return text
        if "-" in text:
            zacatek = text.split("-")[0].strip()
            if zacatek.isdigit() and zacatek != "0":
                return zacatek
    return None


udaje = nacti_env()
ipf = IPFabric(udaje["IPF_URL"], udaje["IPF_USER"], udaje["IPF_PASS"])
snapshot = os.environ.get("IPF_FW_SNAPSHOT") or "22443e66-2430-4a55-b953-d7601b3f5148"
print(f"Pripojeno, snapshot {snapshot}\n")

radky_matice = []
duvody = collections.Counter()
celkem_pravidel = 0

for tabulka in TABULKY:
    sloupce, _ = ipf.sloupce(tabulka, snapshot)
    if not sloupce:
        print(f"{tabulka}: nedostupne")
        continue
    data, pocet = ipf.vzorek(tabulka, sloupce, snapshot, limit=20000)
    print(f"{tabulka}: {len(data)} pravidel")
    celkem_pravidel += len(data)

    for r in data:
        if not r.get("active"):
            duvody["neaktivni pravidlo"] += 1
            continue
        akce = str(r.get("action") or "").strip().lower()
        if akce not in ("allow", "permit", "deny", "drop", "reject"):
            duvody[f"akce '{akce or '-'}' nelze prevest"] += 1
            continue
        src = hostitel(prvni(r.get("ipSrc")))
        dst = hostitel(prvni(r.get("ipDst")))
        if not src:
            duvody["obecny nebo chybejici zdroj"] += 1
            continue
        if not dst:
            duvody["obecny nebo chybejici cil"] += 1
            continue
        proto = protokol(r.get("ipProtocol"))
        if not proto:
            duvody["chybejici nebo neznamy protokol"] += 1
            continue
        if proto == "icmp":
            cislo_portu = "0"
        else:
            cislo_portu = port(r)
            if not cislo_portu:
                duvody["chybejici cilovy port"] += 1
                continue
        nazev = " · ".join(x for x in (
            r.get("hostname"), r.get("policyName"),
            f"pravidlo {r.get('ruleName')}" if r.get("ruleName") else None) if x)
        radky_matice.append({
            "name": (nazev or "pravidlo firewallu")[:120],
            "src": src, "dst": dst, "proto": proto, "port": cislo_portu,
            "expected": "allow" if akce in ("allow", "permit") else "deny",
        })

videno = set()
unikatni = []
for r in radky_matice:
    klic = (r["src"], r["dst"], r["proto"], r["port"], r["expected"])
    if klic in videno:
        duvody["duplicitni kombinace"] += 1
        continue
    videno.add(klic)
    unikatni.append(r)

orezano = unikatni[:MAX_RADKU]

with open(VYSTUP, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["name", "src", "dst", "proto", "port", "expected"])
    w.writeheader()
    w.writerows(orezano)

print(f"\npravidel celkem:        {celkem_pravidel}")
print(f"prevedeno na radky:     {len(radky_matice)}")
print(f"po odstraneni duplicit: {len(unikatni)}")
print(f"zapsano do souboru:     {len(orezano)}  (limit FW_MAX_RADKU={MAX_RADKU})")
print(f"\nduvody, proc pravidlo prevest nelze:")
for duvod, pocet in duvody.most_common():
    print(f"   {pocet:>6}x  {duvod}")
print(f"\nvystup: {VYSTUP}")
