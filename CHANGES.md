# CHANGES

Historie změn a všech problémů, které se při stavbě a provozu řešily. Nejnovější nahoře.
Každý problém má **Příznak / Příčina / Řešení / Stav** (vyřešeno · obejito · otevřené).
Hesla, tokeny a adresy strojů jsou záměrně vynechány.

## 2026-10-12: ochrana větve main a údaje o repu

- Repo má popis, homepage (Release v1.0), topics a zapnuté mazání větví po merge.
- Ruleset „Ochrana main“: zákaz smazání a force-push, změny jen přes PR, povinný check `rhel9`,
  admin může obejít. Nastaveno přes `gh` na vlastním stroji (skript `nastav-repo.sh` ve sdílených souborech projektu).
- **Příznak:** zápis nastavení repa z cloudové session končí HTTP 403.
  **Příčina:** proxy cloudového prostředí nepovoluje měnit nastavení repozitáře.
  **Řešení:** spustit `gh api` na stroji, kde je `gh` přihlášený. **Stav:** obejito.
- **Příznak:** PR jen s dokumentací by na povinný check `rhel9` čekal donekonečna.
  **Příčina:** workflow měl `paths-ignore` pro dokumentaci, takže se vůbec nespustil.
  **Řešení:** workflow běží u každého PR a u čistě dokumentačních změn kroky testu přeskočí. **Stav:** vyřešeno.

## 2026-10-12: jedna větev

- Do `main` sloučena větev s rozborem open-source náhrady IP Fabricu
  ([docs/opensource-misto-ipfabric.md](docs/opensource-misto-ipfabric.md)), odkaz v README.
- Všechny ostatní větve (`offline-rhel9`, `rpm-balik`, `ghcr-obraz` a pracovní větve Claude) smazány;
  jejich obsah už v `main` byl. Tag `v1.0` zůstává.

## 2026-10-12: obraz v GitHub Packages

- Workflow „Offline balicek RHEL9“ publikuje obraz NetBoxu s pluginy do `ghcr.io/obhichus/netbox-ipfabric`
  (štítky verze NetBoxu, tagu release a `latest`); obraz má štítek `org.opencontainers.image.source`,
  takže se zobrazí v záložce Packages repozitáře. RPM a archiv zůstávají v Releases.
- Kuchařka: kapitola 2c (stažení obrazu z ghcr.io).

## 2026-10-11 (večer): RPM a release v1.0

- `build/build-rpm.sh`: RPM `netbox-offline-<verze>-<datum>.el9.x86_64.rpm` (zstd, asi 1 GB). Rozbalí balíček do
  `/opt/netbox-offline-balik` a přidá příkazy `netbox-offline-install` a `netbox-ipfabric-config`; vyžaduje `podman >= 4.4`.
- Workflow „Offline balicek RHEL9“ přikládá k release RPM, archiv po částech, prezentaci pro vedení a kuchařku.
- Test na Rocky Linux 9 instaluje z RPM (`dnf install` bez sítě).
- Kuchařka: instalace z RPM jako hlavní cesta.

## 2026-10-11: repozitář a offline balíček pro RHEL9

### Změny

- Založen repozitář: skripty z `/opt/commatrix`, matice, původní konfigurace netbox-docker, databázové kroky,
  provozní dokument, runbook, prezentace a popis projektu (`docs/PROJEKT.md`).
- Offline nasazení na RHEL9: `build/build-bundle.sh` (stroj s internetem) → archiv s obrazy →
  `deploy/install.sh` (RHEL9, podman + systemd quadlety). Záloha, obnova, `nb-shell.sh`, `install-commatrix.sh`.
- Migrace dat ze starého Ubuntu stroje: `migrate/export-from-docker.sh` a `migrate/import-on-rhel.sh`.
- Batfish je součástí balíčku jako volitelná služba.
- Konfigurátor napojení na IP Fabric `deploy/configure-ipfabric.py`: verze IP Fabricu SŽ (7.5), offline
  přepnutí SDK, CA certifikát, přístupy pro skripty a zdroj v pluginu (problém č. 88).
- Kuchařka instalace `docs/INSTALACE-RHEL9.md` (v balíčku `INSTALACE.md`): požadavky, podman z DVD,
  co kam se nainstaluje, root vs. uživatel, provoz, řešení potíží, odinstalace.
- Test instalace balíčku na Rocky Linux 9 v GitHub Actions (`test/rhel9-e2e.sh`, instalace bez sítě).

### Problémy řešené při přípravě balíčku

#### 79. pip stáhl netbox_branching 1.2.2 a NetBox nenastartoval
- **Příznak:** `collectstatic` při stavbě obrazu padal na `RuntimeError: Model class netbox_branching.models.changes.ObjectChange doesn't declare an explicit app_label and isn't in an application in INSTALLED_APPS.`, ve varování `Plugin netbox_branching requires NetBox minimum version 4.7.0 (current: 4.6.10)`.
- **Příčina:** `ipfabric_netbox` vyžaduje jen `netbox-branching>=1.0.4`, pip tedy vzal nejnovější 1.2.x, která je jen pro NetBox 4.7 (stejný problém jako č. 20).
- **Řešení:** v `build/plugin_requirements.txt` napevno `netboxlabs-netbox-branching==1.1.3` (poslední pro 4.6, `max_version 4.6.99`) a `ipfabric_netbox[ipfabric_7_9]==6.1.0`.
- **Stav:** vyřešeno.

#### 80. NetBox nenastartuje na stroji bez IPv6
- **Příznak:** kontejner `netbox` končí `RuntimeError: Address family not supported by protocol (os error 97)` z granianu.
- **Příčina:** `launch-netbox.sh` v obrazu netbox-docker poslouchá napevno na `::`. Na RHEL serverech s `ipv6.disable=1` to nejde.
- **Řešení:** `build/Containerfile` upraví skript na `--host "${GRANIAN_HOST:-::}"`; v `env/netbox.env` stačí odkomentovat `GRANIAN_HOST=0.0.0.0`.
- **Stav:** vyřešeno (ověřeno v kontejneru bez IPv6).

#### 81. systemd v quadletech rozbaluje `$PROMENNE`
- **Příznak:** healthcheck PostgreSQL převzatý z netbox-docker (`pg_isready -d $POSTGRES_DB -U $POSTGRES_USER`) a spuštění Valkey s `--requirepass $REDIS_PASSWORD` by v systemd dostaly prázdné hodnoty.
- **Příčina:** quadlet z `HealthCmd=`/`Exec=` dělá `ExecStart=` a systemd v něm proměnné nahradí svými (prázdnými) dřív, než se dostanou do kontejneru. V docker compose se to řešilo `$$`.
- **Řešení:** healthcheck s pevnými hodnotami (`-d netbox -U netbox`), heslo pro Valkey v konfiguračním souboru `env/valkey.conf` generovaném při instalaci.
- **Stav:** vyřešeno (`quadlet -dryrun` s podman 4.9).

