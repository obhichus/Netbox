# 10. Známé pasti a jak je poznat

Tahle kapitola je zápis chyb, které nás při stavbě importu zdržely, včetně jejich diagnostického
podpisu. Většina z nich se projeví hláškou, ze které není vůbec vidět, kde je skutečná příčina.
Proto je tu u každé napsáno, čím se pozná.

Navazuje na [9. Poimportní rutina](IMPORT-RUTINA.md) (celý postup importu z IP Fabricu).

| | Projev (hláška) | Kde hledat |
|---|---|---|
| [10.1](#101-null-value-in-column-serial) | `null value in column "serial"` | filtr `serial()` v pluginu, mapa `Device.serial` |
| [10.2](#102-nb_serial--proč-existuje) | (vysvětlení `nb_serial`) | `push_ipf_data.py` |
| [10.3](#103-devicename-delší-než-64-znaků) | ingestion spadne na Azure VNet | `nb_name` v `push_ipf_data.py` |
| [10.4](#104-vrf-se-při-každém-importu-zduplikují) | 151 VRF místo 51 | prázdný řetězec vs. NULL |
| [10.5](#105-po-opravě-serialu-spadnou-všechny-ip-adresy-na-nulu) | `IPAddressPrimaryRemovalError` u každé adresy | mapy IPAddress a MACAddress |
| [10.6](#106-sync-zůstane-viset-ve-stavu-ready_to_merge) | sync visí v „Ready to merge“ | `branch.merge()` místo `enqueue_merge_job` |
| [10.7](#107-job-spadne-na-timeout) | `timeout` | `RQ_DEFAULT_TIMEOUT` v `extra.py` |
| [10.8](#108-prefixy--70-chyb-u-ipv6) | 70 chyb u IPv6 prefixů | `ip_network(..., strict=False)` |
| [10.9](#109-kontrola-matice-hlásí-14-porušení-která-nejsou) | falešná porušení matice | zdrojová IP řádku matice |
| [10.10](#1010-počet-aktivních-rozhraní-se-nerovná) | 2608 vs. 2738 aktivních rozhraní | není to chyba |
| [10.11](#1011-pasti-kolem-netbox-scriptu) | chyby NetBox Scriptů | upload, jména metod, worker |
| [10.12](#1012-konfiguraci-nelze-editovat-na-stránce-configuration) | Configuration nejde editovat | nová `ConfigRevision` |
| [10.13](#1013-přihlášení-k-ip-fabric-selhalo) | „Prihlaseni k IP Fabric selhalo“ | `ipf.env` načtený shellem |
| [10.14](#1014-co-netbox-neumí--aby-to-nikdo-nesliboval) | (co NetBox neumí) | očekávání vedení a kolegů |


## 10.1 null value in column "serial"

**Projev:** ingestion spadne hned na prvním zařízení s chybou

```
null value in column "serial" violates not-null constraint
```

**Příčina:** plugin má vlastní Jinja filtr `serial()`. Když je sériové číslo delší než 50 znaků,
filtr vrátí `data.get("id")`. Jenže funkce `strip_source_data()` pluginu žádné pole `"id"` do dat
nedodává, takže filtr vrátí `None`.

Je to chyba v pluginu, ne v našich datech. Nejde ji obejít lepším nastavením – musí se přepsat mapa
pro `Device.serial` tak, aby filtr `serial()` vůbec nepoužívala.

**Co to NENÍ:** nejsou to stará data v cache a není to hostname delší než 64 znaků. Obě tyhle
hypotézy jsme zkoušeli a obě byly mimo.


## 10.2 nb_serial – proč existuje

Řešením 10.1 je nepočítat serial v Jinja mapě, ale předpočítat ho v `push_ipf_data.py` a do mapy
dát jen `{{ object.nb_serial }}`.

**Pravidlo:** použij `sn`, pokud je neprázdné a kratší než 50 znaků. Jinak vyrob stabilní náhradu
z hashe.

```python
for r in radky:
    sn = (r.get("sn") or "").strip()
    r["nb_serial"] = sn if 0 < len(sn) < 50 else (
        "ipf-" + _hashlib.sha1(
            (sn or repr(sorted(r.items()))).encode()).hexdigest()[:12])
```

Náhrada musí být deterministická. Kdyby se při každém běhu počítala jinak, každý import by založil
nová zařízení místo aktualizace stávajících.


## 10.3 Device.name delší než 64 znaků

**Projev:** ingestion spadne na Azure VNet zařízení, jméno má 151 znaků.

**Příčina:** když plugin najde dvě zařízení se stejným hostname, složí jméno jako
`"hostname - (sn)"`. U Azure VNetu je už samotné `sn` dlouhé, takže výsledek překročí
`max_length` 64 pole `Device.name`.

**Řešení** je stejné jako u serialu – předpočítat `nb_name` a disambiguovat vlastním krátkým
otiskem, ne celým `sn`:

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


## 10.4 VRF se při každém importu zduplikují

**Projev:** po druhém importu je v NetBoxu 151 VRF místo 51.

**Příčina:** naše funkce `normalizuj()` převáděla všechny sloupce ze seznamu `TEXTOVE_SLOUPCE` na
string, takže prázdné `rd` se stalo prázdným řetězcem `""`. NetBox ale ukládá prázdné `rd` jako
NULL. Coalesce strategie pluginu pak hledá VRF s `rd = ""`, nenajde nic a založí novou.

**Řešení:** odstranit `"rd"` ze `TEXTOVE_SLOUPCE` a nechat prázdnou hodnotu projít jako `None`.

**Obecné pravidlo:** prázdný řetězec a NULL nejsou v NetBoxu to samé a coalesce na tom rozdílu
založí nebo nezaloží duplikát. Kdykoli se po importu něco množí, začni hledat tady.


## 10.5 Po opravě serialu spadnou všechny IP adresy na nulu

**Projev:** import IP adres skončí s nulou založených a chybou `IPAddressPrimaryRemovalError`
u každé adresy.

**Příčina** je zřetězená a není zřejmá:

1. v mapě pro IPAddress jsme nahradili `object.sn` za `object.nb_serial`
2. plugin si seznam požadovaných sloupců skládá z toho, na co se mapy odkazují
   (`get_required_source_columns`)
3. `sn` se tím přestalo stahovat
4. plugin má ale na řádku 2599 v `ipfutils.py` hardcodované
   `.exclude(serial=serial(ip_address.data))` – a to `sn` potřebuje
5. filtr dostal prázdná data, vyhodil `TypeError` a ten se projevil až jako
   `IPAddressPrimaryRemovalError`

**Řešení:** v mapě se odkázat na obě hodnoty, aby `sn` ze seznamu požadovaných sloupců nevypadlo:

```jinja
{% set SN = object.nb_serial or object.sn %}
```

Stejná past platí pro mapu MACAddress. Při přechodu na `nb_serial` jsme na ni zapomněli
a ingestion 18 shodil 4618 MAC adres.

**Poučení:** když měníš mapu, projdi VŠECHNY mapy, které se na stejný sloupec odkazují. Seznam
stahovaných sloupců je důsledek všech map dohromady, ne té jedné, kterou právě edituješ.


## 10.6 Sync zůstane viset ve stavu ready_to_merge

**Projev:** ingestion doběhne, ale sync zůstane ve „Ready to merge“ a další sync už nejde spustit.

**Příčina:** větev jsem zmergoval přímo přes `branch.merge()`. Tím se obejde stavový automat
pluginu – větev je zmergovaná, ale plugin o tom neví a svůj záznam nikdy nepřepne.

**Správná cesta:**

```python
ingestion.enqueue_merge_job(user=..., remove_branch=True)
```

nebo zapnout `auto_merge` na zdroji, aby to plugin dělal sám.

**Pravidlo:** objekty pluginu neovládej přes modely branchingu. Plugin má na každý přechod svou
metodu, a jen ta změní i jeho vlastní stav.


## 10.7 Job spadne na timeout

**Projev:** ingestion 7914 záznamů spadne s chybou „timeout“.

**Příčina:** výchozí `RQ_DEFAULT_TIMEOUT` je 300 sekund.

**Řešení:** `RQ_DEFAULT_TIMEOUT = 7200` v `/opt/netbox-docker/configuration/extra.py`

Proměnná v `env/netbox.env` NEFUNGUJE, vyzkoušeno. Soubor `extra.py` je bind-mountovaný, takže stačí
restart kontejneru.


## 10.8 Prefixy – 70 chyb u IPv6

**Projev:** `prefixy.py` založí IPv4 prefixy a u IPv6 vyhodí 70 chyb.

**Příčina:** sloupec `net` obsahuje i zápisy host s maskou, například `beef:37:1::5/64`. To není
platný prefix.

**Řešení:** `ipaddress.ip_network(hodnota, strict=False)`

Pozor na starou verzi skriptu ve scrollbacku terminálu – omylem jsme ji jednou nakopírovali znovu
a chyba se vrátila. Před spuštěním ověř:

```sh
grep -n 'ipaddress' /opt/commatrix/prefixy.py
```


## 10.9 Kontrola matice hlásí 14 porušení, která nejsou

Tohle je nejnebezpečnější past z celého seznamu, protože výsledek vypadá věrohodně. Falešné nálezy
by šly ukázat kolegům jako skutečné a nikdo by si toho nevšiml.

**Projev:** 14 řádků matice hlásí, že komunikace nefunguje, i když pravidla existují.

**Příčina:** jako zdroj jsem použil management IP adresu pražského firewallu. Provoz, který
z firewallu sám vychází, umře na jeho vlastní zone policy už na prvním hopu.

**Řešení:** jako zdroj ber IP adresu switche, ne firewallu.

**Diagnostický podpis:** ve výstupu simulace je „hopu 1“ nebo „hopu 2“ spolu s `FORWARDING(1)`.
Když to vidíš, nehledej chybu v pravidlech – hledej ji ve zdrojové adrese řádku matice.


## 10.10 Počet aktivních rozhraní se nerovná

IP Fabric 2608, NetBox 2738. Není to chyba.

IP Fabric počítá rozhraní s nahozenou vrstvou l1 A ZÁROVEŇ l2. Ověřeno dotazem, vyjde přesně 2608.
NetBoxové `enabled` znamená administrativně povolené, což je jiná věc.

Při srovnávání s dashboardem IP Fabric tedy srovnávej jen zařízení (365), rozhraní celkem (4618)
a lokality (21). Ty se rovnají přesně. Aktivní rozhraní nesrovnávej vůbec.


## 10.11 Pasti kolem NetBox Scriptu

**`Error loading script: invalid syntax (matice-demo.csv, line 2)`**
CSV byl nahrán na formuláři Add Script. Matice se nahrává až na spouštěcím formuláři toho skriptu,
ne při jeho založení.

**`_log() got an unexpected keyword argument 'level'`**
Pomocnou funkci jsem pojmenoval `_log`, čímž jsem překryl `Script._log`, které už v NetBoxu
existuje. Přejmenováno na `zaloguj`. Vlastním metodám ve Script dávej jména, která nekolidují –
v bázové třídě jich je víc, než je vidět.

**Tlačítko Browse nereaguje**
Problém prohlížeče na desktopu, ne NetBoxu. Proto mají oba skripty i textové pole s cestou jako
alternativu k uploadu.

**Skript není vidět / nejde spustit**
Soubor musí existovat v kontejneru `netbox` I `netbox-worker` a patřit uživateli netbox (uid 999).
Skripty běží ve workeru.

**Předvyplněné hodnoty**
Oba skripty si pamatují poslední použitou matici a snapshot
v `/opt/netbox/netbox/media/matice_posledni.json`, aby se nemusely pokaždé zadávat znovu.


## 10.12 Konfiguraci nelze editovat na stránce Configuration

**Projev:** Admin – Configuration zobrazuje hodnoty, ale nejde je změnit.

**Příčina:** ta stránka je jen zobrazení aktuální `ConfigRevision`. NetBox revize needituje,
zakládá novou.

**Postup**, který zachová i dřív nastavené `ENFORCE_GLOBAL_UNIQUE`:

```python
from core.models import ConfigRevision
from netbox.config import get_config, clear_config
posledni = ConfigRevision.objects.order_by('-created').first()
data = dict(posledni.data) if posledni else {}
data['CHANGELOG_RETENTION'] = 0
data['JOB_RETENTION'] = 0
rev = ConfigRevision.objects.create(comment='...', data=data)
rev.activate()
clear_config()
```

Vždy vycházej z poslední revize a měň jen ty klíče, které měnit chceš. Když založíš revizi
z prázdného slovníku, tiše se vrátí výchozí hodnoty všech ostatních nastavení.


## 10.13 Přihlášení k IP Fabric selhalo

**Projev:** skript nahlásí „Prihlaseni k IP Fabric selhalo“, přitom údaje v `ipf.env` jsou správné.

**Příčina:** heslo obsahuje znaky `$` a `*`. Při načtení přes `set -a ; . /opt/commatrix/ipf.env`
je shell expanduje a do API odejde jiné heslo.

**Řešení:** `ipf.env` nikdy nenačítat shellem. Skripty si ho parsují samy ve Pythonu (funkce
`nacti_env`).


## 10.14 Co NetBox neumí – aby to nikdo nesliboval

Tyhle věci jsme našli až při práci a je důležité je nezamlčet, protože na nich stojí očekávání
vedení i kolegů.

**NetBox Community nemá mapu topologie.**
Mapy sítě pocházejí z IP Fabric. V prezentacích a screenshotech musí být jasné, odkud který obrázek
je.

**NetBox nemá model pro firewallová pravidla.**
Pravidla do něj neukládáme. Importujeme je, odvozujeme z nich kandidátskou matici a hygienický
přehled, ale samotná pravidla v NetBoxu žádný nativní objekt nemají.

**1474 z 1732 pravidel nelze simulací ověřit.**
Neomezují zdroj, takže simulace cesty pro ně nemá co počítat. Ověřit lze 258 pravidel. Tohle číslo
je nutné říkat nahlas – jinak si někdo myslí, že jsme ověřili všechno.

**Demo nálezy nejsou ze sítě Správy železnic.**
Všechna data v demu jsou z veřejné demo sítě IP Fabric (guided-demo.eu.ipfabric.io). Při každé
prezentaci to musí být řečeno, jinak to vypadá jako audit naší sítě.

**IP Fabric neví, jak to má být.**
IP Fabric popisuje stav, jaký je. Komunikační matice popisuje stav, jaký má být. Přínos NetBoxu je
právě v tom druhém – drží záměr, proti kterému lze realitu z IP Fabric porovnat.
