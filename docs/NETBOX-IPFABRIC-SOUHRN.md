# NetBox + IP Fabric — souhrn projektu

> Pozn. k umístění v repu: zdrojáky z části 6.6 jsou v [commatrix/](../commatrix/), export z 6.5
> je [commatrix/export_konfigurace.py](../commatrix/export_konfigurace.py), podrobný postup importu
> v [IMPORT-RUTINA.md](IMPORT-RUTINA.md) a pasti v [ZNAME-PASTI.md](ZNAME-PASTI.md).
> Příloha A proto v repu není potřeba (zdrojáky se do dokumentu nekopírují, jsou vedle).
> Kód v 6.5 je původní verze; v repu je opravená (vynechává `ipfabricingestionissue`, exportuje relační mapy).

Zdroj pravdy o síti pro potřeby kybernetické bezpečnosti, postavený
na NetBoxu, plněný daty z IP Fabric a doplněný o kontrolu komunikační
matice a analýzu firewallových pravidel.

Stav: funkční demo nad veřejnou demo sítí IP Fabric. Dokument popisuje,
co se řešilo, jak to skončilo, čeho se dosáhlo a co se k tomu použilo.

---

## 1. Proč to vzniklo

Ve firmě není žádný zdroj pravdy o síti. IP Fabric už nasazený je, ale ten
popisuje **stav, jaký je** — nikoli stav, jaký **má být**. Komunikační matice,
tedy záměr, proti kterému se realita porovnává, neexistuje v žádné podobě.

Cíl je ukázat, že nad importovanými daty lze:

- držet komunikační matici jako záměr a hlídat její porušení,
- importovat firewallová pravidla a navrhovat nad nimi úpravy,
- a to vše z open source, tedy bez nároku na projektové peníze.

Data o síti jsou citlivá, takže NetBox musí běžet ve firmě, nikoli v cloudu.

---

## 2. Prostředí

| Složka | Verze / umístění |
|---|---|
| NetBox | 4.6.10-Docker-5.0.2 Community |
| Plugin | `ipfabric_netbox` 6.1.0 |
| Branching | `netboxlabs-netbox-branching` 1.1.3 |
| Nasazení | `/opt/netbox-docker` (oficiální projekt netbox-docker) |
| Vlastní skripty | `/opt/commatrix` |
| Stroj | `blue-ThinkCentre-M710s`, Ubuntu 24.04 |
| IP Fabric | demo `guided-demo.eu.ipfabric.io` (7.9.4); ve firmě 7.5 |

Na stroji běží i MISP, který patří majiteli stroje. Nic z jeho dat se nemaže.

Volba oficiálního netbox-docker proti ručně psanému compose byla kvůli podpoře
pluginů — `Dockerfile-Plugins` a `plugin_requirements.txt` jsou součást projektu,
takže instalace pluginu je deklarovaná, ne nalepená dodatečně.

---

## 3. Co běží

```
IP Fabric API
     |
     |  push_ipf_data.py          11 tabulek, zjištění sloupců trikem s HTTP 422
     v
IPFabricData (plugin)
     |
     |  ingestion job ve workeru  transformační mapy -> objekty NetBoxu
     v
NetBox  <-- primarni_ip.py        doplní primary_ip4
        <-- prefixy.py            vytvoří prefixy ze sloupce net
     |
     +-- NetBox Script: Kontrola komunikační matice v2
     |       CSV matice + snapshot -> simulace cesty v IP Fabric -> nálezy
     |
     +-- NetBox Script: Přehled firewallových pravidel
             1732 pravidel -> hygienický přehled + kandidátská matice
```

Oba skripty mají tlačítko v NetBoxu, předvyplněná pole a odkaz na nástěnce.

---

## 4. Co se řešilo a jak to skončilo

Pořadí je chronologické. U každé položky je i to, čím se projevila — to je
při opakování práce cennější než samotné řešení.

### 4.1 Import vůbec nenaběhl — `null value in column "serial"`

Plugin má vlastní Jinja filtr `serial()`, který u sériových čísel delších než
50 znaků vrací `data.get("id")`. Jenže `strip_source_data()` pluginu pole `id`
nikdy nedodává, takže filtr vrátí `None` a databáze import odmítne.

