# Kuchařka: instalace NetBoxu s IP Fabricem na RHEL9 bez internetu

Návod krok za krokem pro instalační balíček `netbox-offline-<datum>`. U každého příkazu je uvedeno,
pod kým se spouští:

- **[root]**: jako root, nebo přes `sudo` (vše, co pracuje s podmanem, systemd a `/opt`)
- **[uživatel]**: běžný uživatel, root není potřeba

Kontejnery běží pod rootem (rootful podman) jako systémové služby. Dají se tak spouštět při startu
serveru, a skripty proto pracují s nimi jen přes root.

---

## 0. Co bude potřeba

### Server

| | minimum | doporučeno |
|---|---|---|
| OS | RHEL **9.2** nebo novější (kvůli podman quadletům, podman ≥ 4.4) | RHEL 9.4+ |
| Architektura | x86_64 (amd64) | |
| CPU | 2 jádra | 4 jádra |
| RAM | 6 GB | 8 GB a víc (Batfish si bere kolem 3 GB) |
| Disk `/var/lib/containers` | 15 GB | 30 GB (obrazy mají asi 5 GB, k tomu databáze a zálohy) |
| Disk `/opt` | 5 GB | 10 GB (rozbalený balíček, konfigurace, zálohy v `/opt/netbox-offline/backups`) |
| Disk pro balíček | 3 GB | dočasně: archiv asi 1 GB a rozbalený asi 2 GB |
| Síť | port **8000/tcp** dovnitř (prohlížeč) | |
| | **443/tcp** ven na IP Fabric (jen když se data berou přímo z IP Fabricu) | |

SELinux může zůstat v režimu enforcing. Internet ani registrace RHEL (subscription) nejsou potřeba.

### Software, který musí být na serveru

| balík | k čemu | odkud |
|---|---|---|
| `container-tools` (podman, skopeo, buildah, …) | běh kontejnerů, quadlety | DVD/ISO RHEL9, AppStream |
| `tar`, `gzip`, `coreutils` | rozbalení a kontrola balíčku | standardně v RHEL |
| `python3` | konfigurátor IP Fabricu a skripty matice na hostiteli | standardně v RHEL (potřebuje ho `dnf`) |
| `firewalld` | volitelně, `install.sh` v něm otevře port | standardně v RHEL |
| `curl` | volitelně, kontrola, že NetBox odpovídá | standardně v RHEL |

Nic dalšího (Docker, pip, Python balíčky, Node) se na server neinstaluje. Všechno ostatní je v obrazech
kontejnerů uvnitř balíčku.

Ověření **[uživatel]**:

```bash
cat /etc/redhat-release          # Red Hat Enterprise Linux release 9.x
uname -m                         # x86_64
podman --version                 # 4.4 nebo vyšší (když chybí, viz krok 1)
python3 --version
df -h /var/lib/containers /opt   # volné místo
getenforce                       # Enforcing je v pořádku
```

---

## 1. Podman z instalačního DVD **[root]**

Přeskočte, pokud `podman --version` hlásí 4.4 nebo vyšší.

Na server nahrajte ISO stejné minor verze RHEL, jaká je nainstalovaná (např. `rhel-9.4-x86_64-dvd.iso`),
a připojte ho jako lokální repozitář:

```bash
mkdir -p /mnt/rhel9dvd
mount -o loop,ro /cesta/rhel-9.x-x86_64-dvd.iso /mnt/rhel9dvd

cat > /etc/yum.repos.d/rhel9-dvd.repo <<'EOF'
[dvd-baseos]
name=RHEL9 DVD BaseOS
baseurl=file:///mnt/rhel9dvd/BaseOS
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release
[dvd-appstream]
name=RHEL9 DVD AppStream
baseurl=file:///mnt/rhel9dvd/AppStream
enabled=1
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-redhat-release
EOF

dnf --disablerepo='*' --enablerepo='dvd-*' install -y container-tools tar firewalld python3 curl
podman --version
```

Pokud ve firmě běží Satellite nebo interní zrcadlo repozitářů, stačí `dnf install -y container-tools`.

