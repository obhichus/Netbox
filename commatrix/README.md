# commatrix: skripty kontroly komunikační matice

Na RHEL9 je tento adresář v `/opt/netbox-offline/commatrix` a dostupný i jako `/opt/commatrix`
(stejná cesta jako na původním stroji). Všechny skripty používají jen standardní knihovnu Pythonu,
takže na hostiteli stačí systémový `python3` z RHEL9 bez doinstalovaných balíčků.

## Matice

Formát (hlavička povinná):

```
name,src,dst,proto,port,expected
Sprava - SSH na pristupovy switch L35,10.39.255.1,10.35.255.194,tcp,22,allow
Sprava - telnet na L35 je zakazan,10.39.255.1,10.35.255.194,tcp,23,deny
```

| Soubor | Pro |
|---|---|
| `matice-demo.csv` | první demo snímek `8dc4dd8b-afc0-46ae-995c-38800e1df781` (36 řádků) |
| `matice-demo2.csv` | druhý demo snímek `22443e66-2430-4a55-b953-d7601b3f5148` (40 řádků). **Nedodělané:** dva slabé zdroje umírají na hopu 1 a dávají falešné nálezy, viz [CLAUDE.md](../CLAUDE.md) |
| `matrix-vzor.csv` | vzor formátu |

Matice je vázaná na snímek: adresy v ní musí v kontrolovaném snímku existovat.

Výsledek kontroly má čtyři verdikty: **OK**, **PORUŠENÍ MATICE** (zakázané prochází, řeší bezpečnost),
**CHYBÍ PRAVIDLO** (povolené zahodí firewall, řeší správce pravidel), **NEDOSTUPNÉ** (zahozeno bez
firewallu, chybí trasa, řeší síťaři). Běh s nálezy končí v NetBoxu stavem „failed“, to je záměr.

## NetBox skripty (Customization → Scripts)

Nahrává a registruje je `deploy/install-commatrix.sh` (spustit po každé změně).

| Soubor | Skript |
|---|---|
| `commatrix_v2.py` | **Kontrola komunikační matice — v2**: verdikty s odkazy na zařízení, souhrn podle závažnosti, CSV výstup. Pole `cesta` = soubor v kontejneru, např. `/opt/netbox/netbox/scripts/matice-demo2.csv` |
| `commatrix_script.py` | první verze kontroly (bez odkazů na zařízení) |
| `fw_prehled_script.py` | **Přehled firewallových pravidel**: široká povolení k revizi, přehled po prvcích. Celý běh z nástěnky zatím neověřen |

Čtou `IPF_URL`, `IPF_USER`, `IPF_PASS`, `IPF_SNAPSHOT` z `/opt/netbox-offline/env/netbox.env`.

## Skripty pro NetBox shell

Spouští se přes `deploy/nb-shell.sh` (náhrada `docker compose exec -T netbox manage.py shell < …`).