Je to chyba v pluginu. Nelze ji obejít nastavením — musela se přepsat mapa pro
`Device.serial` tak, aby filtr `serial()` nepoužívala vůbec. Vedlo to k zavedení
předpočítaného `nb_serial` (viz 6.1).

Dvě hypotézy, které jsem měl nejdřív — stará data v cache a hostname delší než
64 znaků — byly obě mimo.

### 4.2 Jméno zařízení delší než 64 znaků

Azure VNet zařízení dostalo jméno o 151 znacích. Plugin při kolizi hostname
skládá jméno jako `hostname - (sn)`, a u Azure je samo `sn` dlouhé. Vyřešeno
předpočítaným `nb_name` s krátkým osmiznakovým otiskem místo celého `sn` (6.2).

### 4.3 VRF se při každém importu znásobily — 51 na 151

Naše `normalizuj()` převáděla `rd` na string, takže prázdná hodnota se stala
prázdným řetězcem. NetBox prázdné `rd` ukládá jako NULL, coalesce strategie
pluginu tedy nikdy nenašla existující VRF a zakládala novou.

Prázdný řetězec a NULL nejsou v NetBoxu totéž. Vyřešeno odstraněním `rd`
ze seznamu textových sloupců. Pokud se po importu něco množí, hledá se tady.

### 4.4 Po opravě serialu spadly všechny IP adresy na nulu

Zřetězená příčina, kterou z chybové hlášky `IPAddressPrimaryRemovalError`
nebylo vidět vůbec:

1. v mapě pro `IPAddress` jsme `object.sn` nahradili `object.nb_serial`,
2. plugin si seznam stahovaných sloupců skládá z toho, na co se mapy odkazují,
3. `sn` se tím přestalo stahovat,
4. plugin má ale na řádku 2599 v `ipfutils.py` hardcodované
   `.exclude(serial=serial(ip_address.data))`, které `sn` potřebuje,
5. filtr dostal prázdná data, vyhodil `TypeError`, a ten se projevil
   až jako `IPAddressPrimaryRemovalError` u každé adresy.

Vyřešeno odkazem na obě hodnoty: `{% set SN = object.nb_serial or object.sn %}`.

Na stejnou past jsem o chvíli později narazil znovu — zapomněl jsem mapu
`MACAddress` a ingestion shodil 4618 MAC adres. Když se mění mapa, musí se
projít **všechny** mapy odkazující na stejný sloupec.

### 4.5 Sync zůstal viset ve stavu `ready_to_merge`

Větve jsem mergoval přímo přes `branch.merge()`. Tím se obejde stavový automat
pluginu: větev je zmergovaná, ale plugin o tom neví a svůj záznam nepřepne.
Správná cesta je `enqueue_merge_job(user=..., remove_branch=True)`, případně
zapnout `auto_merge` na zdroji. Moje chyba.

### 4.6 Job spadl na timeout

Ingestion 7914 záznamů nestihne výchozích 300 sekund. Proměnná v `env/netbox.env`
se neuplatnila; funguje až `RQ_DEFAULT_TIMEOUT = 7200` v
`configuration/extra.py`, který je bind-mountovaný, takže stačí restart.

### 4.7 Prefixy — 70 chyb u IPv6

Sloupec `net` obsahuje i zápisy host s maskou (`beef:37:1::5/64`), což není
platný prefix. Vyřešeno `ipaddress.ip_network(hodnota, strict=False)`.

### 4.8 Kontrola matice hlásila 14 porušení, která neexistovala

Nejnebezpečnější chyba z celého projektu, protože výsledek vypadal věrohodně
a šel by předvést jako skutečný nález.

Jako zdroj jsem použil management IP adresu pražského firewallu. Provoz, který
z firewallu sám vychází, umře na jeho vlastní zone policy už na prvním hopu.
Vyřešeno použitím IP adresy switche.

Diagnostický podpis: ve výstupu simulace je `hopu 1` nebo `hopu 2` spolu
s `FORWARDING(1)`. Když to vidíš, chyba není v pravidlech, ale ve zdrojové
adrese řádku matice.

