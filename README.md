# NetBox + IP Fabric: kontrola komunikační matice

NetBox 4.6.10 s pluginem IP Fabric a sadou Python skriptů, které ověřují komunikační matici
(kdo s kým smí v síti mluvit) proti skutečnému stavu sítě z IP Fabricu a hledají v ní chyby a díry.
Repo obsahuje vše potřebné k provozu na **RHEL9 bez přístupu k internetu** (podman + systemd quadlety).

**Ke stažení:** [Releases](https://github.com/obhichus/Netbox/releases) obsahuje RPM pro RHEL9
(`dnf install ./netbox-offline-*.rpm && netbox-offline-install`), archiv po částech a prezentaci
[netbox-sz-vedeni.pptx](https://github.com/obhichus/Netbox/raw/main/docs/prezentace-vedeni/netbox-sz-vedeni.pptx).
Obraz NetBoxu s pluginy je v [Packages](https://github.com/obhichus/Netbox/pkgs/container/netbox-ipfabric)
(`podman pull ghcr.io/obhichus/netbox-ipfabric:4.6.10`, po `podman login ghcr.io` s tokenem `read:packages`).

**Instalace na RHEL9 krok za krokem: [docs/INSTALACE-RHEL9.md](docs/INSTALACE-RHEL9.md)** (v balíčku jako `INSTALACE.md`).

| Kde | Co |
|---|---|
| [docs/INSTALACE-RHEL9.md](docs/INSTALACE-RHEL9.md) | kuchařka instalace: co nainstalovat, co kam zkopírovat, co spustit pod rootem |
| [docs/PROJEKT.md](docs/PROJEKT.md) | o čem projekt je, proč a co má přinést |
| [docs/NETBOX-IPFABRIC-SOUHRN.md](docs/NETBOX-IPFABRIC-SOUHRN.md) | souhrn projektu: proč, prostředí, co se řešilo, čeho se dosáhlo, co zbývá |
| [docs/IMPORT-RUTINA.md](docs/IMPORT-RUTINA.md) | postup importu z IP Fabricu krok za krokem, transformační mapy, kontrola po importu |
| [docs/ZALOHA-NA-GIT.md](docs/ZALOHA-NA-GIT.md) | záloha zdrojáků, konfigurace a exportu z původního stroje do gitu (`zaloha_na_git.sh`) |
| [docs/ZNAME-PASTI.md](docs/ZNAME-PASTI.md) | známé pasti importu a skriptů a podle čeho je poznat |
| [CLAUDE.md](CLAUDE.md) | souhrn klíčových pravidel pro Clauda a další, kdo v repu pracují |
| [docs/opensource-misto-ipfabric.md](docs/opensource-misto-ipfabric.md) | dá se IP Fabric nahradit open-source nástroji? srovnání, škálování, TCO, pilot |
| [docs/prezentace-vedeni/](docs/prezentace-vedeni/) | prezentace pro vedení SŽ (`netbox-sz-vedeni.pptx`, 18 slajdů) |
| [docs/prezentace/](docs/prezentace/) | prezentace „Komunikační matice v NetBoxu“ (otevřít `prezentace.html`) |
| [docs/provoz-netboxu-s-ipfabric.html](docs/provoz-netboxu-s-ipfabric.html) | provozní dokumentace (IP Fabric → NetBox, snímky, matice) |
| [docs/komunikacni-matice-runbook.html](docs/komunikacni-matice-runbook.html) | runbook ukázky pro kolegy, nálezy, otázky a odpovědi |
| [commatrix/](commatrix/) | skripty kontroly matice, import z IP Fabricu, matice CSV |
| [build/](build/) | stavba offline balíčku (na stroji s internetem) |
| [deploy/](deploy/) | instalace, záloha, obnova na RHEL9 |
| [migrate/](migrate/) | přenos dat ze stávajícího Ubuntu stroje (docker compose) |
| [quadlet/](quadlet/) | systemd jednotky pro podman |
| [reference/](reference/) | původní konfigurace netbox-docker, databázové kroky, rekonstrukce |

## Co poběží na RHEL9

| Kontejner | Obraz | Účel |
|---|---|---|
| `netbox` | `localhost/netbox-ipfabric:4.6.10` (NetBox 4.6.10 + ipfabric_netbox 6.1.0 + netbox_branching 1.1.3) | web na portu 8000 |
| `netbox-worker` | totéž | skripty, ingesce IP Fabricu, housekeeping |
| `netbox-postgres` | `postgres:18-alpine` | databáze |
| `netbox-redis`, `netbox-redis-cache` | `valkey/valkey:9.1-alpine` | fronta úloh a cache |
| `batfish` | `batfish/allinone` | analýza konfigurací firewallů (porty 8888, 9996, 9997) |

Verze jsou na jednom místě v [versions.env](versions.env). Odpovídají původní instalaci
(netbox-docker 5.0.2), takže na RHEL9 jde obnovit stávající databázi.

## Postup

### 1. Stáhnout hotový balíček z GitHubu

Hotový balíček je v [Releases](https://github.com/obhichus/netbox/releases): soubory
`netbox-offline-<datum>.tar.gz.part-00`, `part-01` … a `netbox-offline-<datum>.sha256`
(GitHub bere soubory do 2 GB, proto je archiv rozdělený). Stáhnout všechny na libovolný stroj
a přenést na RHEL9 (USB, interní sdílení).

Na RHEL9 složit a ověřit:

```bash
cat netbox-offline-<datum>.tar.gz.part-* > netbox-offline-<datum>.tar.gz
sha256sum -c netbox-offline-<datum>.sha256
tar xzf netbox-offline-<datum>.tar.gz && cd netbox-offline-<datum>
```

### 2. Nebo si balíček postavit sám

Na stroji s internetem a podmanem nebo dockerem (~8 GB místa):

```bash
git clone https://github.com/obhichus/netbox.git && cd netbox
./build/build-bundle.sh                 # nebo: CTR=docker ./build/build-bundle.sh
# za firemní proxy s TLS inspekcí: BUILD_CA_CERT=/cesta/ca.crt ./build/build-bundle.sh
```

Výsledek je v `dist/`. Totéž umí GitHub Actions: **Actions → Offline balicek RHEL9 → Run workflow**
postaví balíček a přiloží ho k nové release. Obrazy jsou pro `amd64`.

Verzi IP Fabricu není potřeba řešit při stavbě: obraz obsahuje SDK pro všechny verze, které plugin
podporuje, a přepíná se až na RHEL9 konfigurátorem (krok 4). Výchozí SDK v obrazu se dá změnit
`IPF_VERSION=7.5 ./build/build-bundle.sh`.

### 3. Podman na RHEL9 bez internetu

Podman je součást RHEL9 (AppStream). Pokud na serveru není, nainstaluje se z instalačního DVD/ISO:

```bash
mount -o loop rhel-9.x-x86_64-dvd.iso /mnt
cat > /etc/yum.repos.d/dvd.repo <<'EOF'
[dvd-appstream]
name=DVD AppStream
baseurl=file:///mnt/AppStream
gpgcheck=0
[dvd-baseos]
name=DVD BaseOS
baseurl=file:///mnt/BaseOS
gpgcheck=0
EOF
dnf install -y container-tools
```

Quadlety potřebují podman 4.4+, tedy **RHEL 9.2 a novější** (`podman --version`).

### 4. Instalace

```bash
sudo ./deploy/install.sh
```

Skript ověří kontrolní součty, nahraje obrazy (`podman load`), zkopíruje vše do `/opt/netbox-offline`,
vygeneruje hesla do `/opt/netbox-offline/env/` (jen při prvním běhu), nainstaluje quadlety do
`/etc/containers/systemd/`, otevře port 8000 ve firewalld, spustí služby a nahraje skripty kontroly matice.
`/opt/commatrix` je odkaz na `/opt/netbox-offline/commatrix`, takže příkazy z dokumentace platí dál.

Pak jedno z:

```bash
sudo /opt/netbox-offline/deploy/create-superuser.sh                     # čistá instalace
sudo /opt/netbox-offline/migrate/import-on-rhel.sh netbox-export-*.tar.gz  # data ze starého stroje
```

NetBox: `http://<server>:8000/`

Nakonec napojení na IP Fabric SŽ:

```bash
sudo /opt/netbox-offline/deploy/configure-ipfabric.py
```

Konfigurátor se zeptá na URL IP Fabricu, interní CA certifikát, účet (nebo API token) a **verzi IP Fabricu**.
Verzi se pokusí zjistit sám z `/api/version`, jinak nabídne 7.5 (verze SŽ). Na verzi záleží: SDK `ipfabric`
v pluginu musí mít stejné major.minor jako server, jinak plugin se serverem nekomunikuje správně.

| IP Fabric | 7.0 | 7.2 | 7.3 | 7.5 | 7.8 | 7.9 | 7.10 | 7.11 |
|---|---|---|---|---|---|---|---|---|
| SDK v obrazu | 7.0.3 | 7.2.2 | 7.3.1 | 7.5.2 | 7.8.2 | 7.9.1 | 7.10.0 | 7.11.2 |

Jiné verze plugin `ipfabric_netbox` 6.1.0 nepodporuje a konfigurátor je odmítne. Co konfigurátor udělá:

1. uloží nastavení do `env/ipfabric.conf` (bez hesel), přístupy do `env/netbox.env` a `commatrix/ipf.env`,
2. když SDK v obrazu nesedí, postaví bez internetu odvozený obraz `localhost/netbox-ipfabric:4.6.10-ipf7.5`
   z wheelů v `/opt/ipfabric-wheels` a přepne na něj quadlety `netbox` a `netbox-worker`,
3. přidá CA certifikát IP Fabricu k systémovým do `env/ca-bundle.crt` (v kontejneru `/etc/netbox-ca/ca-bundle.crt`),
4. restartuje NetBox a vytvoří nebo upraví zdroj v **IP Fabric → Sources** (režim `local`, když účet smí
   číst snímky, jinak `remote`),
5. ověří spojení z kontejneru NetBoxu přes SDK pluginu (verze serveru, počet snímků) a v režimu `local`
   rovnou načte snímky do NetBoxu. Když spojení selže, vypíše proč a skončí kódem 2.

Samotný import dat se pak spouští v NetBoxu: **IP Fabric → Syncs → Add** (zdroj, snímek, co importovat)
a **Run**. Plugin zapisuje do větve (netbox-branching), změny se po kontrole sloučí do hlavních dat.

Po upgradu balíčku `install.sh` konfigurátor spustí znovu s `--apply` a uložené nastavení použije.

### 5. Přenos dat ze stávajícího stroje (volitelné)

Na starém Ubuntu stroji s `/opt/netbox-docker`:

```bash
sudo ./migrate/export-from-docker.sh /opt/netbox-docker
```

Archiv obsahuje databázi (inventář, historii změn, běhy skriptů, transform mapy, zdroj a sync IP Fabricu),
media, skripty a matice, `/opt/commatrix` a `netbox.env`. Na RHEL9 ho nahraje `import-on-rhel.sh`, který
převezme i `SECRET_KEY` a `API_TOKEN_PEPPER_*`, aby dál platily API tokeny. Archiv obsahuje hesla.

## Provoz

| Úkol | Příkaz |
|---|---|
| stav | `systemctl status 'netbox*' batfish` nebo `podman ps` |
| logy | `journalctl -u netbox -f`, `journalctl -u netbox-worker -f` |
| restart | `systemctl restart netbox netbox-worker` |
| záloha | `/opt/netbox-offline/deploy/backup.sh` (do cronu, drží 14 posledních) |
| obnova | `/opt/netbox-offline/deploy/restore.sh /opt/netbox-offline/backups/<datum>` |
| nahrát změněné skripty/matice | upravit v `/opt/commatrix/`, pak `/opt/netbox-offline/deploy/install-commatrix.sh` |
| skript v NetBox shellu | `/opt/netbox-offline/deploy/nb-shell.sh /opt/commatrix/primarni_ip.py` |
| upgrade | nový balíček, znovu `deploy/install.sh` (hesla, konfigurace i data zůstanou) |

Ekvivalenty příkazů z původní dokumentace (`docker compose …` v `/opt/netbox-docker`):

| Původně | Na RHEL9 |
|---|---|
| `docker compose exec -T netbox manage.py shell < X.py` | `deploy/nb-shell.sh X.py` |
| `docker compose exec -T -e IPF_SNAPSHOT=… netbox … < push_ipf_data.py` | `deploy/nb-shell.sh /opt/commatrix/push_ipf_data.py IPF_SNAPSHOT=…` |
| `docker compose cp X netbox:/opt/netbox/netbox/scripts/` (do netbox i worker) | `deploy/install-commatrix.sh` (svazek je společný) |
| `docker compose restart netbox netbox-worker` | `systemctl restart netbox netbox-worker` |
| `docker compose ps` | `podman ps` |

## Import z IP Fabricu: pořadí skriptů

Pořadí je závazné, každý krok pracuje s výsledkem předchozího. Podrobně v
[docs/IMPORT-RUTINA.md](docs/IMPORT-RUTINA.md), chyby a jejich podpis v [docs/ZNAME-PASTI.md](docs/ZNAME-PASTI.md).

| | Krok | Co dělá |
|---|---|---|
| 1 | `commatrix/push_ipf_data.py` | stáhne tabulky z IP Fabric API (nebo z dumpu) do pluginu jako `IPFabricData`, dopočítá `nb_serial`/`nb_name` |
| 2 | ingestion (IP Fabric → Sources → Sync) | plugin z dat založí objekty NetBoxu ve větvi; merge přes `enqueue_merge_job` nebo `auto_merge` |
| 3 | `commatrix/primarni_ip.py` | doplní `primary_ip4` zařízení |
| 4 | `commatrix/prefixy.py` | založí prefixy ze sloupce `net` |
| 5 | kontrola po importu | počty proti dashboardu IP Fabricu (kap. 9.7) |

Pak kontrola matice (`commatrix_script.py` / `commatrix_check.py`) a přehled firewallů
(`fw_discover.py` → `fw_prehled.py`, `fw_na_matici.py`), viz [commatrix/README.md](commatrix/README.md).
Po změně map, skriptů nebo nastavení spustit `commatrix/export_konfigurace.py` a JSONy commitnout
do `export-konfigurace/`. Na původním Ubuntu stroji to celé (zdrojáky, konfigurace, export, kontrola
úniku hesel, commit) dělá `commatrix/zaloha_na_git.sh`, viz [docs/ZALOHA-NA-GIT.md](docs/ZALOHA-NA-GIT.md).

## Offline a IP Fabric

NetBox na RHEL9 nepotřebuje internet. Pro data ze sítě jsou dvě cesty:

- **IP Fabric je dostupný v interní síti**: spustit `deploy/configure-ipfabric.py` (viz krok 4), který
  nastaví verzi SDK, přístupy pro skripty i zdroj v pluginu.
- **IP Fabric dostupný není**: na stroji, který na něj vidí, uložit snímek do JSON (`IPF_DUMP_DIR`),
  přenést a nahrát přes `IPF_LOAD_DIR`. Postup je v [commatrix/README.md](commatrix/README.md).

## Řešené problémy (výběr)

Úplný seznam 87 problémů (78 z pilotu na Ubuntu, 9 z přípravy RHEL9 balíčku) s příznakem, příčinou a řešením je v [CHANGES.md](CHANGES.md). Tady jsou ty,
na které se dá narazit znovu:

| # | Příznak | Řešení |
|---|---|---|
| 11, 15, 20, 79 | build na NetBoxu 4.7 nebo s netbox_branching 1.2 padá v `collectstatic` | držet NetBox 4.6.10 a `netboxlabs-netbox-branching==1.1.3` |
| 16, 17, 18 | pomalá/nestabilní linka, build a pull padají | `UV_HTTP_TIMEOUT=300`, `UV_CONCURRENT_DOWNLOADS=1`, DNS v `daemon.json`, opakování; offline balíček tohle na RHEL9 obchází |
| 21, 83 | NetBox `unhealthy`, Redis `AuthenticationError`, nesedící hesla | hesla generuje `install.sh` na jednom místě; DB heslo už není v `plugins.py` |
| 25, 29, 36 | plugin IP Fabricu: nesoulad verze SDK, 403 na snímky u demo účtu | extra `ipfabric_7_9` (pro firmu `ipfabric_7_5`), zdroj v režimu *remote* plněný `push_ipf_data.py` |
| 28, 76 | „Failed to Authenticate“ | heslo s `$*` rozbalil bash; Python kód posílat přes `<<'PY'`, `ipf.env` čtou skripty samy (nesourcovat ho shellem) |
| 34, 84 | nahraný skript končí `PermissionError` nebo není vidět | `deploy/install-commatrix.sh` (vlastník `netbox`, `ScriptModule`, restart) |
| 37, 60, 64 | ingesce padá na `serial` NULL nebo na délce jména (151 znaků) | sloupce `nb_serial`/`nb_name` v `push_ipf_data.py` + upravené transform mapy |
| 38 | duplicitní IP v globální tabulce | `ENFORCE_GLOBAL_UNIQUE = False` (ConfigRevision) |
| 40 | VRF se při každém syncu zdvojují | prázdné RD musí jít jako `None`, `rd` není v textových sloupcích |
| 42 | sync uvázne v `ready_to_merge` | nemergovat ručně `branch.merge()`, nechat `auto_merge` |
| 47, 71 | falešné nálezy v matici, všechny na 1. hopu | zdrojová adresa nesmí být management adresa firewallu |
| 55 | tlačítko Procházet nefunguje (Firefox snap přes RDP) | pole **cesta** ve skriptu v2 |
| 59 | ingesce skončí `timeout` | `RQ_DEFAULT_TIMEOUT = 7200` v `configuration/extra.py` (samotná env proměnná nestačí) |
| 61 | VLAN `vid must be >= 1` | VLAN 0 se filtrují už v `push_ipf_data.py` |
| 62 | po přepnutí snímku zůstávají stará zařízení | úklid podle `ipfabric_ingestion`, viz provozní dokument kap. 7 |
| 68 | po ingesci nula IP adres | `sn` musí zůstat mezi povinnými sloupci adres |
| 78 | historie změn se maže po 90 dnech | `CHANGELOG_RETENTION`/`JOB_RETENTION` přes ConfigRevision (0 = nemazat) |
| 80 | RHEL bez IPv6: `Address family not supported by protocol` | `GRANIAN_HOST=0.0.0.0` v `env/netbox.env` |
| 81 | proměnné v quadletech prázdné | žádné `$PROMENNE` v `Exec`/`HealthCmd`, hesla v souborech |

Otevřené: varování při startu (č. 12), IPv6 link-local (43), NEDOSTUPNÉ z VLAN 333 v demo síti (48),
výchozí API pepper po migraci (85).

## Známé věci

- **Vypnuté IPv6** (`ipv6.disable=1`): NetBox nenastartuje s „Address family not supported by protocol“.
  V `env/netbox.env` odkomentovat `GRANIAN_HOST=0.0.0.0` a restartovat.
- **Retence**: `CHANGELOG_RETENTION` a `JOB_RETENTION` byly na původním stroji nastaveny na 0 (nemazat).
  Databáze pak jen roste, sledovat její velikost (výchozí stav 18. 9. 2026: 39 856 změn, 123 MB).
- **Bezpečnost**: heslo k IP Fabricu je v databázi NetBoxu v parametrech zdroje v čitelné podobě a bylo
  vloženo i do chatu. Na původním stroji zůstal výchozí veřejný `API_TOKEN_PEPPER_1` z netbox-docker;
  `install.sh` generuje nový, `import-on-rhel.sh` ale převezme starý, aby platily tokeny. Po přenosu
  doporučuji tokeny přegenerovat a pepper změnit.
- SELinux zůstává zapnutý; svazky jsou označené `:z`/`:Z`.
- `netbox_branching` je zamčený na 1.1.3, verze 1.2 vyžaduje NetBox 4.7.

Ověřeno v kontejnerovém prostředí (docker, ne RHEL): obraz se postaví, NetBox s oběma pluginy nastartuje,
migrace proběhnou, tři NetBox skripty se zaregistrují a záloha/obnova databáze funguje. Quadlety samotné
na RHEL9 spuštěné nebyly.
