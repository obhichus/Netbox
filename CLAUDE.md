# CLAUDE.md

Pokyny pro Clauda (a každého dalšího), kdo v tomhle repu pracuje. Majitel Roman píše česky,
odpovídej česky. Projekt: NetBox 4.6.10 + plugin ipfabric_netbox + skripty komunikační matice,
offline nasazení na RHEL9 (podman). Úvod v [README.md](README.md), kontext v [docs/PROJEKT.md](docs/PROJEKT.md).

## Pravidla práce s repem

- `main` je chráněný, změny jdou přes PR. Po sloučení se větve mažou, drží se jen `main`.
- Každý vyřešený problém zapiš do [CHANGES.md](CHANGES.md) (Příznak / Příčina / Řešení / Stav) a podle
  potřeby do README. Hesla, tokeny a adresy strojů do repa nepatří.

## Znalosti, které musíš znát dřív, než sáhneš na import

Podrobně: [docs/IMPORT-RUTINA.md](docs/IMPORT-RUTINA.md) (kap. 9, postup importu) a
[docs/ZNAME-PASTI.md](docs/ZNAME-PASTI.md) (kap. 10, chyby a jejich diagnostický podpis).

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
- **NetBox Scripty:** soubor musí být v `netbox` i `netbox-worker` a patřit uid 999; vlastní metody
  nepojmenovávej tak, aby překryly metody `Script` (např. `_log`).
- **Kontrola matice:** jako zdroj ber IP switche, ne firewallu. „hopu 1/2“ + `FORWARDING(1)` ve
  výstupu simulace znamená chybnou zdrojovou adresu, ne chybu v pravidlech.
- **Srovnání s IP Fabricem:** srovnávej zařízení (365), rozhraní (4618), lokality (21). Aktivní rozhraní
  (2608 vs. 2738) nesrovnávej, měří jinou věc.

## Co nikomu neslibovat (kap. 10.14)

NetBox Community nemá mapu topologie (obrázky jsou z IP Fabricu) ani model firewallových pravidel.
Simulací lze ověřit jen 258 z 1732 pravidel. Demo data jsou z veřejného dema IP Fabricu
(guided-demo.eu.ipfabric.io), ne ze sítě Správy železnic, a musí to zaznít při každé prezentaci.