#### 82. Konfigurace NetBoxu v podadresáři se nenačte
- **Příznak:** návrh primountovat celý adresář konfigurace jinam než přímo do `/etc/netbox/config/`.
- **Příčina:** loader netbox-docker čte jen soubory `*.py` přímo v `/etc/netbox/config/`, podadresáře ignoruje.
- **Řešení:** `extra.py` a `plugins.py` se mountují jednotlivě přes výchozí soubory v obrazu (jsou v obrazu i zapečené kvůli `collectstatic`).
- **Stav:** vyřešeno.

#### 83. Heslo databáze napsané dvakrát (`plugins.py` a env)
- **Příznak:** na původním stroji muselo heslo v `configuration/plugins.py` ručně odpovídat `POSTGRES_PASSWORD` a `DB_PASSWORD` (README.txt kap. 8, „na tohle se snadno zapomene“).
- **Příčina:** `DATABASES` pro netbox_branching bylo v `plugins.py` vypsané celé i s heslem.
- **Řešení:** `plugins.py` bere `DATABASES` z hlavní konfigurace (`from netbox.configuration.configuration import DATABASES`) a jen ho obalí `DynamicSchemaDict`. Heslo je jen v `env/`.
- **Stav:** vyřešeno.

#### 84. Skripty kontroly na čisté instalaci nejsou vidět
- **Příznak:** soubor zkopírovaný do `/opt/netbox/netbox/scripts/` se v Customization → Scripts neobjeví; na starém stroji se navíc kopírovalo zvlášť do `netbox` i `netbox-worker` a ručně chownovalo.
- **Příčina:** NetBox 4.x potřebuje k souboru záznam `ScriptModule`; worker si drží načtené moduly.
- **Řešení:** `deploy/install-commatrix.sh` nakopíruje skripty a matice do společného svazku, nastaví vlastníka `netbox`, vytvoří chybějící `ScriptModule` a restartuje služby. Ověřeno: zaregistrují se `KontrolaKomunikacniMaticeV2`, `KontrolaKomunikacniMatice`, `PrehledFirewallovychPravidel`.
- **Stav:** vyřešeno.

#### 85. Výchozí `API_TOKEN_PEPPER_1` z netbox-docker
- **Příznak:** na původním stroji zůstal veřejně známý pepper ze vzorového `env/netbox.env`.
- **Řešení:** `deploy/install.sh` generuje nový. Při migraci `import-on-rhel.sh` záměrně převezme starý, aby platily stávající API tokeny; po přenosu je potřeba tokeny přegenerovat a pepper změnit.
- **Stav:** otevřené (na straně provozu).

#### 86. Popis repozitáře na GitHubu nejde nastavit z Claude
- **Příznak:** `gh repo edit --description` → `HTTP 403: Repository settings writes are not permitted through this proxy.`
- **Řešení:** nastavit ručně na stránce repa (About → ozubené kolečko).
- **Stav:** obejito.

#### 87. Prezentace pro vedení (`netbox-sz-vedeni.pptx`) v repu chybí
- **Příčina:** vznikla jen jako soubor v původní pracovní session, ne na disku stroje.
- **Řešení:** z přepisu session obnoven generátor `gen.js` (pptxgenjs) včetně obou pozdějších úprav a prezentace znovu vygenerována do `docs/prezentace-vedeni/` (velikost souhlasí s originálem).
- **Stav:** vyřešeno.

#### 88. Verze SDK `ipfabric` musí sedět s verzí IP Fabricu SŽ
- **Příznak:** obraz se stavěl s SDK pro 7.9 (demo), SŽ provozuje IP Fabric 7.5; na offline RHEL9 nejde SDK doinstalovat z internetu.
- **Příčina:** plugin `ipfabric_netbox` komunikuje přes SDK `ipfabric`, které musí mít stejné major.minor jako server (extra `ipfabric_7_5` apod.).
- **Řešení:** obraz nese wheely SDK pro všechny podporované verze (7.0–7.11) v `/opt/ipfabric-wheels`. `deploy/configure-ipfabric.py` zjistí verzi serveru (`/api/version`) nebo se zeptá, postaví bez sítě odvozený obraz `…-ipf7.5`, přepne quadlety, zapíše přístupy a vytvoří zdroj v NetBoxu. Na konci ověří spojení přes SDK pluginu a načte snímky (zdroj v režimu `local`). Ověřeno přepnutí na 7.3 i 7.5 bez sítě a chybová větev testu spojení; úspěšné načtení snímků vyžaduje skutečný IP Fabric.
- **Stav:** vyřešeno.

#### 89. `install.sh` na čistém serveru skončil hned po „hesla a env soubory“ (kód 2)
- **Příznak:** test na Rocky Linux 9 (GitHub Actions): po kopírování souborů skript bez hlášky skončil s kódem 2.
- **Příčina:** `envval` četl hesla z `netbox.env`, který při první instalaci ještě neexistuje; `sed` vrátil 2 a díky `set -o pipefail` to ukončilo skript. V testech v dockeru se to neprojevilo, protože `install.sh` tam neběžel.
- **Řešení:** `envval` při chybějícím souboru vrací prázdnou hodnotu.
- **Stav:** vyřešeno.

#### 90. Hned po `install.sh` NetBox chvíli neodpovídal
- **Příznak:** test na Rocky Linux 9: instalace doběhla, ale okamžitý `curl http://127.0.0.1:8000/login/` skončil „connection refused“.
- **Příčina:** `install-commatrix.sh` na konci restartuje `netbox` a `netbox-worker` a nečekal, až NetBox znovu naběhne.
- **Řešení:** `install-commatrix.sh` po restartu čeká na healthcheck (max. 5 minut).
- **Stav:** vyřešeno.

#### 91. SDK pro IP Fabric 7.5 (verze SŽ) v obrazu nefungovalo
- **Příznak:** test na Rocky Linux 9: po přepnutí na 7.5 plugin hlásil `PydanticUserError: IPFClient is not fully defined; you should define LifeCycleHook`. Plugin by se na IP Fabric SŽ vůbec nepřipojil, i když instalace a přepnutí verze prošly.
- **Příčina:** SDK `ipfabric` 7.5.x (7.5.0 až 7.5.2) nefunguje s knihovnou `niquests` 3.16 a novější, kterou obraz obsahuje (3.21). Ostatní verze SDK (7.0 až 7.3, 7.8 až 7.11) jsou v pořádku; ověřeno pro každou zvlášť.
- **Řešení:** požadavky na SDK pro jednotlivé verze jsou na jednom místě v `build/ipfabric-sdk-spec.sh` (pro 7.5 navíc `niquests<3.16`) a obraz nese i potřebné wheely. `check.py` v obrazu ověří, že SDK opravdu vytvoří klienta; spouští se při stavbě obrazu, v `build-bundle.sh` pro všech 8 verzí bez sítě, v konfigurátoru i v testu. Konfigurátor odvozený obraz staví vždy znovu z aktuálního základu, aby po upgradu nezůstala stará verze NetBoxu.
- **Stav:** vyřešeno.