### 4.9 Rozpor v počtu aktivních rozhraní

Proti dashboardu IP Fabric vyšlo 2608 vs. 2738. Není to chyba importu:
IP Fabric počítá rozhraní s nahozenou vrstvou l1 **a zároveň** l2 — ověřeno
dotazem, vyjde přesně 2608 — kdežto NetBoxové `enabled` znamená administrativně
povolené. Jsou to dvě různé věci a nelze je srovnávat.

### 4.10 Přihlášení k IP Fabric selhávalo

Heslo obsahuje `$` a `*`. Načtení přes `set -a ; . ipf.env` je nechá shellem
expandovat a do API odejde jiné heslo. Skripty si proto `ipf.env` parsují samy
v Pythonu.

### 4.11 Drobnosti kolem NetBox Scriptů

- `Error loading script: invalid syntax (matice-demo.csv, line 2)` — CSV byl
  nahrán na formuláři *Add Script*; matice se nahrává až na spouštěcím formuláři.
- `_log() got an unexpected keyword argument 'level'` — pomocnou funkci jsem
  pojmenoval `_log` a překryl tím `Script._log`. Přejmenováno na `zaloguj`.
- Tlačítko *Browse* nereagovalo — problém prohlížeče, ne NetBoxu; oba skripty
  proto mají i textové pole s cestou.
- Skripty běží ve **workeru**, takže soubor musí existovat v obou kontejnerech
  a patřit uživateli `netbox` (uid 999).
- Česká lokalizace NetBoxu přeložila *Jobs* jako „Pracovní místa“ (`/core/jobs/`).

### 4.12 Retence změn

Výchozích 90 dní bylo na dokazování málo. Stránka *Admin → Configuration* je
jen zobrazení aktuální revize; mění se zakládáním nové `ConfigRevision`.
Nastaveno `CHANGELOG_RETENTION = 0` a `JOB_RETENTION = 0`, tedy nemazat nikdy.

Důsledek, se kterým je třeba počítat: databázi už nic nezmenší. Jeden import
přidá řádově 2000 záznamů do protokolu změn. Výchozí bod 39 856 změn a 123 MB.

---

## 5. Čeho se dosáhlo

**Import** — opakovatelný, idempotentní, s offline režimem pro práci bez
přístupu k API.

Ověřeno proti dashboardu IP Fabric (snapshot `22443e66`, Network Audit
Evidence, 2024-11-12):

| | IP Fabric | NetBox |
|---|---|---|
| zařízení | 365 | 365 |
| rozhraní | 4618 | 4618 |
| lokality | 21 | 21 |
| aktivní rozhraní | 2608 | 2738 — jiná definice, viz 4.9 |

Dále 51 VRF bez duplikace, prefixy odvozené ze sloupce `net`, primární IP
u 289 z 365 zařízení.

**Kontrola komunikační matice** — NetBox Script s tlačítkem. Vezme CSV matici,
pro každý řádek spustí v IP Fabric simulaci cesty a vypíše verdikt. Nálezy jsou
prolinkované na zařízení, na konci je souhrn, výstupem je i CSV. Pamatuje si
poslední použitou matici a snapshot.

Podstatná vlastnost: najde i službu, která nefunguje, **aniž by byla zakázaná
v pravidlech firewallu** — třeba kvůli směrování nebo zone policy. To samotný
přehled pravidel neukáže.

**Firewallová pravidla** — objeveno 5 použitelných tabulek IP Fabric, naimportováno
1732 pravidel a z nich vyrobeny dva výstupy: hygienický přehled (177 zařízení,
204 příliš širokých povolení) a kandidátská matice. Také jako NetBox Script.

**Provoz** — RQ timeout, retence, nástěnka s metrikami a prokliky na oba skripty,
provozní dokumentace o 10 kapitolách.

**Pro vedení** — prezentace a sada screenshotů.

### Co se naopak ukázalo jako nemožné — a musí se říkat nahlas

