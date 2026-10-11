# NetBox + IP Fabric: kontrola komunikační matice

NetBox 4.6.10 s pluginem IP Fabric a sadou Python skriptů, které ověřují komunikační matici
(kdo s kým smí v síti mluvit) proti skutečnému stavu sítě z IP Fabricu a hledají v ní chyby a díry.
Repo obsahuje vše potřebné k provozu na **RHEL9 bez přístupu k internetu** (podman + systemd quadlety).

| Kde | Co |
|---|---|
| [docs/PROJEKT.md](docs/PROJEKT.md) | o čem projekt je, proč a co má přinést |
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

### 1. Na stroji s internetem: postavit balíček

Potřeba je Linux s podmanem nebo dockerem (klidně stávající Ubuntu stroj) a ~4 GB místa.

```bash
git clone https://github.com/obhichus/netbox.git && cd netbox
./build/build-bundle.sh                 # nebo: CTR=docker ./build/build-bundle.sh
```

Výsledek je `dist/netbox-offline-<datum>.tar.gz` (obrazy jako `docker-archive`, konfigurace, skripty,
kontrolní součty) a vedle něj `.sha256`. Obrazy se stahují pro `amd64`.

Firemní IP Fabric 7.5 místo dema 7.9: v [build/plugin_requirements.txt](build/plugin_requirements.txt)
změnit extra `ipfabric_7_9` na `ipfabric_7_5` a balíček postavit znovu.

### 2. Přenést na RHEL9 a ověřit

```bash
sha256sum -c netbox-offline-<datum>.tar.gz.sha256
tar xzf netbox-offline-<datum>.tar.gz && cd netbox-offline-<datum>
```

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

## Offline a IP Fabric

NetBox na RHEL9 nepotřebuje internet. Pro data ze sítě jsou dvě cesty:

- **IP Fabric je dostupný v interní síti**: nastavit `IPF_URL`, `IPF_USER`, `IPF_PASS` v
  `/opt/netbox-offline/env/netbox.env` (pro skripty v kontejneru) a v `/opt/commatrix/ipf.env`
  (pro skripty na hostiteli), pak `systemctl restart netbox netbox-worker`.
- **IP Fabric dostupný není**: na stroji, který na něj vidí, uložit snímek do JSON (`IPF_DUMP_DIR`),
  přenést a nahrát přes `IPF_LOAD_DIR`. Postup je v [commatrix/README.md](commatrix/README.md).

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
