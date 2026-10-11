"""
NetBox Script: Kontrola komunikační matice proti IP Fabric (verze 2).

Načte CSV s komunikační maticí, pro každý řádek spustí v IP Fabricu
simulaci cesty a porovná skutečnost s očekáváním. Nálezy naváže na
zařízení v NetBoxu, takže z každého řádku vede odkaz na kartu prvku,
a na konci vypíše souhrn seskupený podle závažnosti.

Přihlašovací údaje se čtou z prostředí kontejneru:
    IPF_URL, IPF_USER, IPF_PASS, volitelně IPF_SNAPSHOT

Formát CSV (hlavička povinná):
    name,src,dst,proto,port,expected
"""

import csv
import http.cookiejar
import io
import json
import os
import urllib.error
import urllib.request

from ipam.models import IPAddress
from extras.scripts import Script, FileVar, StringVar

name = "Komunikační matice v2"

_STAV = "/opt/netbox/netbox/media/matice_posledni.json"
_ZALOHA_CESTA = "/opt/netbox/netbox/scripts/matice-demo2.csv"
_ZALOHA_SNAPSHOT = "22443e66-2430-4a55-b953-d7601b3f5148"


def _nacti_posledni(klic, zaloha):
    """Vrati hodnotu z posledniho behu, jinak zalozni."""
    try:
        import json as _json
        with open(_STAV, encoding="utf-8") as f:
            return (_json.load(f).get(klic) or "").strip() or zaloha
    except Exception:
        return zaloha


def _uloz_posledni(cesta, snapshot):
    try:
        import json as _json
        with open(_STAV, "w", encoding="utf-8") as f:
            _json.dump({"cesta": cesta, "snapshot": snapshot}, f)
    except Exception:
        pass


_VYCHOZI_CESTA = _nacti_posledni("cesta", _ZALOHA_CESTA)
_VYCHOZI_SNAPSHOT = _nacti_posledni("snapshot", _ZALOHA_SNAPSHOT)

PORUSENI = "PORUŠENÍ MATICE"
CHYBI = "CHYBÍ PRAVIDLO"
NEDOSTUPNE = "NEDOSTUPNÉ (routing)"
CASTECNE = "ČÁSTEČNĚ"
CHYBA = "CHYBA DOTAZU"
OK = "OK"

ZAVAZNOST = [PORUSENI, CHYBI, NEDOSTUPNE, CASTECNE, CHYBA]

VYSVETLENI = {
    PORUSENI: "zakázaná komunikace prochází - řeší bezpečnost",
    CHYBI: "povolená komunikace je zahozena firewallem - řeší správce pravidel",
    NEDOSTUPNE: "zahozeno bez účasti firewallu, chybí trasa - řeší síťař",
    CASTECNE: "část provozu projde a část ne - vyžaduje ruční posouzení",
    CHYBA: "dotaz do IP Fabricu selhal",
}


class IPFabricClient:
    """Minimalistický klient k IP Fabric API, autentizace přes cookies."""

    def __init__(self, base_url, user, password, timeout=60):
        self.base = base_url.rstrip("/")
        self.timeout = timeout
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )
        self._request("POST", "/api/auth/login",
                      {"username": user, "password": password})
        if not len(self.jar):
            raise RuntimeError("Přihlášení k IP Fabric selhalo.")
        self._request("GET", "/api/users/me")

    def _request(self, metoda, cesta, telo=None):
        url = f"{self.base}{cesta}"
        data = json.dumps(telo).encode("utf-8") if telo is not None else None
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method=metoda
        )
        with self.opener.open(req, timeout=self.timeout) as resp:
            obsah = resp.read().decode("utf-8")
        return json.loads(obsah) if obsah else {}

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
        return self._request("POST", "/api/graphs",
                             {"snapshot": snapshot, "parameters": parameters})


def _soucet(topic):
    return sum(int(v) for v in (topic or {}).values())