- **NetBox Community nemá mapu topologie.** Všechny mapy jsou z IP Fabric.
- **NetBox nemá model pro firewallová pravidla.** Importujeme je a odvozujeme
  z nich výstupy, ale nativní objekt pro ně neexistuje.
- **1474 z 1732 pravidel nelze simulací ověřit**, protože neomezují zdroj.
  Ověřitelných je 258. Tohle číslo se musí uvádět, jinak si někdo myslí,
  že jsme ověřili všechno.
- **Demo nálezy nejsou ze sítě Správy železnic.** Všechna data jsou z veřejné
  demo sítě IP Fabric. Při každé prezentaci to musí být řečeno, jinak to
  vypadá jako audit naší sítě.
- **IP Fabric nepopisuje, jak to má být.** Přínos NetBoxu je právě v tom
  druhém — drží záměr, proti kterému lze realitu porovnat.

---

## 6. Zdrojové kódy

### 6.1 Předpočítaný `nb_serial` — `push_ipf_data.py`

Obchází chybu filtru `serial()` z 4.1. Náhrada musí být deterministická,
jinak by každý import zakládal nová zařízení místo aktualizace stávajících.

```python
for r in radky:
    sn = (r.get("sn") or "").strip()
    r["nb_serial"] = sn if 0 < len(sn) < 50 else (
        "ipf-" + _hashlib.sha1(
            (sn or repr(sorted(r.items()))).encode()).hexdigest()[:12])
```

### 6.2 Předpočítaný `nb_name` — `push_ipf_data.py`

Řeší 4.2. Disambiguuje vlastním krátkým otiskem, ne celým `sn`.

```python
if ep == "/inventory/devices":
    vyskyt = _collections.Counter(
        ((r.get("siteName") or ""), (r.get("hostname") or ""))
        for r in radky)
    for r in radky:
        host = (r.get("hostname") or "").strip()
        klic = ((r.get("siteName") or ""), (r.get("hostname") or ""))
        if vyskyt[klic] > 1 or len(host) > 64:
            otisk = _hashlib.sha1(
                (r.get("sn") or host).encode()).hexdigest()[:8]
            r["nb_name"] = f"{host[:53]} ({otisk})"
        else:
            r["nb_name"] = host
```

### 6.3 Transformační mapy

**Neexistují v žádném souboru — jsou jen v databázi NetBoxu.** Při obnově
z nuly se musí zadat znovu, jinak import spadne.

```jinja
Device.serial
    {{ object.nb_serial }}

Device.name
    {{ object.nb_name }}

Interface, relace na device
    {{ dcim.Device.objects.get(serial=object.nb_serial).pk }}

IPAddress.assigned_object_id
    {% set NAME = object.nameOriginal or object.intName %}
    {% set SN = object.nb_serial or object.sn %}
    {{ dcim.Interface.objects.filter(device__serial=SN, name=NAME).first().pk }}

MACAddress.assigned_object_id
    {% set NAME = object.nameOriginal or object.intName %}
    {{ dcim.Interface.objects.filter(device__serial=object.nb_serial, name=NAME).first().pk }}

DeviceType.model
    {% if object.model %}{{ object.model | string }}{% else %}{{ [object.vendor, object.family, object.platform] | select | join(' ') }}{% endif %}

DeviceType.slug
    totéž spojené přes '-' a protažené filtrem slugify

InventoryItem.name
    name -> dscr -> (pid ~ ' ' ~ sn) -> 'neznama polozka'
```

V mapě `IPAddress` je `object.nb_serial or object.sn` záměrně — viz 4.4.

### 6.4 Předvyplněná pole ve skriptech

Aby se matice a snapshot nemusely zadávat při každém spuštění.

```python
_STAV = "/opt/netbox/netbox/media/matice_posledni.json"
_ZALOHA_CESTA = "/opt/netbox/netbox/scripts/matice-demo2.csv"
_ZALOHA_SNAPSHOT = "22443e66-2430-4a55-b953-d7601b3f5148"

_VYCHOZI_CESTA = _nacti_posledni("cesta", _ZALOHA_CESTA)
_VYCHOZI_SNAPSHOT = _nacti_posledni("snapshot", _ZALOHA_SNAPSHOT)
```

