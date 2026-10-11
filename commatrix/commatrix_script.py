"""
NetBox Script: Kontrola komunikacni matice proti IP Fabric.

Nacte CSV s komunikacni matici, pro kazdy radek spusti v IP Fabricu
simulaci cesty (path lookup) a porovna skutecnost s ocekavanim.
Vysledky loguje do vystupu skriptu, takze jsou videt primo ve webu
NetBoxu vcetne historie jednotlivych behu.

Prihlasovaci udaje se ctou z promennych prostredi kontejneru:
    IPF_URL, IPF_USER, IPF_PASS, volitelne IPF_SNAPSHOT

Format CSV (hlavicka povinna):
    name,src,dst,proto,port,expected
    Web z DMZ,10.0.0.30,10.0.0.40,tcp,443,allow
"""

import csv
import http.cookiejar
import io
import json
import os
import urllib.error
import urllib.request

from extras.scripts import Script, FileVar, StringVar

name = "Komunikacni matice"


class IPFabricClient:
    """Minimalisticky klient k IP Fabric API, autentizace pres cookies."""

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
            raise RuntimeError("Prihlaseni k IP Fabric selhalo.")
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
    blokuje = ", ".join(duvody) or "-"

    skutecnost = {"all": "allow", "none": "deny"}.get(prochazi, str(prochazi))

    if prochazi not in ("all", "none"):
        verdikt, uroven = "CASTECNE", "warning"
    elif ocekavani == "allow" and prochazi == "all":
        verdikt, uroven = "OK", "success"
    elif ocekavani == "deny" and prochazi == "none":
        verdikt, uroven = "OK", "success"
    elif ocekavani == "deny" and prochazi == "all":
        verdikt, uroven = "PORUSENI MATICE", "failure"
    elif ocekavani == "allow" and prochazi == "none":
        if acl or zonefw:
            verdikt, uroven = "CHYBI PRAVIDLO", "failure"
        else:
            verdikt, uroven = "NEDOSTUPNE (routing)", "warning"
    else:
        verdikt, uroven = "CASTECNE", "warning"

    return skutecnost, verdikt, uroven, hopu, blokuje


class KontrolaKomunikacniMatice(Script):
    class Meta:
        name = "Kontrola komunikacni matice"
        description = ("Overi kazdy radek komunikacni matice simulaci cesty "
                       "v IP Fabric a oznaci porusení, chybejici pravidla "
                       "a nedostupne cile.")
        commit_default = False
        scheduling_enabled = True

    matice = FileVar(
        description="CSV s komunikacni matici (name,src,dst,proto,port,expected)",
        required=False,
    )
    cesta = StringVar(
        description="Nebo cesta k CSV uvnitr kontejneru, napr. /opt/netbox/netbox/scripts/matice-demo.csv",
        required=False,
    )
    snapshot = StringVar(
        description="ID snapshotu v IP Fabric, prazdne = podle IPF_SNAPSHOT nebo $last",
        required=False,
    )

    def run(self, data, commit):
        url = os.environ.get("IPF_URL")
        user = os.environ.get("IPF_USER")
        pwd = os.environ.get("IPF_PASS")
        snapshot = (data.get("snapshot") or os.environ.get("IPF_SNAPSHOT")
                    or "$last")

        if not (url and user and pwd):
            self.log_failure("Chybi promenne prostredi IPF_URL, IPF_USER nebo IPF_PASS. "
                             "Doplnte je do env/netbox.env a restartujte stack.")
            return "Neprovedeno: chybejici konfigurace."

        try:
            ipf = IPFabricClient(url, user, pwd)
        except Exception as e:
            self.log_failure(f"Pripojeni k IP Fabric selhalo: {e}")
            return "Neprovedeno: nelze se pripojit."

        self.log_info(f"Pripojeno k {url}, snapshot {snapshot}")

        soubor = data.get("matice")
        cesta_csv = (data.get("cesta") or "").strip()
        if soubor:
            obsah = soubor.read()
        elif cesta_csv:
            with open(cesta_csv, "rb") as f:
                obsah = f.read()
        else:
            self.log_failure("Zadejte soubor s matici, nebo cestu k nemu.")
            return "Neprovedeno: chybi vstupni matice."
        if isinstance(obsah, bytes):
            obsah = obsah.decode("utf-8-sig")
        radky = list(csv.DictReader(io.StringIO(obsah)))

        povinne = {"name", "src", "dst", "proto", "port", "expected"}
        if not radky or not povinne.issubset(set(radky[0].keys())):
            self.log_failure(f"CSV musi mit sloupce: {', '.join(sorted(povinne))}")
            return "Neprovedeno: spatny format matice."

        self.log_info(f"Radku matice: {len(radky)}")

        pocty = {}
        vysledky = []

        for i, r in enumerate(radky, 1):
            nazev = r["name"].strip()
            src = r["src"].strip()
            dst = r["dst"].strip()
            proto = r["proto"].strip().lower()
            port = r["port"].strip()
            ocekavani = r["expected"].strip().lower()
            popis = f"{nazev} | {src} -> {dst} {proto}/{port} | ocekavano {ocekavani}"

            try:
                odpoved = ipf.path_lookup(snapshot, src, dst, proto, port)
                skutecnost, verdikt, uroven, hopu, blokuje = vyhodnot(odpoved, ocekavani)
                zprava = f"{popis} | skutecnost {skutecnost} | {verdikt} | {blokuje} | hopu {hopu}"
            except urllib.error.HTTPError as e:
                try:
                    detail = e.read().decode("utf-8")[:200]
                except Exception:
                    detail = ""
                skutecnost, verdikt, uroven, hopu, blokuje = "", "CHYBA DOTAZU", "warning", 0, "-"
                zprava = f"{popis} | CHYBA HTTP {e.code} {detail}"
            except Exception as e:
                skutecnost, verdikt, uroven, hopu, blokuje = "", "CHYBA DOTAZU", "warning", 0, "-"
                zprava = f"{popis} | CHYBA {e}"

            if uroven == "success":
                self.log_success(zprava)
            elif uroven == "warning":
                self.log_warning(zprava)
            else:
                self.log_failure(zprava)

            pocty[verdikt] = pocty.get(verdikt, 0) + 1
            vysledky.append({
                "name": nazev, "src": src, "dst": dst, "proto": proto,
                "port": port, "expected": ocekavani, "actual": skutecnost,
                "verdict": verdikt, "hops": hopu, "blocked_by": blokuje,
            })

        vystup = io.StringIO()
        w = csv.DictWriter(vystup, fieldnames=list(vysledky[0].keys()))
        w.writeheader()
        w.writerows(vysledky)

        shrnuti = " | ".join(f"{k}: {v}" for k, v in sorted(pocty.items()))
        self.log_info(f"Shrnuti: {shrnuti}")

        problemy = pocty.get("PORUSENI MATICE", 0) + pocty.get("CHYBI PRAVIDLO", 0)
        if problemy:
            self.log_failure(f"Nalezeno {problemy} problemu vyzadujicich zasah.")
        else:
            self.log_success("Zadne porusení matice ani chybejici pravidla.")

        return vystup.getvalue()
