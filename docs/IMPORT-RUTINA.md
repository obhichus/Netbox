# 9. Poimportní rutina – celý postup importu z IP Fabric

Import dat z IP Fabric do NetBoxu není jeden krok a plugin ipfabric_netbox sám nestačí. Plugin umí
načíst data a založit objekty, ale neumí dvě věci, které potřebujeme: nedoplní primární IP adresy
zařízení a nevytvoří prefixy. To dodělávají naše dva skripty. Pořadí kroků je závazné – každý krok
pracuje s výsledkem toho předchozího.

Všechny skripty leží v `/opt/commatrix` na stroji blue-ThinkCentre-M710s (v repu
v [commatrix/](../commatrix/)). NetBox běží z `/opt/netbox-docker` (oficiální projekt netbox-docker).

Chyby, na které jsme při stavbě importu narazili, jsou v [10. Známé pasti](ZNAME-PASTI.md).


## 9.1 Přehled kroků

| | Krok | Co dělá |
|---|---|---|
| 1 | `push_ipf_data.py` | stáhne tabulky z IP Fabric API a uloží je do pluginu jako `IPFabricData` |
| 2 | ingestion | plugin z načtených dat vytvoří objekty NetBoxu (běží jako job ve workeru) |
| 3 | `primarni_ip.py` | doplní `primary_ip4` u zařízení |
| 4 | `prefixy.py` | vytvoří `Prefix` objekty ze sloupce `net` |

Krok 1 a 2 jsou oddělené záměrně. Mezi nimi si lze zkontrolovat, co se vlastně natáhlo, aniž by se
už zapisovalo do inventáře.


## 9.2 Krok 1 – stažení dat z IP Fabric

Přístupové údaje jsou v `/opt/commatrix/ipf.env` (`chmod 600`). Soubor NIKDY nenačítej přes
`set -a ; . ipf.env` – heslo obsahuje znaky `$` a `*`, které shell expanduje a přihlášení pak selže
s hláškou „Prihlaseni k IP Fabric selhalo“. Skripty si proto soubor parsují samy ve Pythonu
(funkce `nacti_env`).

Spuštění:

```sh
cd /opt/netbox-docker
docker compose exec -T netbox \
  /opt/netbox/netbox/manage.py shell < /opt/commatrix/push_ipf_data.py
```

Skript projde slovník `MAPOVANI` (11 endpointů pluginu proti tabulkám IP Fabric), u každé tabulky
si zjistí dostupné sloupce, stáhne je po stránkách a uloží do `IPFabricData`.

Zjišťování sloupců stojí za vysvětlení: IP Fabric nemá endpoint, který by seznam sloupců vrátil.
Skript proto pošle záměrně neplatný dotaz, dostane HTTP 422 a z chybové hlášky
(`"Expected (.+?), received"`) si seznam sloupců přečte. Je to dokumentovaný trik, ne náhoda – kdyby
se chování API změnilo, selže funkce `sloupce()` a import se zastaví hned, ne až v polovině.

Offline režim:

```sh
IPF_DUMP_DIR=/opt/commatrix/dump    # uloží odpovědi API na disk
IPF_LOAD_DIR=/opt/commatrix/dump    # čte z disku místo z API
```

Offline režim je jediný způsob, jak import zkoušet bez připojení do demo instance – a zároveň jediný
způsob, jak ho později provozovat ve firmě, dokud nebude z management zóny povolen přístup na API
IP Fabric.

Výchozí zdroj je guided-demo.eu.ipfabric.io, přepíná se proměnnou `IPF_SOURCE_NAME`.


## 9.3 Krok 2 – ingestion

Ve webovém rozhraní: Plugins – IP Fabric – Sources – zdroj – Sync.
Z příkazové řádky přes `enqueue_sync_job(adhoc=True, user=...)`.