## 2026-09-04 až 2026-09-18: stavba pilotu na Ubuntu stroji

### 2026-09-04: údržba Ubuntu hostitele a starý NetBox

#### 1. Jádro zaseknuté na 6.5 a zadržené balíky
- **Příznak:** po `apt upgrade` zůstávalo jádro 6.5 a část balíků byla „kept back“.
- **Příčina:** metabalíky HWE-22.04 (pozůstatek po upgradu distribuce) dál táhly řadu 6.5; noble HWE se nenainstaloval sám.
- **Řešení:** ručně doinstalován `linux-generic` (6.8.0-139), pak `apt full-upgrade`.
- **Stav:** vyřešeno.

#### 2. MOTD stále hlásil „61 updates could not be installed automatically“
- **Příznak:** hláška v MOTD i po úspěšném upgradu.
- **Příčina:** zastaralý soubor `/var/lib/unattended-upgrades/kept-back`.
- **Řešení:** `unattended-upgrade -v` soubor přepočítal.
- **Stav:** vyřešeno.

#### 3. Staré jádro 6.5.0-28 nešlo uklidit autoremove
- **Příznak:** `apt autoremove` balíky starého jádra ignoroval; adresář v `/lib/modules` nešel smazat („not empty“).
- **Příčina:** balíky byly označené jako ručně instalované; v adresáři zůstaly `.ko` moduly VirtualBoxu.
- **Řešení:** explicitní `apt purge` balíků 6.5, `update-grub`, ruční smazání zbytkového adresáře modulů.
- **Stav:** vyřešeno.

#### 4. VirtualBox po přechodu na jádro 6.8
- **Příznak:** moduly Oracle VirtualBox 7.1 nebyly pro 6.8 sestavené.
- **Příčina:** Oracle balík nemá DKMS. Asistentův `apt install --reinstall virtualbox-dkms` navíc nechtěně nahradil Oracle 7.1.4 distribuční verzí 7.0.16, šlo tedy o downgrade.
- **Řešení:** ověřeno, že nastavení VM (formát 1.19) jde v 7.0.16 otevřít. Zůstalo se na 7.0.16 + DKMS, „rc“ zbytky Oracle balíku byly vyčištěny. Secure Boot je vypnutý, takže podepisovat moduly netřeba.
- **Stav:** obejito (funkční, ale na starší verzi VirtualBoxu).

#### 5. Repozitář Dockeru ukazoval na `mantic`
- **Příznak:** apt pro Docker bral balíky pro starou verzi Ubuntu. Po opravě se objevilo `N: Ignoring file 'docker.list.bak-2026-09-04' ... invalid filename extension`.
- **Příčina:** zdroj nebyl po upgradu distribuce přepsán; zálohu apt ve `sources.list.d` odmítá kvůli příponě.
- **Řešení:** `mantic` → `noble`, záloha přesunuta do `/root`.
- **Stav:** vyřešeno.

#### 6. Ubuntu Pro / ESM (37 čekajících aktualizací)
- **Příznak:** `pro attach --attach-config` vrátil „Invalid token“.
- **Příčina:** místo tokenu byl vložen jednorázový „magic“ kód z webu. Účet Ubuntu One ani uložený token neexistoval.
- **Řešení:** později připojeno správným tokenem (esm-apps, esm-infra, livepatch).
- **Stav:** vyřešeno.

#### 7. Starý stack `/opt/fw_stack`: kontejnery ve stavu „Created“
- **Příznak:** 4 kontejnery (netbox, worker, celery_beat, batfish) se nespustily. Restart policy byla v pořádku.
- **Příčina:** compose byl převzatý z návodu ve stylu Nautobotu. Worker volal `celery` a končil chybou `Unknown command: 'celery'`.
- **Řešení:** příkaz workeru změněn na `rqworker`. Uživatel nejdřív vkládal YAML přímo do shellu („command not found“), proto se přešlo na zápis přes heredoc.
- **Stav:** vyřešeno (stack později nahrazen netbox-dockerem).

#### 8. Služba housekeeping ve starém stacku
- **Příznak:** chyběl `/opt/netbox/housekeeping.sh` a služba logovala `Unknown command: 'housekeeping'`.
- **Příčina:** novější NetBox housekeeping jako příkaz nemá; úklid dělá RQ scheduler (úloha System Housekeeping).
- **Řešení:** služba odstraněna z compose.
- **Stav:** vyřešeno.

#### 9. NetBox na portu 8000 neodpovídal
- **Příznak:** `curl` vracel prázdnou odpověď nebo „Connection reset by peer“.
- **Příčina:** v kontejneru ještě běžely migrace.
- **Řešení:** počkat na doběhnutí migrací.
- **Stav:** vyřešeno.

#### 10. Výchozí (ukázková) hesla a otevřená instance
- **Příznak:** v `env/netbox.env` 4 výskyty vzorových hesel, port publikovaný na všech rozhraních, `ALLOWED_HOSTS=*`.
- **Příčina:** konfigurace převzatá z návodu.
- **Řešení:** nový SECRET_KEY, heslo DB (`\password`), heslo Redisu, `down/up`. `changepassword` nejdřív odmítl heslo („This password is too short. It must contain at least 12 characters. / Password must have at least one numeral.“), zvoleno silnější. Omezení portu jen na localhost uživatel odmítl (port 8000 zůstal dostupný v LAN).
- **Stav:** vyřešeno, port v LAN zůstává vědomě otevřený.

#### 11. Tag `latest` potichu nasadil NetBox 4.7.0
- **Příznak:** po pullu proběhly migrace na 4.7.0, aniž by to kdo chtěl.
- **Příčina:** obraz s tagem `latest` bez pinování verze.
- **Řešení:** doporučeno pinovat konkrétní tag; vyřešeno přechodem na netbox-docker s pevnou verzí (viz 15).
- **Stav:** vyřešeno.

#### 12. Varování při startu NetBoxu
- **Příznak:** `API_TOKEN_PEPPERS is not defined` a `FutureWarning: LOGIN_REQUIRED is deprecated`.
- **Příčina:** konfigurace z předchozí verze.
- **Řešení:** nic, jen kosmetika; varování se v logu objevuje dál.
- **Stav:** otevřené (neškodné).

#### 13. Prostý obraz NetBoxu neumí pluginy
- **Příznak:** do oficiálního obrazu nešlo doinstalovat ipfabric_netbox a branching.
- **Příčina:** pluginy se musí zabudovat do vlastního obrazu.
- **Řešení:** rozhodnutí přejít na netbox-docker (varianta 1) s `Dockerfile-Plugins`.
- **Stav:** vyřešeno.