def vyhodnot(odpoved, ocekavani):
    pl = odpoved.get("pathlookup", {})
    prochazi = pl.get("passingTraffic")
    topics = pl.get("eventsSummary", {}).get("topics", {})
    hopu = len(pl.get("decisions", {}) or {})

    acl = _soucet(topics.get("ACL"))
    zonefw = _soucet(topics.get("ZONEFW"))
    duvody = []
    for klic in ("ACL", "ZONEFW", "FORWARDING", "NAT44", "PBR"):
        pocet = _soucet(topics.get(klic))
        if pocet:
            duvody.append(f"{klic}({pocet})")
    blokuje = ", ".join(duvody) or "nic neblokuje"

    skutecnost = {"all": "allow", "none": "deny"}.get(prochazi, str(prochazi))

    if prochazi not in ("all", "none"):
        verdikt, uroven = CASTECNE, "warning"
    elif ocekavani == "allow" and prochazi == "all":
        verdikt, uroven = OK, "success"
    elif ocekavani == "deny" and prochazi == "none":
        verdikt, uroven = OK, "success"
    elif ocekavani == "deny" and prochazi == "all":
        verdikt, uroven = PORUSENI, "failure"
    elif ocekavani == "allow" and prochazi == "none":
        if acl or zonefw:
            verdikt, uroven = CHYBI, "failure"
        else:
            verdikt, uroven = NEDOSTUPNE, "warning"
    else:
        verdikt, uroven = CASTECNE, "warning"

    return skutecnost, verdikt, uroven, hopu, blokuje


