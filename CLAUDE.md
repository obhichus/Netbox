# CLAUDE.md

Pokyny pro Clauda (a každého dalšího), kdo v tomhle repu pracuje. Majitel Roman píše česky,
odpovídej česky. Projekt: NetBox 4.6.10 + plugin ipfabric_netbox + skripty komunikační matice,
offline nasazení na RHEL9 (podman). Úvod v [README.md](README.md), kontext v [docs/PROJEKT.md](docs/PROJEKT.md).

## Pravidla práce s repem

- `main` je chráněný, změny jdou přes PR. Po sloučení se větve mažou, drží se jen `main`.
- Každý vyřešený problém zapiš do [CHANGES.md](CHANGES.md) (Příznak / Příčina / Řešení / Stav) a podle
  potřeby do README. Hesla, tokeny a adresy strojů do repa nepatří.

## Znalosti, které musíš znát dřív, než sáhneš na import

Celkový přehled projektu (proč, prostředí, co běží, čeho se dosáhlo, konfigurace):
[docs/NETBOX-IPFABRIC-SOUHRN.md](docs/NETBOX-IPFABRIC-SOUHRN.md).
Podrobně: [docs/IMPORT-RUTINA.md](docs/IMPORT-RUTINA.md) (kap. 9, postup importu) a
[docs/ZNAME-PASTI.md](docs/ZNAME-PASTI.md) (kap. 10, chyby a jejich diagnostický podpis).

- **Původní stroj** `blue-ThinkCentre-M710s` (Ubuntu 24.04, `/opt/netbox-docker`, `/opt/commatrix`) běží
  i MISP majitele stroje. Z jeho dat se nic nemaže.
- **IP Fabric:** demo `guided-demo.eu.ipfabric.io` je 7.9.4, ve firmě (SŽ) 7.5.
- **Pořadí importu je závazné:** `push_ipf_data.py` → ingestion (job ve `netbox-worker`) →
  `primarni_ip.py` → `prefixy.py`.
- **Transformační mapy jsou jen v databázi** (`IPFabricTransformMap`), doslovně jsou v kap. 9.6.
  Při obnově od nuly je nutné je zadat znovu.
- **`nb_serial` a `nb_name`** nejsou sloupce IP Fabric, dopočítává je `push_ipf_data.py`
  (obchází chybu filtru `serial()` v pluginu a limit 64 znaků `Device.name`). Náhrady musí být
  deterministické, jinak každý import založí nová zařízení.
- **Když měníš jednu mapu, projdi všechny**, které se odkazují na stejný sloupec. Seznam stahovaných
  sloupců plugin skládá ze všech map; v mapách IPAddress/MACAddress drž `object.nb_serial or object.sn`.
- **Prázdný řetězec ≠ NULL.** Když se po importu něco množí (VRF), hledej `""` místo `None`.
- **Větev pluginu nemerguj přes `branch.merge()`**, jen `enqueue_merge_job(...)` nebo `auto_merge`.
- **`RQ_DEFAULT_TIMEOUT = 7200` patří do `configuration/extra.py`**, proměnná v `env/netbox.env` nefunguje.
- **`ipf.env` nikdy nenačítej shellem** (`$` a `*` v hesle), skripty ho parsují samy (`nacti_env`).
- **Prefixy:** `ipaddress.ip_network(hodnota, strict=False)`.
- **Konfigurace NetBoxu** se mění novou `ConfigRevision` odvozenou z poslední, nikdy z prázdného slovníku.
  Aktuálně `ENFORCE_GLOBAL_UNIQUE = False`, `CHANGELOG_RETENTION = 0`, `JOB_RETENTION = 0` (nic se nemaže,
  databáze jen roste, asi 2000 změn na import).
- **NetBox Scripty:** soubor musí být v `netbox` i `netbox-worker` a patřit uid 999; vlastní metody
  nepojmenovávej tak, aby překryly metody `Script` (např. `_log`).
- **Kontrola matice:** jako zdroj ber IP switche, ne firewallu. „hopu 1/2“ + `FORWARDING(1)` ve
  výstupu simulace znamená chybnou zdrojovou adresu, ne chybu v pravidlech.