#### 14. netbox-docker: chybějící soubory a neexistující služba
- **Příznak:** `Dockerfile-Plugins: No such file or directory`; odkaz na dokumentaci vracel 404; služba `netbox-housekeeping` v override neexistovala.
- **Příčina:** `Dockerfile-Plugins` repozitář neobsahuje, je jen popsaný ve wiki. netbox-docker 5.x službu housekeeping nemá.
- **Řešení:** podle wiki ručně vytvořeny `Dockerfile-Plugins`, `plugin_requirements.txt` a `docker-compose.override.yml`; služba z override odstraněna.
- **Stav:** vyřešeno.

#### 15. Build na NetBoxu 4.7 padal v collectstatic
- **Příznak:** `NotImplementedError: GraphQL type for model field 'core.Job.execution_time' has not been implemented`.
- **Příčina:** NetBox 4.7 byl dva dny starý a závislosti pluginu (strawberry-graphql-django) na něj ještě nebyly připravené.
- **Řešení:** downgrade na `v4.6.10-5.0.2`: `FROM` v Dockerfile, `VERSION` v `.env`, název obrazu v override; repo přepnuto na tag 5.0.2.
- **Stav:** vyřešeno.

#### 16. DNS uvnitř kontejnerů při buildu
- **Příznak:** uv hlásil „dns error / failed to lookup address information: Try again“.
- **Příčina:** hostitel používá stub resolver systemd (127.0.0.53) a search doménu Tailscale; kontejnery to nepřevzaly.
- **Řešení:** `/etc/docker/daemon.json` s klíčem `dns` (veřejné resolvery), restart Dockeru.
- **Stav:** vyřešeno.

#### 17. Extrémně pomalá a nestabilní síť (LTE)
- **Příznak:** ping `sendmsg: No buffer space available`, RTT až 38–48 s, 11 % ztrát; speedtest „Cannot open socket“ / „Couldn't resolve host name“. RTT klesalo přesně o 1 s na paket. Při vypnutém Tailscale hlásil mtr „Temporary failure in name resolution“.
- **Příčina:** postupně vyloučeny Wi-Fi (USB TL-WN722N, ovladač rtl8xxxu, signál -31 dBm, 0 retries) i DNS. Ethernet nebyl zapojený. Klesající RTT ukazovalo na bufferbloat, tedy vyprazdňování fronty. Skutečný viník: LTE hotspot TP-Link M7000 (O2, CGNAT) přiškrcený po 241 GB (FUP).
- **Řešení:** zkoušeny parametry modulu `ht40_2g`/`dma_aggregation` přes systemd-run s pojistkou `shutdown -r +20` (bez efektu). Nasazeno `fq_codel`. Out-of-tree DKMS ovladače jsou na jádře 6.8 slepá ulička (rozbité `skb_pull`, podpora jen do 6.3). Snap „code“ 44 minut neúspěšně auto-refreshoval, proto bylo připojení označeno jako metered a nastaveno `snap refresh.metered=hold`. Přidán monitor `linkmon.service`. Tailscale byl dočasně vypnutý a 09-05 zase zapnut. Doporučen kabel nebo adaptér MT76.
- **Stav:** obejito (příčina na straně operátora; build dotlačen obezličkami v bodě 18).

#### 18. Build a pull padaly na pomalé lince
- **Příznak:** přerušovaný `docker pull` a timeouty uv proti PyPI.
- **Příčina:** linka viz bod 17.
- **Řešení:** Docker `max-concurrent-downloads 1` a `max-download-attempts 10`; v `Dockerfile-Plugins` `UV_HTTP_TIMEOUT=300` a `UV_CONCURRENT_DOWNLOADS=1`; nohup smyčka `until` (pull → build → up) s logem do `/var/log/netbox-build*.log`. Navržené systemd jednotky pro build a stack uživatel odmítl.
- **Stav:** obejito.

---

### 2026-09-05: dokončení stacku

#### 19. Reboot po fwupd zabil běžící build
- **Příznak:** po aktualizaci firmwaru (db 2011→2023, dbx) a restartu nohup build neběžel.
- **Příčina:** restart systému.
- **Řešení:** smyčka buildu spuštěna znovu. Aktualizace dbx nemá při vypnutém Secure Bootu vliv.
- **Stav:** vyřešeno.

#### 20. Plugin branching vyžadoval NetBox 4.7
- **Příznak:** `Plugin netbox_branching requires NetBox minimum version 4.7.0 (current: 4.6.10)`.
- **Příčina:** uv stáhl netboxlabs-netbox-branching 1.2.0; podle COMPATIBILITY.md patří k 4.6 řada 1.1.x.
- **Řešení:** v `plugin_requirements.txt` připnuto `netboxlabs-netbox-branching<1.2` (výsledek 1.1.3), předem ověřeno přes `uv --dry-run`.
- **Stav:** vyřešeno.

#### 21. Kontejner netbox „unhealthy“ kvůli Redisu
- **Příznak:** `dependency failed to start: container netbox-docker-netbox-1 is unhealthy`; v logu `redis.exceptions.AuthenticationError: invalid username-password pair`.
- **Příčina:** sed při rotaci hesel nezměnil `REDIS_PASSWORD` a `REDIS_CACHE_PASSWORD` v `env/netbox.env`, takže neseděly s env Redisu.
- **Řešení:** hodnoty sjednoceny (kontrola přes md5sum), `up -d`; zdravý stav ve 12:53.
- **Stav:** vyřešeno.

#### 22. Neexistující uživatel admin
- **Příznak:** `CommandError: user 'admin' does not exist`.
- **Příčina:** netbox-docker 5.x ve výchozím stavu superuživatele nezakládá.
- **Řešení:** `manage.py createsuperuser`.
- **Stav:** vyřešeno.

#### 23. Úklid starého stacku a plný disk
- **Příznak:** disk zaplněný na 88 %; souběžně ležel starý stack a duplicitní obrazy.
- **Příčina:** pozůstatky `/opt/fw_stack`, build cache a obraz `netbox:latest` (stejné ID jako 4.7).
- **Řešení:** archiv `/root/fw_stack-archiv-2026-09-05.tar.gz` (včetně dumpu DB), smazány volumes a obrazy, `builder prune` uvolnil 648 MB. Volumes MISP patří šéfovi a zůstaly.
- **Stav:** vyřešeno.

#### 24. Vzdálený grafický přístup
- **Příznak:** uživatel nebyl u PC, potřeboval GUI.
- **Příčina:** —
- **Řešení:** nastaveno xrdp (mimo jiné snížená barevná hloubka kvůli pomalé lince).
- **Stav:** vyřešeno.

---

### 2026-09-06: plugin ipfabric_netbox, IP Fabric API a první import

#### 25. Nesoulad verze SDK s IP Fabricem
- **Příznak:** demo IP Fabric běží na 7.9.4, plugin byl postaven s extra `ipfabric_7_5`.
- **Příčina:** SDK musí odpovídat verzi IP Fabricu.
- **Řešení:** extra změněna na `ipfabric_7_9` (SDK 7.9.1), rebuild.
- **Stav:** vyřešeno.