Po instalaci lze DVD odpojit (`umount /mnt/rhel9dvd`) a `.repo` soubor smazat.

---

## 2. Stažení a instalace z RPM (nejjednodušší cesta)

Na počítači s přístupem na GitHub **[uživatel]**: stránka repozitáře → **Releases** → poslední verze
(např. `v1.0`) → v části *Assets* stáhnout:

- `netbox-offline-4.6.10-<datum>.el9.x86_64.rpm` (asi 1 GB)
- `netbox-offline-4.6.10-<datum>.el9.x86_64.rpm.sha256`

Přenést na server (USB disk, `scp`, sdílený disk) a tam **[root]**:

```bash
cd /tmp
sha256sum -c netbox-offline-*.rpm.sha256       # musí být OK
dnf install ./netbox-offline-*.rpm             # potřebuje podman z kroku 1 (dnf ho najde na DVD)
netbox-offline-install                         # = krok 4 níže: nahraje obrazy a spustí služby
```

RPM jen rozbalí balíček do `/opt/netbox-offline-balik` a přidá příkazy `netbox-offline-install`
a `netbox-ipfabric-config`. Pokračujte krokem 5. Kroky 2b a 3 jsou jen pro variantu bez RPM.

### 2b. Varianta bez RPM: archiv po částech **[uživatel]**

Na stránce repozitáře **Releases** stáhněte u poslední verze soubory:

- `netbox-offline-<datum>.tar.gz.part-00` (případně i `part-01`, …)
- `netbox-offline-<datum>.sha256`

Přeneste je na server (USB disk, `scp`, sdílený disk), například do `/root/instalace`:

```bash
scp netbox-offline-* admin@server:/tmp/              # [uživatel], z vašeho počítače
```

---

## 3. Složení, kontrola a rozbalení **[root]**

```bash
mkdir -p /root/instalace && cd /root/instalace
mv /tmp/netbox-offline-* .                           # pokud jste kopírovali do /tmp

cat netbox-offline-<datum>.tar.gz.part-* > netbox-offline-<datum>.tar.gz
sha256sum -c netbox-offline-<datum>.sha256           # všechny řádky musí být OK
tar xzf netbox-offline-<datum>.tar.gz
cd netbox-offline-<datum>
ls                                                   # images/ deploy/ quadlet/ env/ commatrix/ docs/ ...
```

Když `sha256sum -c` hlásí `FAILED`, je soubor poškozený přenosem a je potřeba ho stáhnout znovu.

---

## 4. Instalace **[root]**

```bash
cd /root/instalace/netbox-offline-<datum>
./deploy/install.sh
```

Skript udělá postupně tohle:

1. zkontroluje podman (≥ 4.4) a kontrolní součty všech souborů v balíčku,
2. nahraje obrazy do podmanu (`podman load`): NetBox s pluginy, PostgreSQL, Valkey a Batfish,
3. zkopíruje soubory do `/opt/netbox-offline` a vytvoří odkaz `/opt/commatrix`,
4. při prvním běhu vygeneruje náhodná hesla a klíče do `/opt/netbox-offline/env/`,
5. nainstaluje systemd jednotky (quadlety) do `/etc/containers/systemd/`,
6. otevře port 8000/tcp ve firewalld (jen když firewalld běží),
7. spustí služby a počká, až NetBox odpovídá. **První start dělá migrace databáze a trvá 5 až 10 minut**,
8. nahraje do NetBoxu skripty kontroly komunikační matice.

Na konci vypíše adresu NetBoxu a další kroky.

### Kam se co nainstaluje

