"""
NetBox Script: Přehled firewallových pravidel z IP Fabric.

Nedělá simulaci cest. Popisuje, jak jsou pravidla napsaná — kolik jich
omezuje zdroj, cíl, protokol a port, kolik je neaktivních a na kterých
prvcích jich je nejvíc. Výstupem je buď seznam širokých povolení
k revizi, nebo přehled po jednotlivých prvcích.

Definice použité v přehledu:
    libovolný zdroj      ipSrc chybí, je prázdný nebo obsahuje 0.0.0.0/0 či ::/0
    libovolný cíl        totéž pro ipDst
    libovolný protokol   ipProtocol chybí, je prázdný nebo 'any'
    bez omezení portu    žádný z dstPorts, tcpDst, udpDst, l4Dst není vyplněný
    široké povolení      pravidlo povoluje a zároveň neomezuje zdroj ani protokol

Přihlašovací údaje se čtou z prostředí kontejneru:
    IPF_URL, IPF_USER, IPF_PASS
"""

import collections
import csv
import http.cookiejar
import io
import json
import os
import re
import urllib.error
import urllib.request

from extras.scripts import Script, StringVar, ChoiceVar

name = "Firewallová pravidla"

_STAV = "/opt/netbox/netbox/media/matice_posledni.json"
_ZALOHA_SNAPSHOT = "22443e66-2430-4a55-b953-d7601b3f5148"

TABULKY = ["security/acl", "security/zone-firewall/policies"]
OBECNE = {"0.0.0.0/0", "::/0", "any", "", "0.0.0.0", "none"}
POVOLUJE = {"allow", "permit", "accept"}
ZAKAZUJE = {"deny", "drop", "reject", "discard"}


def _nacti_posledni(klic, zaloha):
    try:
        with open(_STAV, encoding="utf-8") as f:
            return (json.load(f).get(klic) or "").strip() or zaloha
    except Exception:
        return zaloha


_VYCHOZI_SNAPSHOT = _nacti_posledni("snapshot", _ZALOHA_SNAPSHOT)


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


class IPFabricClient:
    """Minimalistický klient k IP Fabric API, autentizace přes cookies."""

    def __init__(self, base_url, user, password, timeout=180):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.raw("POST", "/api/auth/login",
                 {"username": user, "password": password})
        if not len(self.jar):
            raise RuntimeError("Přihlášení k IP Fabric selhalo.")

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