#### 26. Šedé tlačítko ingesce / „loaded 1“
- **Příznak:** Sync nešlo spustit; plugin hlásil jeden snapshot.
- **Příčina:** plugin sám založil snapshot `$last`. `ready_for_sync` vracelo False, protože `snapshot_data.ipf_data.count()==0`. `enqueue_sync_job(request=None)` padal.
- **Řešení:** nejdřív naplnit data snapshotu; při volání z shellu předat `SimpleNamespace(user=..., id=None)`, později `enqueue_sync_job(adhoc=True, user=u)`.
- **Stav:** vyřešeno.

#### 27. Sync zdroje: chybějící autentizace
- **Příznak:** po 0,24 s „Syncing Snapshot Failed: `IP Fabric Authentication not provided.`“ / „Unable to connect to IP Fabric.“
- **Příčina:** formulář zdroje nemá pole pro autentizaci a `parameters` obsahovaly jen `{'timeout': 9}`.
- **Řešení:** ze SDK zjištěn klíč `auth` v `parameters`, doplněn přes ORM.
- **Stav:** vyřešeno (dále viz 28–29).

#### 28. „Failed to Authenticate“: bash rozexpandoval heslo
- **Příznak:** `niquests.exceptions.HTTPError: Failed to Authenticate`.
- **Příčina:** heslo obsahuje `$*` a v dvojitých uvozovkách ho bash rozexpandoval.
- **Řešení:** Python předáván přes heredoc `<<'PY'` bez expanze. Heslo uniklo do chatu, proto doporučena jeho změna.
- **Stav:** vyřešeno.

#### 29. Nedostatečná práva demo účtu v IP Fabricu
- **Příznak:** „User or Token does not have access to 'POST /prepared-requests'“; `/api/tables/management/snapshots` → 403 `API_INSUFFICIENT_RIGHTS: Insufficient Rights`.
- **Příčina:** omezená role demo účtu. `/api/snapshots` vrací 200 a tabulková API fungují přes POST.
- **Řešení:** vlastní cesta mimo vestavěný sync zdroje (body 33–34).
- **Stav:** obejito.

#### 30. Tabulková API vracela 422 / 404
- **Příznak:** `422 "Array must contain at least 1 element(s)"` (chybějící columns); některé hádané cesty 404. Skript `ipf_discover.py` vypadal zaseknutý na pomalé tabulce QoS (timeout 90 s).
- **Příčina:** API vyžaduje výčet sloupců; názvy tabulek se v 7.9 liší od odhadů.
- **Řešení:** trik s neplatnou hodnotou enumu, kdy 422 odpověď vypíše platné sloupce; druhé kolo průzkumu s opravenými cestami.
- **Stav:** vyřešeno.

#### 31. Žádné konfigurace pro Batfish, path lookup přes API
- **Příznak:** `management/configuration` má 0 řádků. `/api/graphs/*` vracelo 404, `/api/graphs` 422 `"parameters" does not match any of the allowed types`.
- **Příčina:** demo nesbírá konfigurace; formát těla dotazu na graf není triviální.
- **Řešení:** místo Batfishe simulace cest v IP Fabricu; tělo dotazu sestaveno přes SDK `ipfabric.diagrams.Unicast(...).model_dump()`.
- **Stav:** obejito.

#### 32. Kontrola matice: přihlášení a UDP dotazy
- **Příznak:** „Nelze se pripojit k IP Fabric: Prihlaseni selhalo, server nevratil accessToken.“ Dále řádky UDP končily „CHYBA DOTAZU“ (422).
- **Příčina:** login IP Fabricu je založený na cookies (niquests předtím fungoval omylem s „Bearer None“). U UDP se posílaly TCP `l4Options` (flags).
- **Řešení:** `http.cookiejar` v `commatrix_check.py`; UDP bez flags, ICMP přes type/code.
- **Stav:** vyřešeno.

#### 33. Custom Objects v NetBox 4.6 Community nejsou
- **Příznak:** seznam modelů prázdný (`[]`).
- **Příčina:** funkce není v komunitní verzi 4.6.
- **Řešení:** kontrola matice napsána jako NetBox Script.
- **Stav:** obejito.

#### 34. Nahrání skriptu: PermissionError
- **Příznak:** `PermissionError [Errno 13] Permission denied: '/opt/netbox/netbox/scripts/commatrix_script.py'`; `chown unit:root` → „invalid user“.
- **Příčina:** `docker compose cp` vytvořil soubor vlastněný rootem; NetBox v kontejneru běží jako `netbox` (uid 999), ne `unit`.
- **Řešení:** soubor smazán, `chown -R netbox:root` na adresář scripts, nahrání přes UI.
- **Stav:** vyřešeno.

#### 35. `ipf_to_netbox.py`: chybějící konfigurace a 403
- **Příznak:** „Chybi konfigurace…“, poté `HTTP Error 403: Forbidden`.
- **Příčina:** neexportované proměnné a placeholder `SEM_VLOZ_TOKEN` místo API tokenu NetBoxu.
- **Řešení:** token vytvořen přes `manage.py shell`. Uživatel pak plugin považoval za zbytečný; vysvětleno, že plugin je importér a blokuje ho jen jedna tabulka s 403.
- **Stav:** vyřešeno.

#### 36. Typ zdroje vysvětlen obráceně, REST endpoint nepoužitelný
- **Příznak:** zmatek, proč zdroj nemá pole pro token a jak nahrát data offline.
- **Příčina:** asistent zprvu tvrdil, že `local` = soubor. Ve skutečnosti `local` = živé spojení s tokenem a `remote` = data dodaná zvenku. Endpoint `snapshot/<pk>/raw/` nenastavuje `type`.
- **Řešení:** vlastní `push_ipf_data.py`, který přes Django ORM zakládá `IPFabricData` se správným typem endpointu (11 endpointů, 1647 záznamů).
- **Stav:** vyřešeno.

#### 37. Ingesce: NULL v `serial` a navazující chyby
- **Příznak:** `null value in column "serial" of relation "dcim_device" violates not-null constraint`, `Device matching query does not exist`, `Field 'assigned_object_id' expected a number but got ''`, `invalid literal for int() with base 10: ''` (27 issues).
- **Příčina:** `strip_source_data()` ořezává data na povinné sloupce, takže zahodí `id`. Filtr `serial` při `sn` delším než 50 znaků padá na `id`, a výsledek je None. AWS objekty mají `sn` dlouhé 55–97 znaků. První pokus (null→'' v textových sloupcích) nepomohl.
- **Řešení:** šablona serialu: `sn`, je-li kratší než 50 znaků, jinak `hostname[:50]`.
- **Stav:** vyřešeno (později nahrazeno `nb_serial`, viz 60).