| cesta | obsah |
|---|---|
| `/opt/netbox-offline/` | vše z balíčku kromě obrazů |
| `/opt/netbox-offline/env/netbox.env` | hesla, klíče a přístupy k IP Fabricu (práva 600, **nesdílet**) |
| `/opt/netbox-offline/env/postgres.env`, `valkey*.conf` | hesla databáze a cache |
| `/opt/netbox-offline/env/ipfabric.conf` | nastavení IP Fabricu bez hesel (vytvoří konfigurátor) |
| `/opt/netbox-offline/configuration/` | `plugins.py`, `extra.py`: konfigurace NetBoxu (úpravy se při upgradu zachovají) |
| `/opt/netbox-offline/backups/` | zálohy |
| `/opt/commatrix` → `/opt/netbox-offline/commatrix` | skripty a vzory matice, `ipf.env` |
| `/etc/containers/systemd/*.container`, `*.volume`, `netbox.network` | definice služeb |
| `/var/lib/containers/storage/volumes/` | data: databáze, Redis, média, skripty NetBoxu |

### Služby

| služba | co dělá |
|---|---|
| `netbox.service` | webové rozhraní a API na portu 8000 |
| `netbox-worker.service` | úlohy na pozadí (synchronizace s IP Fabricem, skripty) |
| `netbox-postgres.service` | databáze PostgreSQL 18 |
| `netbox-redis.service`, `netbox-redis-cache.service` | fronty a cache (Valkey) |
| `batfish.service` | analýza konfigurací firewallů (volitelná) |

Služby se spouštějí samy po restartu serveru.

---

## 5. První přihlášení

### Nový server: vytvořit správce **[root]**

```bash
/opt/netbox-offline/deploy/create-superuser.sh
```

### Nebo převzít data ze starého stroje **[root]**

Na starém Ubuntu stroji **[root]**: `./migrate/export-from-docker.sh` vytvoří `netbox-export-<datum>.tar.gz`.
Archiv přeneste a na RHEL9 spusťte:

```bash
/opt/netbox-offline/migrate/import-on-rhel.sh /cesta/netbox-export-<datum>.tar.gz
```

Převezme se databáze, média, skripty, `SECRET_KEY` a peppery API tokenů, takže platí stávající účty i tokeny.

Pak v prohlížeči **[uživatel]**: `http://<server>:8000/`

---

## 6. Napojení na IP Fabric SŽ **[root]**

```bash
netbox-ipfabric-config                              # při instalaci z RPM
/opt/netbox-offline/deploy/configure-ipfabric.py    # totéž bez RPM
```

Konfigurátor se zeptá na:

| dotaz | příklad | poznámka |
|---|---|---|
| URL IP Fabricu | `https://ipfabric.<domena>` | |
| CA certifikát | `/root/sz-ca.crt` nebo `-` | soubor PEM s interní CA, když certifikát IP Fabricu nepodepsala veřejná autorita |
| API token | (Enter = jméno a heslo) | token z IP Fabricu: Settings → Integration → API tokens |
| uživatel a heslo | | pro skripty kontroly matice |
| **verze IP Fabricu** | `7.5` | zjistí se sama, jinak ji zadejte. Musí sedět, jinak plugin data nenačte |

Výsledek: plugin dostane SDK odpovídající verzi (přepnutí běží bez internetu) a v NetBoxu vznikne zdroj
v **IP Fabric → Sources**. Konfigurátor ověří spojení a načte seznam snímků. Když spojení selže, vypíše
důvod a skončí kódem 2. Opravte příčinu (URL, firewall, certifikát, účet) a spusťte ho znovu.

Import dat do NetBoxu pak v prohlížeči: **IP Fabric → Syncs → Add** (zdroj, snímek, co importovat) a **Run**.

IP Fabric není ze serveru dostupný? Data se dají přenést jako soubor, postup je v `commatrix/README.md`
(„Snímek bez připojení k IP Fabricu“).

---

## 7. Kontrola komunikační matice

V prohlížeči **[uživatel]**: **Customization → Scripts → Komunikační matice v2 → Kontrola komunikační matice — v2 s odkazy na zařízení**, nahrát CSV matice
(vzor `commatrix/matrix-vzor.csv`) a spustit. Výsledek: OK / PORUŠENÍ MATICE / CHYBÍ PRAVIDLO / NEDOSTUPNÉ.

Skripty na hostiteli **[root]** (čtou přístupy z `/opt/commatrix/ipf.env`, který smí číst jen root):

```bash
cd /opt/commatrix
python3 commatrix_check.py matice.csv --out report.csv
```

