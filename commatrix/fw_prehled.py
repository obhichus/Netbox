"""Prehled kvality bezpecnostnich pravidel z IP Fabric.

Nedela simulaci cest. Jen popisuje, jak jsou pravidla napsana:
kolik jich omezuje zdroj, cil, protokol a port, kolik je neaktivnich
a na kterych prvcich jich je nejvic.

Definice pouzite v prehledu:
  "libovolny zdroj"    ipSrc chybi, je prazdny nebo obsahuje 0.0.0.0/0 resp. ::/0
  "libovolny cil"      totez pro ipDst
  "libovolny protokol" ipProtocol chybi, je prazdny nebo 'any'
  "bez omezeni portu"  zadny z dstPorts, tcpDst, udpDst, l4Dst neni vyplneny
  "siroke povoleni"    akce povoluje a zaroven neomezuje zdroj ani protokol

Spousteni na hostiteli:
    python3 /opt/commatrix/fw_prehled.py
"""

import collections
import csv
import os
import sys

sys.path.insert(0, "/opt/commatrix")
from fw_discover import IPFabric, nacti_env

TABULKY = ["security/acl", "security/zone-firewall/policies"]
VYSTUP_ZARIZENI = "/opt/commatrix/fw_prehled.csv"
VYSTUP_SIROKA = "/opt/commatrix/fw_siroka_pravidla.csv"

OBECNE = {"0.0.0.0/0", "::/0", "any", "", "0.0.0.0", "none"}
POVOLUJE = {"allow", "permit", "accept"}
ZAKAZUJE = {"deny", "drop", "reject", "discard"}


def seznam(hodnota):
    if hodnota is None:
        return []
    if isinstance(hodnota, list):
        return [str(x).strip() for x in hodnota if x not in (None, "")]
    text = str(hodnota).strip()
    return [text] if text else []


def je_obecne(hodnota):
    polozky = seznam(hodnota)
    if not polozky:
        return True
    return any(p.lower() in OBECNE for p in polozky)


def bez_portu(radek):
    for klic in ("dstPorts", "tcpDst", "udpDst", "l4Dst"):
        for p in seznam(radek.get(klic)):
            if p.lower() not in ("any", "0", "0-65535", "1-65535"):
                return False
    return True


udaje = nacti_env()
ipf = IPFabric(udaje["IPF_URL"], udaje["IPF_USER"], udaje["IPF_PASS"])
snapshot = os.environ.get("IPF_FW_SNAPSHOT") or "22443e66-2430-4a55-b953-d7601b3f5148"
print(f"Pripojeno, snapshot {snapshot}\n")

vsechna = []
for tabulka in TABULKY:
    sloupce, _ = ipf.sloupce(tabulka, snapshot)
    if not sloupce:
        print(f"{tabulka}: nedostupne")
        continue
    data, _ = ipf.vzorek(tabulka, sloupce, snapshot, limit=20000)
    print(f"{tabulka}: {len(data)} pravidel")
    for r in data:
        r["_tabulka"] = tabulka
        vsechna.append(r)

if not vsechna:
    raise SystemExit("Zadna pravidla nenactena.")

celkem = len(vsechna)
aktivni = [r for r in vsechna if r.get("active")]
akce = collections.Counter(str(r.get("action") or "-").strip().lower() for r in vsechna)

bez_zdroje = [r for r in aktivni if je_obecne(r.get("ipSrc"))]
bez_cile = [r for r in aktivni if je_obecne(r.get("ipDst"))]
bez_protokolu = [r for r in aktivni if je_obecne(r.get("ipProtocol"))]
bez_portu_seznam = [r for r in aktivni if bez_portu(r)]
konkretni = [r for r in aktivni
             if not je_obecne(r.get("ipSrc")) and not je_obecne(r.get("ipDst"))]