#### 38. Duplicitní IP v globální tabulce
- **Příznak:** `Duplicate IP address found in global table: …/25`.
- **Příčina:** demo síť má stejné adresy na více místech a NetBox vynucuje globální jedinečnost.
- **Řešení:** nová ConfigRevision s `ENFORCE_GLOBAL_UNIQUE=False`.
- **Stav:** obejito (ponecháno vypnuté i v dalších revizích).

#### 39. Chyby v asistentových ladicích skriptech
- **Příznak:** `NameError` na `d`, `render()` bez `connection_name`, pole `object_type` místo `changed_object_type` (jeden merge proto selhal); později `ConnectionDoesNotExist: The connection 'None' doesn't exist` při testovacím renderu.
- **Příčina:** chyby v ad hoc kódu.
- **Řešení:** opraveno v dalších verzích příkazů.
- **Stav:** vyřešeno.

#### 40. VRF se při každém syncu zdvojovaly (51 → 101 → 151)
- **Příznak:** počet VRF rostl s každou ingescí.
- **Příčina:** `normalizuj()` v pushi měnil `rd` None na '', v DB je NULL, takže coalesce nenašel shodu.
- **Řešení:** `rd` vyřazen z `TEXTOVE_SLOUPCE`, 100 duplicit smazáno; VRF pak stabilně 51.
- **Stav:** vyřešeno.

#### 41. Rozhraní a IP bez zařízení (18 issues)
- **Příznak:** ``Error getting context for `dcim.interface`. Error querying for relationship `device` …``.
- **Příčina:** po změně šablony serialu hledala relace rozhraní→zařízení a IP→rozhraní pořád podle `sn`, ale AWS zařízení měla serial z hostname.
- **Řešení:** relační mapa a mapa `assigned_object_id` (IPv4) dostaly fallback na hostname; `hostname` přidán do povinných sloupců.
- **Stav:** vyřešeno.

#### 42. Zaseknutý sync po ručním merge
- **Příznak:** sync ve stavu `ready_to_merge`, tlačítko Synchronize blokované.
- **Příčina:** merge přes `branch.merge()` v ORM obešel stavový automat pluginu.
- **Řešení:** stav nastaven na COMPLETED a zapnuto `auto_merge=True`; správná cesta je `ingestion.enqueue_merge_job()`. Issues klesly z 18 na 6.
- **Stav:** vyřešeno.

#### 43. IPv6 link-local adresy (6 issues)
- **Příznak:** `assigned_object_id expected a number but got ''` u adres fe80::.
- **Příčina:** tabulka adres používá zkrácený název rozhraní (`Gi0/1`), inventář plný (`GigabitEthernet0/1`).
- **Řešení:** přijato jako známé omezení; všech 389 IPv4 přiřazeno.
- **Stav:** otevřené.

#### 44. Prefixy: nenamapovaný endpoint `managed-networks`
- **Příznak:** v NetBoxu 0 prefixů; tabulka se do dumpu nestahovala.
- **Příčina:** název tabulky ve verzi 7.9 nebyl znám.
- **Řešení:** 09-17 obejito odvozením prefixů ze sloupce `net` (viz 69).
- **Stav:** obejito.

#### 45. Přepsaný `ipf_discover.py`
- **Příznak:** `ModuleNotFoundError: No module named 'ipfabric_netbox'` na hostiteli.
- **Příčina:** do souboru se vložil obsah push skriptu, který potřebuje Django.
- **Řešení:** obnovena kopie `-old`.
- **Stav:** vyřešeno.

#### 46. CSV nahrané jako skript
- **Příznak:** „Error loading script: invalid syntax (matice-demo.csv, line 2)“.
- **Příčina:** CSV bylo nahráno do Skriptů místo do pole formuláře.
- **Řešení:** spustit skript a CSV vložit do jeho pole.
- **Stav:** vyřešeno.

#### 47. Falešné nálezy matice kvůli zdrojové adrese
- **Příznak:** 14 řádků „CHYBÍ PRAVIDLO“ se ZONEFW na prvním hopu.
- **Příčina:** zdrojem byla management adresa samotného firewallu d2xfw01, takže provoz narážel na jeho vlastní zónovou politiku.
- **Řešení:** zdroj změněn na switch s2xsw01. Výsledek: OK 18 / PORUŠENÍ 9 / CHYBÍ 4 / NEDOSTUPNÉ 5.
- **Stav:** vyřešeno.

#### 48. Čtyři řádky NEDOSTUPNÉ z londýnské VLAN 333
- **Příznak:** všechny padají na prvním hopu.
- **Příčina:** pravděpodobně jediná společná příčina v routingu demo sítě, nevyšetřeno.
- **Řešení:** —
- **Stav:** otevřené.

#### 49. Zdroj v pluginu svítil červeně „Selhalo“
- **Příznak:** stav zdroje failed.
- **Příčina:** remote zdroj při synchronizaci volá tabulku snapshotů, kterou demo účet nesmí číst (403 / „Authentication not provided“).
- **Řešení:** stav ručně nastaven na COMPLETED, doplněn popis, smazány chybové joby. Doporučení: na Sources → Synchronizovat neklikat.
- **Stav:** obejito.

#### 50. Přejmenování syncu
- **Příznak:** `IPFabricSync.DoesNotExist`.
- **Příčina:** sync už byl přejmenován, hledalo se podle starého jména.
- **Řešení:** použito `.first()`.
- **Stav:** vyřešeno.

#### 51. Zbytkové větve (Postgres schémata) a nulová nástěnka
- **Příznak:** 6 větví (2 ready, 4 merged); po jejich smazání ukazovala nástěnka všude nuly.
- **Příčina:** větve vznikly ruční prací z doby ručního mergování. Nulová nástěnka se už nevyšetřovala; 09-08 changelog ukazoval další import, data byla na místě.
- **Řešení:** větve smazány (data v Main to neovlivní).
- **Stav:** větve vyřešeny; nuly na nástěnce nepotvrzeny ani nevysvětleny.

---

### 2026-09-08: skript kontroly matice v2

#### 52. Nalezení historie běhů v české lokalizaci
- **Příznak:** „Operace → Úlohy“ v menu není.
- **Příčina:** nepovedený překlad „Jobs“ jako „Pracovní místa“.
- **Řešení:** Operace → Pracovní místa, případně `/core/jobs/`; správný běh je job 31, job 30 má falešné nálezy.
- **Stav:** vyřešeno.

#### 53. `cat >` přepsal původní skript v1
- **Příznak:** na disku zmizela v1.
- **Příčina:** heredoc v2 zapisoval do stejného souboru.
- **Řešení:** v1 obnovena z kontejneru.
- **Stav:** vyřešeno.

#### 54. v2 nešlo přidat přes webové UI
- **Příznak:** nahrání v2 přes UI nefungovalo.
- **Příčina:** viz práva a nahrávání v bodě 34.
- **Řešení:** `docker compose cp` do obou kontejnerů, `chown netbox:root`, registrace přes `ScriptModule.objects.get_or_create(file_root='scripts', file_path='commatrix_v2.py')`.
- **Stav:** vyřešeno.