Ingestion běží v kontejneru `netbox-worker`, ne v `netbox`. Když přidáváš soubor skriptu, musí
existovat v obou kontejnerech a patřit uživateli netbox (uid 999), jinak ho worker neuvidí.

Plugin si vytvoří větev (branch) a po dokončení ji zmerguje. Merge se spouští přes
`enqueue_merge_job(user=..., remove_branch=True)`, nebo se zapne `auto_merge` na zdroji. Větev
NIKDY nemerguj přes `branch.merge()` – viz [kapitola 10.6](ZNAME-PASTI.md#106-sync-zůstane-viset-ve-stavu-ready_to_merge).

Doběh kontroluj v Operations – Jobs (česká lokalizace to přeložila jako „Pracovní místa“, cesta
`/core/jobs/`).

Ingestion 7914 záznamů trvá podstatně víc než pět minut, což je výchozí timeout RQ. Proto je
v `/opt/netbox-docker/configuration/extra.py` nastaveno `RQ_DEFAULT_TIMEOUT = 7200`. Proměnná
v `env/netbox.env` nefunguje, musí být v `extra.py`. Soubor je bind-mountovaný, stačí restart
kontejneru, ne přestavba obrazu.


## 9.4 Krok 3 – primární IP adresy

```sh
docker compose exec -T netbox \
  /opt/netbox/netbox/manage.py shell < /opt/commatrix/primarni_ip.py
```

Skript nastavuje `primary_ip4` podle dvou pravidel:

1. podle sloupce `loginIp` z IP Fabric (management adresa)
2. pokud zařízení má přesně jednu IPv4 adresu, dostane ji

Zařízení, které management adresu nehlásí a má adres víc, zůstane bez primární IP. To je záměr.
Hádat, která z adres je správná, by znamenalo dát do zdroje pravdy údaj, který nikdo netvrdí.

Při posledním běhu vyšlo 289 z 365 zařízení.


## 9.5 Krok 4 – prefixy

```sh
docker compose exec -T netbox \
  /opt/netbox/netbox/manage.py shell < /opt/commatrix/prefixy.py
```

Prefixy se odvozují ze sloupce `net`. Ten obsahuje i zápisy typu host s maskou (například
`beef:37:1::5/64`), které nejsou platný prefix. Skript je proto prohání přes

```python
ipaddress.ip_network(hodnota, strict=False)
```

což adresu zkanonikalizuje na síťovou. Bez toho padalo 70 IPv6 záznamů. Před spuštěním si ověř, že
ve skriptu ta funkce opravdu je:

```sh
grep -n 'ipaddress' /opt/commatrix/prefixy.py
```


## 9.6 Transformační mapy

Mapy nejsou v žádném souboru – jsou v databázi NetBoxu (`IPFabricTransformMap`). Při obnově z nuly
je nutné je zadat znovu, jinak import spadne. Proto jsou tady.

**Device.serial**

```jinja
{{ object.nb_serial }}
```

**Device.name**

```jinja
{{ object.nb_name }}
```

**Interface, relace na device**

```jinja
{{ dcim.Device.objects.get(serial=object.nb_serial).pk }}
```

**IPAddress.assigned_object_id**

```jinja
{% set NAME = object.nameOriginal or object.intName %}
{% set SN = object.nb_serial or object.sn %}
{{ dcim.Interface.objects.filter(device__serial=SN, name=NAME).first().pk }}
```

**MACAddress.assigned_object_id**

```jinja
{% set NAME = object.nameOriginal or object.intName %}
{{ dcim.Interface.objects.filter(device__serial=object.nb_serial, name=NAME).first().pk }}
```

**DeviceType.model**

```jinja
{% if object.model %}{{ object.model | string }}{% else %}
{{ [object.vendor, object.family, object.platform] | select | join(' ') }}{% endif %}
```

**DeviceType.slug**
totéž, spojené přes `'-'` a protažené filtrem `slugify`

**InventoryItem.name**

```
name - dscr - (pid ~ ' ' ~ sn) - 'neznama polozka'
```

Pozn.: `nb_serial` a `nb_name` nejsou sloupce IP Fabric. Dopočítává je `push_ipf_data.py`, viz
[kapitola 10.2](ZNAME-PASTI.md#102-nb_serial--proč-existuje) a
[10.3](ZNAME-PASTI.md#103-devicename-delší-než-64-znaků).

V mapě IPAddress je záměrně `object.nb_serial or object.sn`. Když tam zůstane jen `nb_serial`,
vypadne `sn` ze seznamu požadovaných sloupců a plugin pak spadne na svém vlastním hardcodovaném
řádku v `ipfutils.py` (viz [kapitola 10.5](ZNAME-PASTI.md#105-po-opravě-serialu-spadnou-všechny-ip-adresy-na-nulu)).

> Pozor: mapa MACAddress výše se odkazuje jen na `object.nb_serial`. Podle kapitoly 10.5 stejná
> past platí i pro ni (ingestion 18 kvůli tomu shodil 4618 MAC adres), takže při zadávání map od
> nuly zvaž i tam `{% set SN = object.nb_serial or object.sn %}`.


## 9.7 Kontrola po importu

```sh
docker compose exec -T netbox /opt/netbox/netbox/manage.py shell <<'PY'
from dcim.models import Device, Interface, Site
from ipam.models import IPAddress, Prefix, VRF
print('zarizeni  :', Device.objects.count())
print('rozhrani  :', Interface.objects.count())
print('lokality  :', Site.objects.count())
print('IP adresy :', IPAddress.objects.count())
print('prefixy   :', Prefix.objects.count())
print('VRF       :', VRF.objects.count())
print('s primarni IP:', Device.objects.exclude(primary_ip4=None).count())
PY
```

Referenční hodnoty proti dashboardu IP Fabric (snapshot 22443e66, Network Audit Evidence,
2024-11-12):

| | NetBox | IP Fabric |
|---|---|---|
| zařízení | 365 | 365 |
| rozhraní | 4618 | 4618 |
| lokality | 21 | 21 |
| VRF | 51 | (pozor na duplikaci, viz [kapitola 10.4](ZNAME-PASTI.md#104-vrf-se-při-každém-importu-zduplikují)) |

Počet aktivních rozhraní se NEROVNÁ. IP Fabric uvádí 2608, NetBox 2738. Není to chyba importu:
IP Fabric počítá rozhraní, která mají nahozenou vrstvu l1 A ZÁROVEŇ l2 (ověřeno, vyjde přesně 2608),
kdežto NetBoxové `enabled` znamená administrativně povolené. Jsou to dvě jiné věci a nelze je
srovnat.


## 9.8 Velikost databáze a retence

`CHANGELOG_RETENTION` a `JOB_RETENTION` jsou nastaveny na 0, tedy neuchovávat časově omezeně – nic se
nikdy nemaže. Je to vědomé rozhodnutí kvůli důkazní hodnotě změn, ale znamená, že databázi nic
nezmenší. Jeden import přidává řádově 2000 záznamů do protokolu změn.

Výchozí bod: 39856 změn, 92 běhů, databáze 123 MB.

Kontrola:

```sh
docker compose exec -T netbox /opt/netbox/netbox/manage.py shell <<'PY'
from core.models import ObjectChange, Job
from django.db import connection
with connection.cursor() as c:
    c.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
    velikost = c.fetchone()[0]
print(f'zmeny: {ObjectChange.objects.count()} | behy: {Job.objects.count()} | databaze: {velikost}')
PY
```

Nastavení se nemění na stránce Admin – Configuration, ta je jen zobrazení aktuální revize. Změna se
dělá založením nové `ConfigRevision` – viz
[kapitola 10.12](ZNAME-PASTI.md#1012-konfiguraci-nelze-editovat-na-stránce-configuration).