### 6.5 Export konfigurace, která žije jen v databázi

Bez tohoto exportu není obnova ze zálohy úplná.

```python
import json
import pathlib

from django.apps import apps
from django.core import serializers

CIL = pathlib.Path("/opt/netbox/netbox/media/export-konfigurace")
CIL.mkdir(parents=True, exist_ok=True)

VYNECHAT = {
    "ipfabricsource",
    "ipfabricdata",
    "ipfabricsnapshot",
    "ipfabricsync",
    "ipfabricingestion",
    "ipfabricrelationshipfield",
}

CITLIVE = ("PASSWORD", "SECRET", "TOKEN", "KEY", "CREDENTIAL")


def zapis(nazev, data):
    cesta = CIL / nazev
    cesta.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    print(f"  {cesta.name}")


print("transformacni mapy pluginu:")
try:
    konfigurace = apps.get_app_config("ipfabric_netbox")
except LookupError:
    print("  plugin ipfabric_netbox neni nainstalovan, preskakuji")
else:
    for model in konfigurace.get_models():
        nazev = model._meta.model_name
        if nazev in VYNECHAT:
            continue
        objekty = list(model.objects.all())
        if not objekty:
            continue
        text = serializers.serialize("json", objekty, indent=2)
        (CIL / f"plugin-{nazev}.json").write_text(text)
        print(f"  plugin-{nazev}.json ({len(objekty)})")

print("registrovane skripty:")
from extras.models import Script, ScriptModule

zapis(
    "skripty.json",
    [
        {
            "file_root": m.file_root,
            "file_path": m.file_path,
            "skripty": sorted(
                Script.objects.filter(module=m).values_list("name", flat=True)),
        }
        for m in ScriptModule.objects.all()
    ],
)

print("nastenky:")
from extras.models import Dashboard

zapis(
    "nastenky.json",
    [
        {"uzivatel": d.user.username, "layout": d.layout, "config": d.config}
        for d in Dashboard.objects.select_related("user")
    ],
)

print("konfiguracni revize:")
from core.models import ConfigRevision

revize = ConfigRevision.objects.order_by("-created").first()
if revize is None:
    print("  zadna revize neexistuje, plati vychozi hodnoty")
else:
    data = {
        k: v
        for k, v in revize.data.items()
        if not any(slovo in k.upper() for slovo in CITLIVE)
    }
    vynechano = sorted(set(revize.data) - set(data))
    zapis(
        "konfiguracni-revize.json",
        {
            "created": revize.created,
            "comment": revize.comment,
            "data": data,
            "vynechane_citlive_klice": vynechano,
        },
    )
    if vynechano:
        print(f"  vynechano jako citlive: {', '.join(vynechano)}")

print()
print(f"hotovo, vystup v {CIL}")
```

### 6.6 Soubory, které je třeba doplnit z pracovního PC

Tyto zdrojáky leží na `blue-ThinkCentre-M710s` a do tohoto dokumentu se
nedostaly. Doplní je příkaz v příloze A.

| soubor | role |
|---|---|
| `push_ipf_data.py` | stažení 11 tabulek z IP Fabric, zjištění sloupců trikem s HTTP 422, normalizace, uložení do `IPFabricData` |
| `primarni_ip.py` | doplnění `primary_ip4` podle `loginIp`, plus pravidlo jedné IPv4 |
| `prefixy.py` | prefixy ze sloupce `net`, kanonizace přes `ip_network(strict=False)` |
| `commatrix_script.py` | kontrola matice, verze 1 |
| `commatrix_v2.py` | kontrola matice, verze 2 — verdikt první, prolinkované nálezy, souhrn, CSV |
| `fw_discover.py` | sondování 17 kandidátských tabulek bezpečnosti, `nacti_env()` |
| `fw_na_matici.py` | pravidla na kandidátskou matici |
| `fw_prehled.py` | hygienická statistika pravidel |
| `fw_prehled_script.py` | tentýž přehled jako NetBox Script |

---

## 7. Konfigurace

### 7.1 `/opt/netbox-docker/configuration/extra.py`

```python
RQ_DEFAULT_TIMEOUT = 7200
```