#### 55. Tlačítko Procházet ve Firefoxu přes RDP nic nedělá
- **Příznak:** dialog pro výběr souboru se neotevře.
- **Příčina:** Firefox ze snapu přes xdg-desktop-portal v xrdp session.
- **Řešení:** do v2 (a pak i v1) přidáno pole `cesta` (StringVar) s cestou k CSV uvnitř kontejneru; CSV zkopírováno do kontejnerů.
- **Stav:** obejito.

#### 56. v2 padala na TypeError
- **Příznak:** `TypeError("KontrolaKomunikacniMaticeV2._log() got an unexpected keyword argument 'level'")`.
- **Příčina:** pomocná metoda `_log` přepsala interní `Script._log`.
- **Řešení:** přejmenována na `zaloguj`.
- **Stav:** vyřešeno.

---

### 2026-09-15: druhý snapshot (365 zařízení)

#### 57. Push po přejmenování zdroje
- **Příznak:** `IPFabricSource.DoesNotExist`.
- **Příčina:** zdroj přejmenován na název serveru, skript hledal starý název.
- **Řešení:** proměnná `IPF_SOURCE_NAME` a nová výchozí hodnota ve skriptu.
- **Stav:** vyřešeno.

#### 58. Offline kopie snapshotu
- **Příznak:** požadavek mít snímek bez závislosti na demo serveru; archiv snapshotu IP Fabricu nejde importovat přímo.
- **Příčina:** archiv je nedokumentovaný formát určený pro nahrání zpět do IP Fabricu a logika převodu je v transform mapách pluginu.
- **Řešení:** push rozšířen o `IPF_DUMP_DIR` / `IPF_LOAD_DIR` (JSON po endpointech, 10 souborů, 4,6 MB). Jednou se patch při vkládání rozbil („co ted?“) a vložil se znovu. Kosmetika: v režimu načítání se vypisuje nesouvisející ID snapshotu z prostředí.
- **Stav:** vyřešeno.

#### 59. Ingesce vypršela (timeout)
- **Příznak:** `sync: timeout`, „Sync Job Timed Out … Check if RQ_DEFAULT_TIMEOUT needs increasing.“ Nic se nesloučilo.
- **Příčina:** výchozí RQ timeout 300 s nestačí na 7914 záznamů. Proměnná `RQ_DEFAULT_TIMEOUT` v `env/netbox.env` se nepropsala, protože ji konfigurace nečte.
- **Řešení:** `RQ_DEFAULT_TIMEOUT = 7200` v `configuration/extra.py`, restart netbox a worker, ověřeno v settings; smazány 2 nesloučené větve; ingesce 15 doběhla jako `completed`.
- **Stav:** vyřešeno.

#### 60. Azure VNet se jménem 151 znaků
- **Příznak:** `{'name': ['Ensure this value has at most 64 characters (it has 151).']}` a kaskáda „Skipping syncing of `dcim.interface` … due to previous error“.
- **Příčina:** dva VNety stejného jména v různých resource groups. Plugin kolizi řeší připojením ` - (sn)`, kde `sn` je celá Azure cesta, a tím přeteče limit 64 znaků. Tři hypotézy asistenta (délka hostname, kolize serialu, jiná mapa) byly mylné.
- **Řešení:** 09-16 push počítá vlastní `nb_serial` (sn, nebo `ipf-` + otisk) a `nb_name` (hostname, při kolizi nebo přetečení zkrácené jméno + otisk); mapy zařízení a rozhraní je používají.
- **Stav:** vyřešeno (365/365 zařízení).

#### 61. VLAN s ID 0
- **Příznak:** `{'vid': ['Ensure this value is greater than or equal to 1.']}`.
- **Příčina:** 3 řádky v datech s `vlanId` 0 (dva bez jména, jeden „default“), tedy artefakt dat.
- **Řešení:** filtr v `push_ipf_data.py` (jen `vlanId >= 1`); po pushi 440 VLAN místo 443.
- **Stav:** vyřešeno.

#### 62. Zastaralá zařízení ze starého snapshotu
- **Příznak:** po merge 449 zařízení místo 365.
- **Příčina:** 85 zařízení z ingesce 12 (mimo jiné celé MPLS jádro) v novém snímku není; plugin nic nemaže.
- **Řešení:** smazána zařízení s vlastním polem `ipfabric_ingestion` ≠ 15. Stará `matice-demo.csv` tím přestala platit, vznikla `matice-demo2.csv`.
- **Stav:** vyřešeno.

#### 63. Provozní dokument a prezentace: drobné vady
- **Příznak:** v textové dokumentaci slovo s cyrilským „о“; v prezentaci nezarovnané texty a mrtvé místo v kartách.
- **Příčina:** překlep; pptxgenjs ve výchozím stavu zarovnává text svisle na střed.
- **Řešení:** `sed` opravou; `valign: 'top'` v 65 rámečcích, vizuální QA bez závad. Nálezy z demo sítě v prezentaci označeny jako „ukázka metody“.
- **Stav:** vyřešeno.

---

### 2026-09-16 až 09-17: dorovnání s dashboardem IP Fabricu

#### 64. Změna serialů by zdvojila objekty
- **Příznak:** riziko duplicit po přechodu na `nb_serial`.
- **Příčina:** coalesce podle serialu by stará zařízení nenašel.
- **Řešení:** importované objekty smazány, push offline a nová ingesce. Výsledek 365 zařízení / 4618 rozhraní / 21 lokalit, přesná shoda s dashboardem IP Fabricu.
- **Stav:** vyřešeno.

#### 65. Ošklivé názvy typů zařízení
- **Příznak:** `azure -  - vnet`, `gcp -  -`.
- **Příčina:** šablona natvrdo spojovala vendor, family a platform i při prázdném poli.
- **Řešení:** `[vendor, family, platform] | select | join(' ')` (slug analogicky).
- **Stav:** vyřešeno.

#### 66. Aktivní rozhraní 2738 vs. 2608 v dashboardu
- **Příznak:** rozdíl 130.
- **Příčina:** IP Fabric počítá aktivní = L1 i L2 up, my mapujeme `enabled` jen z L1.
- **Řešení:** vysvětleno a ponecháno (pole `enabled` má jiný význam).
- **Stav:** vyřešeno (vysvětleno).

#### 67. 2005 issues v ingesci 17, MAC a inventář
- **Příznak:** 94 chyb u `dcim.macaddress` (v ingesci 18 dokonce 4618), 178 položek inventáře `{'name': ['This field cannot be blank']}`.
- **Příčina:** mapa MAC adres hledala zařízení pořád podle starého `sn`, při přepisu na `nb_serial` byla zapomenuta; ingesce 18 navíc běžela dřív, než se oprava uložila. 196 z 336 položek part-numbers nemá `name` ani `dscr`.
- **Řešení:** mapa MAC přepnuta na `nb_serial`; jméno položky inventáře se skládá z `pid` a `sn`. Ingesce 19: MAC 4618, inventář 326.
- **Stav:** vyřešeno (10 položek inventáře zbývá).