class KontrolaKomunikacniMaticeV2(Script):
    class Meta:
        name = "Kontrola komunikační matice — v2 s odkazy na zařízení"
        description = ("Ověří každý řádek komunikační matice simulací cesty "
                       "v IP Fabricu, naváže nálezy na zařízení v NetBoxu "
                       "a na konci vypíše souhrn podle závažnosti.")
        commit_default = False
        scheduling_enabled = True

    matice = FileVar(
        description="CSV s komunikační maticí (name,src,dst,proto,port,expected)",
        required=False,
    )
    cesta = StringVar(
        description="Cesta k CSV uvnitř kontejneru (předvyplněno z posledního běhu)",
        default=_VYCHOZI_CESTA,
        required=False,
    )
    snapshot = StringVar(
        description="ID snapshotu v IP Fabricu (předvyplněno z posledního běhu)",
        default=_VYCHOZI_SNAPSHOT,
        required=False,
    )

    def zaloguj(self, uroven, zprava, objekt=None):
        metoda = {
            "success": self.log_success,
            "warning": self.log_warning,
            "failure": self.log_failure,
            "info": self.log_info,
        }[uroven]
        if objekt is None:
            metoda(zprava)
            return
        try:
            metoda(zprava, obj=objekt)
        except TypeError:
            metoda(zprava)

    def run(self, data, commit):
        url = os.environ.get("IPF_URL")
        user = os.environ.get("IPF_USER")
        pwd = os.environ.get("IPF_PASS")
        snapshot = (data.get("snapshot") or os.environ.get("IPF_SNAPSHOT")
                    or "$last")

        if not (url and user and pwd):
            self.log_failure("Chybí proměnné prostředí IPF_URL, IPF_USER nebo IPF_PASS. "
                             "Doplňte je do env/netbox.env a restartujte stack.")
            return "Neprovedeno: chybějící konfigurace."

        try:
            ipf = IPFabricClient(url, user, pwd)
        except Exception as e:
            self.log_failure(f"Připojení k IP Fabricu selhalo: {e}")
            return "Neprovedeno: nelze se připojit."

        self.log_info(f"Připojeno k {url}, snapshot {snapshot}")

        podle_ip = {}
        for adresa in IPAddress.objects.all():
            podle_ip[str(adresa.address.ip)] = adresa

        def zarizeni_podle_ip(ip):
            adresa = podle_ip.get(ip.split("/")[0])
            if not adresa:
                return None
            return getattr(adresa.assigned_object, "device", None)

        soubor = data.get("matice")
        cesta_csv = (data.get("cesta") or "").strip()
        if soubor:
            obsah = soubor.read()
        elif cesta_csv:
            with open(cesta_csv, "rb") as f:
                obsah = f.read()
        else:
            self.log_failure("Zadejte soubor s maticí, nebo cestu k němu.")
            return "Neprovedeno: chybí vstupní matice."
        if isinstance(obsah, bytes):
            obsah = obsah.decode("utf-8-sig")
        radky = list(csv.DictReader(io.StringIO(obsah)))
        _uloz_posledni(cesta_csv, snapshot)

        povinne = {"name", "src", "dst", "proto", "port", "expected"}
        if not radky or not povinne.issubset(set(radky[0].keys())):
            self.log_failure(f"CSV musí mít sloupce: {', '.join(sorted(povinne))}")
            return "Neprovedeno: špatný formát matice."

        self.log_info(f"Řádků matice: {len(radky)}, adres v NetBoxu: {len(podle_ip)}")

        pocty = {}
        vysledky = []
        nalezy = {}

        for r in radky:
            nazev = r["name"].strip()
            src = r["src"].strip()
            dst = r["dst"].strip()
            proto = r["proto"].strip().lower()
            port = r["port"].strip()
            ocekavani = r["expected"].strip().lower()
            cil = zarizeni_podle_ip(dst)
            zdroj = zarizeni_podle_ip(src)
            objekt = cil or zdroj

            try:
                odpoved = ipf.path_lookup(snapshot, src, dst, proto, port)
                skutecnost, verdikt, uroven, hopu, blokuje = vyhodnot(odpoved, ocekavani)
                zprava = (f"{verdikt} · {nazev} · {src} → {dst} {proto}/{port} · "
                          f"očekáváno {ocekavani}, skutečnost {skutecnost} · "
                          f"{hopu} hopů · {blokuje}")
            except urllib.error.HTTPError as e:
                try:
                    detail = e.read().decode("utf-8")[:200]
                except Exception:
                    detail = ""
                skutecnost, verdikt, uroven, hopu, blokuje = "", CHYBA, "warning", 0, "-"
                zprava = f"{CHYBA} · {nazev} · HTTP {e.code} {detail}"
            except Exception as e:
                skutecnost, verdikt, uroven, hopu, blokuje = "", CHYBA, "warning", 0, "-"
                zprava = f"{CHYBA} · {nazev} · {e}"

            self.zaloguj(uroven, zprava, objekt)

            pocty[verdikt] = pocty.get(verdikt, 0) + 1
            if verdikt != OK:
                nalezy.setdefault(verdikt, []).append(
                    (nazev, src, dst, proto, port, hopu, blokuje, objekt)
                )
            vysledky.append({
                "name": nazev, "src": src, "dst": dst, "proto": proto,
                "port": port, "expected": ocekavani, "actual": skutecnost,
                "verdict": verdikt, "hops": hopu, "blocked_by": blokuje,
                "device": cil.name if cil else "",
            })

        vystup = io.StringIO()
        w = csv.DictWriter(vystup, fieldnames=list(vysledky[0].keys()))
        w.writeheader()
        w.writerows(vysledky)

        self.log_info("──────── SOUHRN ────────")
        self.log_info(f"V pořádku: {pocty.get(OK, 0)} z {len(radky)}")

        for verdikt in ZAVAZNOST:
            polozky = nalezy.get(verdikt)
            if not polozky:
                continue
            self.log_info(f"{verdikt} — {len(polozky)}× — {VYSVETLENI[verdikt]}")
            for nazev, src, dst, proto, port, hopu, blokuje, objekt in polozky:
                self.zaloguj(
                    "failure" if verdikt in (PORUSENI, CHYBI) else "warning",
                    f"    {nazev} · {src} → {dst} {proto}/{port} · {hopu} hopů · {blokuje}",
                    objekt,
                )

        problemy = pocty.get(PORUSENI, 0) + pocty.get(CHYBI, 0)
        if problemy:
            self.log_failure(f"Nalezeno {problemy} problémů vyžadujících zásah.")
        else:
            self.log_success("Žádné porušení matice ani chybějící pravidla.")

        return vystup.getvalue()