Skripty, které jen zpracovávají soubory a `ipf.env` nepotřebují, smí spouštět i běžný uživatel.

---

## 8. Běžný provoz **[root]**

```bash
systemctl status 'netbox*'                     # stav služeb
podman ps                                      # běžící kontejnery
journalctl -u netbox -f                        # log webu
journalctl -u netbox-worker -f                 # log úloh (sync s IP Fabricem)
systemctl restart netbox netbox-worker         # restart po změně konfigurace
/opt/netbox-offline/deploy/nb-shell.sh skript.py KLIC=hodnota   # python skript v NetBox shellu
```

### Zálohy

```bash
/opt/netbox-offline/deploy/backup.sh           # ruční záloha do /opt/netbox-offline/backups (drží 14 posledních)
echo '15 2 * * * root /opt/netbox-offline/deploy/backup.sh' > /etc/cron.d/netbox-backup   # každou noc
/opt/netbox-offline/deploy/restore.sh /opt/netbox-offline/backups/<zaloha>   # obnova, ptá se na ANO
```

Zálohy kopírujte i mimo server.

### Upgrade na nový balíček

Nový balíček rozbalit jako v kroku 3 a znovu spustit `./deploy/install.sh`. Hesla, data, konfigurace
i nastavení IP Fabricu zůstanou, nahrají se jen nové obrazy. Konfigurátor IP Fabricu se spustí sám s
uloženým nastavením. Před upgradem udělejte zálohu.

---

## 9. Když něco nejde

| příznak | řešení |
|---|---|
| `chybi podman` / `podman je moc stary` | krok 1. Quadlety potřebují RHEL 9.2+ |
| `kontrolni soucty nesedi` | balíček je poškozený, stáhnout a přenést znovu |
| NetBox se nespustí, v `journalctl -u netbox` je `Address family not supported by protocol` | na serveru je vypnuté IPv6: v `/opt/netbox-offline/env/netbox.env` odkomentovat `GRANIAN_HOST=0.0.0.0` a `systemctl restart netbox netbox-worker` |
| `install.sh` čeká dlouho | první start dělá migrace (až 10 minut), sledujte `journalctl -u netbox -f` |
| stránka se z jiného počítače nenačte | `firewall-cmd --list-ports` musí obsahovat `8000/tcp`; zkontrolovat síťový firewall |
| konfigurátor: `CERTIFICATE_VERIFY_FAILED` | zadat CA certifikát IP Fabricu (PEM) |
| konfigurátor: `401` | špatný token nebo heslo |
| konfigurátor: timeout | firewall mezi serverem a IP Fabricem (443/tcp) |
| `verze X.Y neni podporovana` | plugin 6.1.0 umí IP Fabric 7.0, 7.2, 7.3, 7.5, 7.8, 7.9, 7.10, 7.11 |
| málo místa | `podman image prune` smaže staré obrazy po upgradu; `du -sh /var/lib/containers` |
| SELinux `avc: denied` | `ausearch -m avc -ts recent`; svazky mají `:z`, nekopírujte konfiguraci mimo `/opt/netbox-offline` |

Diagnostika pro podporu **[root]**:

```bash
systemctl --no-pager status 'netbox*' > diag.txt; podman ps -a >> diag.txt
journalctl -u netbox -u netbox-worker --no-pager -n 300 >> diag.txt
```

Soubor `diag.txt` neobsahuje hesla. Soubory z `env/` neposílejte.

---

## 10. Odinstalace **[root]**

```bash
systemctl stop netbox netbox-worker batfish netbox-redis netbox-redis-cache netbox-postgres
rm -f /etc/containers/systemd/netbox* /etc/containers/systemd/batfish*
systemctl daemon-reload
# data (nevratně!):  podman volume rm netbox-postgres-data netbox-redis-data netbox-media netbox-reports netbox-scripts batfish-data
# soubory:           rm -rf /opt/netbox-offline /opt/commatrix
dnf remove netbox-offline        # jen při instalaci z RPM (smaže /opt/netbox-offline-balik)
```