siroka = [r for r in aktivni
          if str(r.get("action") or "").strip().lower() in POVOLUJE
          and je_obecne(r.get("ipSrc")) and je_obecne(r.get("ipProtocol"))]


def procento(cast, zaklad):
    return f"{100.0 * len(cast) / zaklad:5.1f} %" if zaklad else "    - "


print("\n" + "=" * 64)
print(f"pravidel celkem                     {celkem:>6}")
print(f"  z toho aktivnich                  {len(aktivni):>6}   {procento(aktivni, celkem)}")
print(f"  z toho neaktivnich                {celkem - len(aktivni):>6}")
print("\nrozlozeni akci:")
for a, n in akce.most_common():
    print(f"   {n:>6}x  {a}")

print("\nz aktivnich pravidel:")
z = len(aktivni)
print(f"  neomezuje zdroj                   {len(bez_zdroje):>6}   {procento(bez_zdroje, z)}")
print(f"  neomezuje cil                     {len(bez_cile):>6}   {procento(bez_cile, z)}")
print(f"  neomezuje protokol                {len(bez_protokolu):>6}   {procento(bez_protokolu, z)}")
print(f"  neomezuje cilovy port             {len(bez_portu_seznam):>6}   {procento(bez_portu_seznam, z)}")
print(f"  omezuje zdroj i cil               {len(konkretni):>6}   {procento(konkretni, z)}")
print(f"  siroke povoleni (zdroj i protokol){len(siroka):>6}   {procento(siroka, z)}")

podle_zarizeni = collections.defaultdict(lambda: collections.Counter())
for r in vsechna:
    klic = (r.get("hostname") or "-", r.get("siteName") or "-")
    c = podle_zarizeni[klic]
    c["celkem"] += 1
    if r.get("active"):
        c["aktivnich"] += 1
        a = str(r.get("action") or "").strip().lower()
        if a in POVOLUJE:
            c["povoluje"] += 1
        elif a in ZAKAZUJE:
            c["zakazuje"] += 1
        if je_obecne(r.get("ipSrc")):
            c["bez_zdroje"] += 1

print("\nprvky s nejvice pravidly:")
serazene = sorted(podle_zarizeni.items(), key=lambda x: -x[1]["celkem"])
print(f"   {'prvek':<34}{'lokalita':<16}{'celkem':>7}{'aktiv':>7}{'povol':>7}{'zakaz':>7}{'bez zdroje':>12}")
for (host, site), c in serazene[:12]:
    print(f"   {host[:32]:<34}{site[:14]:<16}{c['celkem']:>7}{c['aktivnich']:>7}"
          f"{c['povoluje']:>7}{c['zakazuje']:>7}{c['bez_zdroje']:>12}")

with open(VYSTUP_ZARIZENI, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["prvek", "lokalita", "pravidel celkem", "aktivnich",
                "povoluje", "zakazuje", "neomezuje zdroj"])
    for (host, site), c in serazene:
        w.writerow([host, site, c["celkem"], c["aktivnich"],
                    c["povoluje"], c["zakazuje"], c["bez_zdroje"]])

with open(VYSTUP_SIROKA, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["prvek", "lokalita", "politika", "pravidlo", "akce",
                "zdroj", "cil", "protokol", "porty"])
    for r in siroka:
        w.writerow([r.get("hostname"), r.get("siteName"), r.get("policyName"),
                    r.get("ruleName"), r.get("action"),
                    "; ".join(seznam(r.get("ipSrc"))) or "libovolny",
                    "; ".join(seznam(r.get("ipDst"))) or "libovolny",
                    "; ".join(seznam(r.get("ipProtocol"))) or "libovolny",
                    "; ".join(seznam(r.get("dstPorts"))) or "bez omezeni"])

print(f"\nzapsano:")
print(f"   {VYSTUP_ZARIZENI}   ({len(serazene)} prvku)")
print(f"   {VYSTUP_SIROKA}   ({len(siroka)} pravidel)")