#### 68. Nula IP adres a „Error removing primary IP from other device.“
- **Příznak:** 1705 chyb, v NetBoxu 0 IP adres; výjimka `TypeError`.
- **Příčina:** plugin při zakládání IP volá vlastní filtr `serial()` nad daty řádku (`len(data.get("sn"))`). Po přepnutí mapy IP na `nb_serial` vypadl `sn` z povinných sloupců, ořezání dat ho zahodilo a celý zápis adresy se zrušil. Hypotéza asistenta o `ENFORCE_GLOBAL_UNIQUE` byla mylná.
- **Řešení:** šablona `{% set SN = object.nb_serial or object.sn %}`, aby zůstaly povinné oba sloupce. Po další ingesci 1659 IP adres.
- **Stav:** vyřešeno.

#### 69. Primární IP adresy zařízení
- **Příznak:** 0 z 365 zařízení s primární IPv4; `primarni_ip.py` podle `loginIp` zprvu nenastavil nic (279 adres není na žádném rozhraní, 86 bez `loginIp`).
- **Příčina:** management adresy často nejsou v tabulce spravovaných adres; navíc chyba z bodu 68.
- **Řešení:** po opravě 68 skript nastavil 264; doplněno pravidlo „jediná IPv4 na rozhraních“ → 289/365. Zbylých 76 vědomě prázdných (bez rozhraní, bez adres nebo s více adresami bez určení správcovské).
- **Stav:** vyřešeno (částečně, záměrně).

#### 70. Deset zařízení bez rozhraní
- **Příznak:** 10 zařízení v NetBoxu bez rozhraní.
- **Příčina:** AWS internet gateways, NSX T0 a load balancer rozhraní v datech nemají. Podezření na `stackMemberSn` se nepotvrdilo.
- **Řešení:** žádné, je to správné chování.
- **Stav:** vyřešeno (není chyba).

#### 71. Falešné zdroje v matici 2
- **Příznak:** běh matice 2: OK 20, PORUŠENÍ 8, CHYBÍ 2, NEDOSTUPNÉ 10; dva řádky vyhodnocené na prvním hopu.
- **Příčina:** zdrojová adresa patřila samotnému síťovému prvku (stejný jev jako v bodě 47).
- **Řešení:** dva řádky opraveny přes `sed` na jiné zdroje, CSV znovu zkopírováno do kontejnerů.
- **Stav:** vyřešeno.

#### 72. Mapa sítě a spoje v NetBoxu
- **Příznak:** šéf chtěl screenshot mapy sítě z NetBoxu.
- **Příčina:** komunitní NetBox topologii nekreslí a sousedství/linky se neimportují.
- **Řešení:** mapa, routing a FW pravidla se screenují z IP Fabricu.
- **Stav:** obejito.

#### 73. Nástěnka s nulami a reklamním pruhem
- **Příznak:** prázdné sekce (Racks, Circuits…), banner „New Release Available“, 0 prefixů.
- **Příčina:** organizační evidence se v pilotu neplní; prefixy chyběly (bod 44).
- **Řešení:** nástěnka sestavena z CLI (model `Dashboard`): ObjectCountsWidget s 8 modely, později ObjectListWidget s joby a NoteWidget s odkazy na skripty. Název widgetu byl nejdřív bez diakritiky, pak opraven. Nevyplňovat fiktivní data.
- **Stav:** vyřešeno.

#### 74. Prefixy z IPv6 hostitelských adres
- **Příznak:** `invalid cidr value: "beef:37:1::5/64"` – `DETAIL: Value has bits set to right of mask.` (70 chyb). Uživatel pak spustil starou verzi skriptu ze scrollbacku.
- **Příčina:** sloupec `net` obsahuje u části IPv6 adresu hostitele s maskou, ne síť.
- **Řešení:** `ipaddress.ip_network(hodnota, strict=False)`; kontrola verze přes `grep 'ipaddress'` přímo v příkazu. Výsledek 1142 prefixů, 0 chyb.
- **Stav:** vyřešeno.

#### 75. Opakované zadávání cesty a snapshotu ve skriptu
- **Příznak:** při každém spuštění kontroly matice se musela psát cesta k CSV a ID snapshotu.
- **Příčina:** pole formuláře neměla výchozí hodnoty.
- **Řešení:** skript ukládá poslední hodnoty do `media/matice_posledni.json` (sdílené webem i workerem) a nabízí je jako výchozí.
- **Stav:** vyřešeno.

#### 76. FW průzkum: přihlášení selhalo kvůli `set -a; . ipf.env`
- **Příznak:** „Prihlaseni k IP Fabric selhalo.“; vložený heredoc se v terminálu navíc pomíchal.
- **Příčina:** stejná expanze `$*` v hesle jako v bodě 28, tentokrát při sourcování env souboru shellem.
- **Řešení:** funkce `nacti_env()` čte `/opt/commatrix/ipf.env` přímo v Pythonu, bez shellu.
- **Stav:** vyřešeno.

#### 77. NetBox nemá model pro FW pravidla; většina pravidel neověřitelná
- **Příznak:** pravidla nejde do NetBoxu „naimportovat“. Z 1732 pravidel (`security/acl` 1482, `security/zone-firewall/policies` 250) se do matice převedlo jen 6.
- **Příčina:** NetBox pravidla neeviduje. 1474 pravidel má zdroj 0.0.0.0/0 (často AWS security groups), takže se nedají simulovat. Jeden řádek mířil sám na sebe.
- **Řešení:** `fw_na_matici.py` vytváří kandidátní matici; degenerovaný řádek odstraněn. `fw_prehled.py` počítá statistiku kvality pravidel (177 prvků, 204 širokých povolení) a existuje i jako NetBox Script s odkazem na nástěnce.
- **Stav:** obejito.

---

### 2026-09-18: retence historie

#### 78. Changelog a joby se mažou po 90 dnech
- **Příznak:** stránka konfigurace nejde editovat; retence 90 dnů je pro audit krátká.
- **Příčina:** konfigurace se v NetBoxu mění založením nové ConfigRevision, ne úpravou té zobrazené.
- **Řešení:** nová ConfigRevision přes shell (převzetí předchozích dat včetně `ENFORCE_GLOBAL_UNIQUE`), na přání uživatele `CHANGELOG_RETENTION=0` a `JOB_RETENTION=0` (nemazat). Výchozí stav: 39 856 změn, DB 123 MB.
- **Stav:** vyřešeno; velikost DB je potřeba průběžně hlídat.

---

**Celkem: 78 problémů.** Otevřené zůstávají: 12 (varování v konfiguraci), 43 (IPv6 link-local), 48 (NEDOSTUPNÉ z VLAN 333) a 51 (nevysvětlená nulová nástěnka). Ostatní jsou vyřešené nebo obejité.