class PrehledFirewallovychPravidel(Script):
    class Meta:
        name = "Přehled firewallových pravidel"
        description = ("Popíše, jak jsou pravidla napsaná: kolik jich neomezuje "
                       "zdroj, cíl, protokol či port, kolik je neaktivních a kde "
                       "jich je nejvíc. Nedělá simulaci cest.")
        commit_default = False
        scheduling_enabled = True

    snapshot = StringVar(
        description="ID snapshotu v IP Fabricu (předvyplněno z posledního běhu)",
        default=_VYCHOZI_SNAPSHOT,
        required=False,
    )
    vystup = ChoiceVar(
        description="Co má být ve staženém souboru",
        choices=(
            ("siroka", "Široká povolení k revizi"),
            ("prvky", "Přehled po jednotlivých prvcích"),
        ),
        default="siroka",
        required=False,
    )

    def run(self, data, commit):
        url = os.environ.get("IPF_URL")
        user = os.environ.get("IPF_USER")
        pwd = os.environ.get("IPF_PASS")
        snapshot = (data.get("snapshot") or "").strip() or _VYCHOZI_SNAPSHOT
        volba = data.get("vystup") or "siroka"

        if not (url and user and pwd):
            self.log_failure("Chybí proměnné prostředí IPF_URL, IPF_USER nebo IPF_PASS.")
            return "Neprovedeno: chybějící konfigurace."

        try:
            ipf = IPFabricClient(url, user, pwd)
        except Exception as e:
            self.log_failure(f"Připojení k IP Fabricu selhalo: {e}")
            return "Neprovedeno: nelze se připojit."

        self.log_info(f"Připojeno k {url}, snapshot {snapshot}")

        vsechna = []
        for tabulka in TABULKY:
            sl = ipf.sloupce(tabulka, snapshot)
            if not sl:
                self.log_warning(f"Tabulka {tabulka} není dostupná.")
                continue
            try:
                radky = ipf.data(tabulka, sl, snapshot)
            except Exception as e:
                self.log_warning(f"Tabulka {tabulka}: {e}")
                continue
            self.log_info(f"{tabulka}: {len(radky)} pravidel")
            for r in radky:
                r["_tabulka"] = tabulka
                vsechna.append(r)

        if not vsechna:
            self.log_failure("Z IP Fabricu se nepodařilo načíst žádná pravidla.")
            return "Neprovedeno: žádná data."

        celkem = len(vsechna)
        aktivni = [r for r in vsechna if r.get("active")]
        z = len(aktivni) or 1

        bez_zdroje = [r for r in aktivni if je_obecne(r.get("ipSrc"))]
        bez_cile = [r for r in aktivni if je_obecne(r.get("ipDst"))]
        bez_protokolu = [r for r in aktivni if je_obecne(r.get("ipProtocol"))]
        bez_portu_sez = [r for r in aktivni if bez_portu(r)]
        konkretni = [r for r in aktivni
                     if not je_obecne(r.get("ipSrc")) and not je_obecne(r.get("ipDst"))]
        siroka = [r for r in aktivni
                  if str(r.get("action") or "").strip().lower() in POVOLUJE
                  and je_obecne(r.get("ipSrc")) and je_obecne(r.get("ipProtocol"))]

        def pct(cast):
            return f"{100.0 * len(cast) / z:.1f} %"

        self.log_info("──────── SOUHRN ────────")
        self.log_info(f"Pravidel celkem: {celkem}, z toho aktivních {len(aktivni)}, "
                      f"neaktivních {celkem - len(aktivni)}")

        akce = collections.Counter(str(r.get("action") or "-").strip().lower() for r in vsechna)
        self.log_info("Rozložení akcí: " + ", ".join(f"{a} {n}×" for a, n in akce.most_common()))

        self.log_info(f"Neomezuje zdroj: {len(bez_zdroje)} ({pct(bez_zdroje)} aktivních)")
        self.log_info(f"Neomezuje cíl: {len(bez_cile)} ({pct(bez_cile)})")
        self.log_info(f"Neomezuje protokol: {len(bez_protokolu)} ({pct(bez_protokolu)})")
        self.log_info(f"Neomezuje cílový port: {len(bez_portu_sez)} ({pct(bez_portu_sez)})")
        self.log_info(f"Omezuje zdroj i cíl: {len(konkretni)} ({pct(konkretni)})")

        if siroka:
            self.log_warning(f"Širokých povolení k revizi: {len(siroka)} "
                             f"({pct(siroka)} aktivních pravidel) — povolují provoz "
                             f"a neomezují ani zdroj, ani protokol.")
        else:
            self.log_success("Žádné pravidlo nepovoluje provoz bez omezení zdroje i protokolu.")

        podle = collections.defaultdict(collections.Counter)
        for r in vsechna:
            c = podle[(r.get("hostname") or "-", r.get("siteName") or "-")]
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

        serazene = sorted(podle.items(), key=lambda x: -x[1]["celkem"])
        self.log_info(f"Prvků s pravidly: {len(serazene)}. Deset s největším počtem:")
        for (host, site), c in serazene[:10]:
            self.log_info(f"    {host} ({site}) · {c['celkem']} pravidel · "
                          f"povoluje {c['povoluje']} · zakazuje {c['zakazuje']} · "
                          f"bez omezení zdroje {c['bez_zdroje']}")

        vystup = io.StringIO()
        if volba == "prvky":
            w = csv.writer(vystup)
            w.writerow(["prvek", "lokalita", "pravidel celkem", "aktivnich",
                        "povoluje", "zakazuje", "neomezuje zdroj"])
            for (host, site), c in serazene:
                w.writerow([host, site, c["celkem"], c["aktivnich"],
                            c["povoluje"], c["zakazuje"], c["bez_zdroje"]])
            self.log_info(f"Ve výstupu je přehled {len(serazene)} prvků.")
        else:
            w = csv.writer(vystup)
            w.writerow(["prvek", "lokalita", "politika", "pravidlo", "akce",
                        "zdroj", "cil", "protokol", "porty"])
            for r in siroka:
                w.writerow([r.get("hostname"), r.get("siteName"), r.get("policyName"),
                            r.get("ruleName"), r.get("action"),
                            "; ".join(seznam(r.get("ipSrc"))) or "libovolny",
                            "; ".join(seznam(r.get("ipDst"))) or "libovolny",
                            "; ".join(seznam(r.get("ipProtocol"))) or "libovolny",
                            "; ".join(seznam(r.get("dstPorts"))) or "bez omezeni"])
            self.log_info(f"Ve výstupu je {len(siroka)} širokých povolení.")

        return vystup.getvalue()