- **Důkaz, že import sedí:** [commatrix/doklady/ipfabric-dashboard-22443e66.pdf](commatrix/doklady/ipfabric-dashboard-22443e66.pdf)
  (dashboard IP Fabricu ke snímku 22443e66: 365 zařízení, 2608/4618 rozhraní, 104 hostů, 120 hraničních rozhraní).
- **Srovnání s IP Fabricem:** srovnávej zařízení (365), rozhraní (4618), lokality (21). Aktivní rozhraní
  (2608 vs. 2738) nesrovnávej, měří jinou věc.

## Konfigurace, která je jen v databázi

Transformační mapy, registrace NetBox Scriptů, rozložení nástěnek a konfigurační revize nejsou v žádném
souboru, žijí jen v databázi NetBoxu. Text map v kap. 9.6 je dokumentace, ne záloha. Zálohu dělá
[commatrix/export_konfigurace.py](commatrix/export_konfigurace.py) a výsledné JSONy jsou v
[export-konfigurace/](export-konfigurace/) (export z 2026-10-24; chybí relační mapy, viz níže).
Na původním stroji zálohu do gitu (zdrojáky, konfigurace, export, kontrola úniku hesel) dělá
[commatrix/zaloha_na_git.sh](commatrix/zaloha_na_git.sh) (kap. 11, [docs/ZALOHA-NA-GIT.md](docs/ZALOHA-NA-GIT.md)). Commituje do větve `zaloha-<datum>` (main je
chráněný) a vypíše odkaz na pull request; konfiguraci z netbox-dockeru ukládá do
`reference/puvodni-netbox-docker/`, `configuration/` (konfigurace pro RHEL9) nepřepisuje.

## Nedodělané – nepovažuj za hotové

- **`commatrix/matice-demo2.csv`**: Roman psal o dvou slabých zdrojích, které umírají na hopu 1
  (`10.52.103.101` → `10.52.98.1` a řádek „NTP z L77“ → `10.48.139.136`). Verze na Ubuntu PC (2026-10-24)
  je shodná s repem a záměny už obsahuje (řádek „L52 na aplikaci v L35“ ze `10.52.98.1`, „NTP z L48“
  z `10.48.139.136`). **Neověřeno je, že po záměně proběhla kontrola znovu bez nálezů na hopu 1/2**
  (past 10.9). Dokud se to nestane, nálezy z této matice neukazovat kolegům jako skutečné.
- **`fw_prehled_script.py`** nebyl nikdy spuštěn z nástěnky od začátku do konce. Je zaregistrovaný
  a proklik funguje, ale celý běh ověřený není.
- Nálezy matice se neukládají jako Journal Entries, takže je nelze vypsat widgetem na nástěnce.
- Neimportují se tabulky sousedů a linků (bez nich nelze kreslit topologii).
- Nenamapovaný endpoint `managed-networks`: neimportovaných 104 hostů a 120 hraničních rozhraní.
- **V repu zatím chybí** (Roman nemá přístup k Ubuntu stroji blue-ThinkCentre-M710s, doplní se až ho mít
  bude, nejlépe během `commatrix/zaloha_na_git.sh`): relační mapy (`ipfabricrelationshipfield`, např.
  „Interface, relace na device“) – první export 2026-10-24 je vynechal, skript je opravený, stačí export
  zopakovat; dále `commatrix/conmantrix_discovery.py`, který na PC je a v repu ne. Zda jsou skripty
  v `commatrix/` poslední verze, není ověřeno (kontrolní součty: `sha256sum` proti `/opt/commatrix`).

## Co do repa nesmí

`ipf.env`, celé `/opt/netbox-docker/env/`, generované `fw_prehled.csv` a `fw_siroka_pravidla.csv`
(jsou v `.gitignore`). Hesla, tokeny a adresy strojů obecně.

## Co nikomu neslibovat (kap. 10.14)

NetBox Community nemá mapu topologie (obrázky jsou z IP Fabricu) ani model firewallových pravidel.
Simulací lze ověřit jen 258 z 1732 pravidel. Demo data jsou z veřejného dema IP Fabricu
(guided-demo.eu.ipfabric.io), ne ze sítě Správy železnic, a musí to zaznít při každé prezentaci.