| Soubor | Co dělá |
|---|---|
| `push_ipf_data.py` | stáhne 11 tabulek snímku z IP Fabric API a vloží je do pluginu (zdroj v režimu *remote*); pak se spustí ingesce |
| `primarni_ip.py` | nastaví zařízením primární IP |
| `prefixy.py` | založí prefixy z naimportovaných adres |
| `export_konfigurace.py` | export konfigurace, která je jen v databázi (mapy, skripty, nástěnky, revize) do JSON (adresář `export-konfigurace/` v kořeni repa), viz [Záloha do gitu](#záloha-do-gitu) |

```bash
# import snímku z IP Fabricu
/opt/netbox-offline/deploy/nb-shell.sh /opt/commatrix/push_ipf_data.py IPF_SNAPSHOT=22443e66-2430-4a55-b953-d7601b3f5148
# spuštění ingesce (merge dělá plugin sám, sync má auto_merge)
podman exec -i netbox /opt/netbox/netbox/manage.py shell <<'PY'
from ipfabric_netbox.models import IPFabricSync
from users.models import User
s = IPFabricSync.objects.first()
u = User.objects.filter(is_superuser=True).order_by('pk').first()
print('job:', s.enqueue_sync_job(adhoc=True, user=u))
PY
```

Pořadí je vždy **push → ingesce → merge**. Přepnutí snímku nevyčistí objekty ze starého snímku,
úklid je v `docs/provoz-netboxu-s-ipfabric.html`, kapitola 7.

### Snímek bez připojení k IP Fabricu

Na stroji, který na IP Fabric vidí (třeba starý Ubuntu stroj), uložit snímek do JSON:

```bash
cd /opt/netbox-docker && docker compose exec -T \
  -e IPF_SNAPSHOT=22443e66-2430-4a55-b953-d7601b3f5148 \
  -e IPF_DUMP_DIR=/opt/netbox/netbox/scripts/snapshot-22443e66 \
  netbox /opt/netbox/netbox/manage.py shell < /opt/commatrix/push_ipf_data.py
docker compose cp netbox:/opt/netbox/netbox/scripts/snapshot-22443e66 ./snapshot-22443e66
```

Přenést adresář na RHEL9 a nahrát:

```bash
podman cp snapshot-22443e66 netbox:/opt/netbox/netbox/scripts/
podman exec -u root netbox chown -R netbox:root /opt/netbox/netbox/scripts/snapshot-22443e66
/opt/netbox-offline/deploy/nb-shell.sh /opt/commatrix/push_ipf_data.py IPF_LOAD_DIR=/opt/netbox/netbox/scripts/snapshot-22443e66
```

Ve výpisu má být `Ctu ulozeny snapshot z …`. Pozor: kontrola matice (simulace cest) ale potřebuje
živý IP Fabric; offline jde jen inventář.

## Nástroje pro hostitele

Čtou `/opt/commatrix/ipf.env` (vzor `ipf.env.example`, práva 600).

| Soubor | Co dělá |
|---|---|
| `commatrix_check.py` | kontrola matice bez NetBoxu, výstup CSV (`python3 commatrix_check.py matice.csv --out report.csv`) |
| `ipf_discover.py` | zmapuje tabulky a sloupce, které instance IP Fabricu nabízí |
| `ipf_to_netbox.py` | starší import přes REST API NetBoxu (nahrazen pluginem + `push_ipf_data.py`) |
| `fw_discover.py` | zjistí dostupné tabulky bezpečnostních pravidel |
| `fw_na_matici.py` | převede pravidla firewallů na kandidátní matici `matice-z-firewallu.csv` (obrácená kontrola) |
| `fw_prehled.py` | přehled kvality pravidel do CSV |

`provoz-netbox-ipfabric.txt` je textová verze provozní dokumentace.

## Záloha do gitu

`zaloha_na_git.sh` (Romanův skript pro původní Ubuntu stroj) zkopíruje skripty a data z `/opt/commatrix`
(`*.py *.csv *.txt *.md *.sh`, nikdy `ipf.env` ani `dump/`), vybrané soubory z `/opt/netbox-docker`
(bez `env/`), spustí `export_konfigurace.py` a vyzvedne JSONy do `export-konfigurace/`. Před commitem
zkontroluje, že se nepřidává tajný soubor ani hodnota hesla z `ipf.env` nebo heslo zapsané v kódu
(výjimky do `.zaloha-povoleno`). Volby `--bez-push`, `--bez-exportu`, `--zprava "text"`.

`export_konfigurace.py` exportuje konfiguraci, která je jen v databázi: transformační mapy pluginu,
registrace NetBox Scriptů, nástěnky a aktivní konfigurační revizi. Záměrně vynechává `IPFabricSource`
(přístupové údaje), provozní data pluginu a klíče revize s PASSWORD/SECRET/TOKEN/KEY/CREDENTIAL.
Na RHEL9: `deploy/nb-shell.sh /opt/commatrix/export_konfigurace.py`.