Proměnná v `env/netbox.env` se neuplatní, vyzkoušeno. Soubor je bind-mountovaný,
takže stačí restart kontejneru, ne přestavba obrazu.

### 7.2 Konfigurační revize

```
ENFORCE_GLOBAL_UNIQUE = False
CHANGELOG_RETENTION   = 0
JOB_RETENTION         = 0
```

Mění se zakládáním nové revize. Vždy se vychází z poslední, aby se ostatní
nastavení tiše nevrátila na výchozí hodnoty:

```python
from core.models import ConfigRevision
from netbox.config import get_config, clear_config

posledni = ConfigRevision.objects.order_by('-created').first()
data = dict(posledni.data) if posledni else {}
data['CHANGELOG_RETENTION'] = 0
data['JOB_RETENTION'] = 0

rev = ConfigRevision.objects.create(
    comment='Historie zmen i behu se neuchovava casove omezene - nemazat',
    data=data)
rev.activate()
clear_config()
```

### 7.3 Přístupové údaje

`/opt/commatrix/ipf.env`, chmod 600. Do gitu nesmí, stejně jako
`/opt/netbox-docker/env/`. Heslo obsahuje `$` a `*`, takže se soubor nikdy
nenačítá shellem — skripty si ho parsují v Pythonu.

---

## 8. Kontrolní dotazy

Stav importu:

```python
from dcim.models import Device, Interface, Site
from ipam.models import IPAddress, Prefix, VRF
print('zarizeni  :', Device.objects.count())
print('rozhrani  :', Interface.objects.count())
print('lokality  :', Site.objects.count())
print('IP adresy :', IPAddress.objects.count())
print('prefixy   :', Prefix.objects.count())
print('VRF       :', VRF.objects.count())
print('s primarni IP:', Device.objects.exclude(primary_ip4=None).count())
```

Velikost databáze — hlídat, protože retence je na nule:

```python
from core.models import ObjectChange, Job
from django.db import connection
with connection.cursor() as c:
    c.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
    velikost = c.fetchone()[0]
print(f'zmeny: {ObjectChange.objects.count()} | behy: {Job.objects.count()} | databaze: {velikost}')
```

---

## 9. Co zůstává nedodělané

- `matice-demo2.csv` má dva slabé zdroje, které umírají na hopu 1 —
  `10.52.103.101` na `10.52.98.1` a řádek NTP z L77 na `10.48.139.136`.
  Dokud se nezamění, to CSV generuje falešné nálezy, tedy přesně past 4.8.
- `fw_prehled_script.py` nebyl nikdy spuštěn z nástěnky od začátku do konce.
  Zaregistrovaný je, proklik funguje, celý běh ověřený není.
- Nálezy matice se neukládají jako Journal Entries, takže je nelze vypsat
  widgetem na nástěnce.
- Neimportují se tabulky sousedů a linků, bez nichž nelze kreslit topologii.
- Nenamapovaný endpoint `managed-networks`, neimportovaných 104 hostů
  a 120 hraničních rozhraní.

---

## Příloha A — doplnění zdrojáků z pracovního PC

Spustit na `blue-ThinkCentre-M710s` ve složce, kde je tento dokument:

```
cd /opt/commatrix
{
printf '\n---\n\n## Příloha B — zdrojové kódy\n'
for f in push_ipf_data.py primarni_ip.py prefixy.py commatrix_script.py \
         commatrix_v2.py fw_discover.py fw_na_matici.py fw_prehled.py \
         fw_prehled_script.py export_konfigurace.py
do
  test -f "$f" || continue
  printf '\n### %s\n\n```python\n' "$f"
  cat "$f"
  printf '```\n'
done
} >> NETBOX-IPFABRIC-SOUHRN.md
```

Potom zkontrolovat, že se do dokumentu nedostalo heslo:

```
grep -niE 'password|apitoken|secret|IPF_PASS' NETBOX-IPFABRIC-SOUHRN.md
```

Vypsat se smí jen řádky, kde se hodnota čte z prostředí nebo z `ipf.env`.
Pokud se objeví heslo samo, dokument do gitu nedávej.
