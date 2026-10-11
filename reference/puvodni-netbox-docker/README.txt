================================================================================
NETBOX + IP FABRIC + BATFISH
Provozni kucharka pro stroj blue-ThinkCentre-M710s
Ucel: evidence a validace firewallovych pravidel, kontrola komunikacni matice
Aktualizovano: 2026-09-06
================================================================================

Hesla NEJSOU v tomto souboru. Jsou v password.txt.


--------------------------------------------------------------------------------
OBSAH
--------------------------------------------------------------------------------
 1. Prehled a pristupy
 2. Struktura adresaru
 3. Start, stop, restart
 4. Logy
 5. Zmena verze IP Fabric pluginu
 6. Zmena verze NetBoxu
 7. Prestavba image
 8. Hesla a jejich propojeni
 9. Zaloha a obnova databaze
10. IP Fabric API - pristup a omezeni
11. Kontrola komunikacni matice - skript na hostiteli
12. Kontrola komunikacni matice - NetBox Script
13. Reseni problemu
14. Uklid a misto na disku
15. Vzdalena plocha (RDP)
16. Historie zasahu na stroji
17. Rychly tahak


--------------------------------------------------------------------------------
1. PREHLED A PRISTUPY
--------------------------------------------------------------------------------

Stroj:            blue-ThinkCentre-M710s
SSH:              ssh user@<WIREGUARD_IP>        (WireGuard)
                  ssh user@<LAN_IP>   (LAN, po zapojeni kabelu)
Tailscale:        <TAILSCALE_IP>
RDP:              port 3389 (xrdp)
NetBox web:       http://<WIREGUARD_IP>:8000  nebo  http://<LAN_IP>:8000
Batfish Jupyter:  port 8888
Batfish API:      port 9997 (work 9996)
IP Fabric demo:   https://guided-demo.eu.ipfabric.io  (verze 7.9.4)

Verze, na kterych to jede:

  NetBox                        4.6.10
  netbox-docker                 5.0.2  (git tag, detached HEAD)
  image (zaklad)                netboxcommunity/netbox:v4.6.10-5.0.2
  image (sestaveny s pluginy)   netbox:v4.6.10-5.0.2-plugins
  ipfabric_netbox               6.1.0  (extra: ipfabric_7_9)
  ipfabric SDK                  7.9.1
  netboxlabs-netbox-branching   1.1.3  (omezeno na <1.2)
  PostgreSQL                    18-alpine
  Redis                         valkey 9.1-alpine

POZOR NA VERZE:
NetBox 4.7 zatim NEPOUZIVAT. netbox-branching 1.2.0 sice 4.7 vyzaduje, ale
rozbiji GraphQL schema (chyba: GraphQL type for model field
'core.Job.execution_time' has not been implemented). Proto jedeme na 4.6.10
s branchingem 1.1.3, kde vse funguje.

Matice kompatibility:
  https://github.com/netboxlabs/netbox-branching/blob/main/COMPATIBILITY.md
  https://pypi.org/project/ipfabric_netbox/


--------------------------------------------------------------------------------
2. STRUKTURA ADRESARU
--------------------------------------------------------------------------------

/opt/netbox-docker/           klon netbox-community/netbox-docker (tag 5.0.2)

  Ze repozitare, needitovat:
    docker-compose.yml            definice sluzeb

  Vytvorene rucne (git je nezna):
    plugin_requirements.txt       seznam pluginu k instalaci
    Dockerfile-Plugins            recept na sestaveni image s pluginy
    docker-compose.override.yml   vlastni image, porty, batfish, restart policy
    .env                          VERSION=v4.6.10-5.0.2
    README.txt                    tento soubor
    password.txt                  hesla (chmod 600)

  Editovane (git je hlasi jako zmenene):
    configuration/plugins.py      seznam pluginu + DB router pro branching
    env/netbox.env                hesla, SECRET_KEY, IPF_* promenne
    env/postgres.env              heslo do databaze
    env/redis.env                 heslo pro Redis
    env/redis-cache.env           heslo pro Redis cache

/opt/commatrix/               kontrola komunikacni matice
    commatrix_check.py            skript pro hostitele
    commatrix_script.py           varianta pro NetBox Script
    matrix-vzor.csv               ukazkova matice
    ipf.env                       pristupove udaje k IP Fabric (chmod 600)
    report.csv                    posledni vysledek

/root/fw_stack-archiv-2026-09-05.tar.gz
    archiv puvodniho rucne psaneho stacku vcetne dumpu prazdne databaze


--------------------------------------------------------------------------------
3. START, STOP, RESTART
--------------------------------------------------------------------------------

Vzdy nejdriv:
  cd /opt/netbox-docker

Nastartovat vse:
  docker compose up -d

Zastavit vse (data zustavaji):
  docker compose down

Zastavit VCETNE smazani dat -- NEPOUZIVAT:
  docker compose down -v

Restart jedne sluzby:
  docker compose restart netbox

Stav:
  docker compose ps

PO RESTARTU STROJE se stack nastartuje sam. Restart policy unless-stopped je
nastavena v docker-compose.override.yml pro vsech sest sluzeb; upstream
docker-compose.yml zadnou restart policy nema. Vyjimka: po rucnim
'docker compose down' nebo 'stop' stack po rebootu nenaskoci -- to je zamer.

Overeni restart policy:
  docker inspect -f '{{.Name}} -> {{.HostConfig.RestartPolicy.Name}}' $(docker compose ps -aq)


--------------------------------------------------------------------------------
4. LOGY
--------------------------------------------------------------------------------

Vse dohromady:
  docker compose logs --tail=100

Jedna sluzba:
  docker compose logs --tail=60 netbox
  docker compose logs --tail=60 netbox-worker
  docker compose logs --tail=60 postgres
  docker compose logs --tail=60 batfish

Zive (Ctrl+C ukonci vypis, ne kontejner):
  docker compose logs -f netbox

Hledani:
  docker compose logs netbox | grep -iE "error|traceback|exception"

Logy z buildu:
  /var/log/netbox-build*.log

Systemove:
  journalctl -u docker --no-pager | tail -50


--------------------------------------------------------------------------------
5. ZMENA VERZE IP FABRIC PLUGINU
--------------------------------------------------------------------------------

Plugin se instaluje s "extra" balickem, ktery pripne spravnou verzi IP Fabric
SDK. Musi odpovidat verzi serveru IP Fabric.

Dostupne extras: ipfabric_7_0, ipfabric_7_2, ipfabric_7_3, ipfabric_7_5,
                 ipfabric_7_8, ipfabric_7_9, ipfabric_7_10, ipfabric_7_11

Postup (priklad prechod na 7.10):

  cd /opt/netbox-docker

  cat > plugin_requirements.txt <<'EOF'
  ipfabric_netbox[ipfabric_7_10]
  netboxlabs-netbox-branching<1.2
  EOF

Nejdriv nechat spocitat nasucho (vteriny, nic neinstaluje):

  docker run --rm netboxcommunity/netbox:v4.6.10-5.0.2 sh -c \
    "/usr/local/bin/uv pip install --dry-run 'ipfabric_netbox[ipfabric_7_10]' 'netboxlabs-netbox-branching<1.2' 2>&1 | tail -30"

Pak prestavet:

  docker compose build
  docker compose up -d

Overeni:

  docker compose exec netbox /opt/netbox/netbox/manage.py showmigrations ipfabric_netbox | tail -5

Databaze zustava, meni se jen kod pluginu.


--------------------------------------------------------------------------------
6. ZMENA VERZE NETBOXU
--------------------------------------------------------------------------------

Dostupne tagy:

  curl -s "https://hub.docker.com/v2/repositories/netboxcommunity/netbox/tags?page_size=100&name=4.7" \
    | python3 -c "import sys,json;[print(t['name']) for t in json.load(sys.stdin)['results']]" | sort -V | tail -20

Verze se meni na TRECH mistech, musi byt vsude stejna:

  1) Dockerfile-Plugins, radek FROM
  2) docker-compose.override.yml, nazev image (dvakrat)
  3) .env, radek VERSION

  cd /opt/netbox-docker
  sed -i "s|^FROM netboxcommunity/netbox:.*|FROM netboxcommunity/netbox:NOVY_TAG|" Dockerfile-Plugins
  sed -i "s|netbox:v4.6.10-5.0.2-plugins|netbox:NOVY_TAG-plugins|g" docker-compose.override.yml
  echo "VERSION=NOVY_TAG" > .env
  grep -rn "4\.6\.10" Dockerfile-Plugins docker-compose.override.yml .env

Posledni prikaz musi vratit prazdno.

Pri prechodu na NetBox 4.7+ uvolnit i omezeni branchingu v plugin_requirements.txt.

Druhe cislo v tagu je verze netbox-docker. Pokud se zmeni, prepnout i repozitar:

  git checkout 5.1.0

Checkout necha netknute rucne vytvorene soubory a editovanou konfiguraci.

PRED KAZDYM UPGRADEM UDELAT ZALOHU DATABAZE (kapitola 9).
Migrace jsou jednosmerne.


--------------------------------------------------------------------------------
7. PRESTAVBA IMAGE
--------------------------------------------------------------------------------

Normalni prestavba (pouzije cache):
  cd /opt/netbox-docker
  docker compose build
  docker compose up -d

Prestavba od nuly:
  docker compose build --no-cache

Na pomale lince na pozadi, aby to prezilo zavreni terminalu:
  nohup sh -c 'until docker compose build; do sleep 60; done; docker compose up -d && echo HOTOVO' \
    > /var/log/netbox-build.log 2>&1 &

Kontrola:
  tail -f /var/log/netbox-build.log
  grep -E "HOTOVO|ERROR|error:" /var/log/netbox-build.log | tail -10

Obsah Dockerfile-Plugins:

  FROM netboxcommunity/netbox:v4.6.10-5.0.2
  COPY ./plugin_requirements.txt /opt/netbox/
  RUN UV_HTTP_TIMEOUT=300 UV_CONCURRENT_DOWNLOADS=1 /usr/local/bin/uv pip install -r /opt/netbox/plugin_requirements.txt
  COPY configuration/configuration.py /etc/netbox/config/configuration.py
  COPY configuration/plugins.py /etc/netbox/config/plugins.py
  RUN DEBUG="true" SECRET_KEY="dummy..." /opt/netbox/venv/bin/python /opt/netbox/netbox/manage.py collectstatic --no-input

UV_HTTP_TIMEOUT a UV_CONCURRENT_DOWNLOADS jsou tam kvuli pomalym linkam.
Bez nich build pada na "operation timed out".


--------------------------------------------------------------------------------
8. HESLA A JEJICH PROPOJENI
--------------------------------------------------------------------------------

Ulozena jsou v password.txt. Tady je mapa, co s cim musi souhlasit.

  POSTGRES_PASSWORD v env/postgres.env
    = DB_PASSWORD v env/netbox.env
    = PASSWORD v configuration/plugins.py     <-- na tohle se snadno zapomene

  REDIS_PASSWORD v env/redis.env
    = REDIS_PASSWORD v env/netbox.env

  REDIS_PASSWORD v env/redis-cache.env
    = REDIS_CACHE_PASSWORD v env/netbox.env

  SECRET_KEY v env/netbox.env    (min. 50 znaku, zmena odhlasi vsechny relace)

  IPF_URL, IPF_USER, IPF_PASS, IPF_SNAPSHOT v env/netbox.env
    -> pouziva je NetBox Script pro kontrolu matice

Kontrola shody bez vypisovani hesel:

  cd /opt/netbox-docker
  grep -E '^POSTGRES_PASSWORD=' env/postgres.env | cut -d= -f2- | md5sum
  grep -E '^DB_PASSWORD=' env/netbox.env | cut -d= -f2- | md5sum
  grep -E '^REDIS_PASSWORD=' env/redis.env | cut -d= -f2- | md5sum
  grep -E '^REDIS_PASSWORD=' env/netbox.env | cut -d= -f2- | md5sum
  grep -E '^REDIS_PASSWORD=' env/redis-cache.env | cut -d= -f2- | md5sum
  grep -E '^REDIS_CACHE_PASSWORD=' env/netbox.env | cut -d= -f2- | md5sum

Odpovidajici si dvojice musi mit stejny otisk.

Generovani:
  openssl rand -hex 24
  openssl rand -hex 32                (pro SECRET_KEY)

Zmena hesla v bezici databazi (zmena env souboru nestaci):
  docker compose exec postgres psql -U netbox -d netbox
  \password netbox
  \q
Potom stejne heslo do env/postgres.env, env/netbox.env i plugins.py
a docker compose up -d.

Uzivatel NetBoxu:
  vytvoreni:    docker compose exec netbox /opt/netbox/netbox/manage.py createsuperuser
  zmena hesla:  docker compose exec netbox /opt/netbox/netbox/manage.py changepassword admin

Pozadavky: min. 12 znaku, cislice, velke i male pismeno, specialni znak.
Generator:
  python3 -c "import secrets,string; a=string.ascii_letters+string.digits+'!@#%^*_-'; print(''.join(secrets.choice(a) for _ in range(20)))"

POZOR NA BASH: hesla obsahujici $ nebo * se ve dvojitych uvozovkach expanduji.
Pouzivej jednoduche uvozovky nebo heredoc s uvozenym oddelovacem (<<'EOF').


--------------------------------------------------------------------------------
9. ZALOHA A OBNOVA DATABAZE
--------------------------------------------------------------------------------

Zaloha:
  cd /opt/netbox-docker
  docker compose exec -T postgres pg_dump -U netbox netbox | gzip > /root/netbox-$(date +%F).sql.gz
  ls -lh /root/netbox-*.sql.gz

Obnova (prepise stavajici data):
  gunzip -c /root/netbox-2026-09-06.sql.gz | docker compose exec -T postgres psql -U netbox -d netbox

Zalohu delat vzdy pred upgradem NetBoxu nebo pluginu.


--------------------------------------------------------------------------------
10. IP FABRIC API - PRISTUP A OMEZENI
--------------------------------------------------------------------------------

Instance:  https://guided-demo.eu.ipfabric.io  (7.9.4)
Ucet:      role ID 15, scope: read, settings, custom, write, ipf-gui

AUTENTIZACE JE COOKIE-BASED.
/api/auth/login v tele NEVRACI accessToken, jen nastavi cookies. Kazdy dalsi
pozadavek musi ty cookies nest. Bearer token se nepouziva.

  POST /api/auth/login  {"username": ..., "password": ...}
  -> Set-Cookie (accessToken, refreshToken)
  -> dalsi dotazy s temito cookies

CO UCET SMI:
  /api/version                        200
  /api/snapshots                      200
  /api/users/me                       200
  /api/tables/inventory/devices       200 (POST s columns)
  /api/tables/inventory/interfaces    200 (POST s columns)
  /api/tables/security/acl            200 (POST s columns)
  /api/tables/security/zone-firewall/policies    200
  /api/tables/security/zone-firewall/interfaces  200
  /api/graphs                         200 (path lookup)

CO UCET NESMI:
  /api/tables/management/snapshots    403 API_INSUFFICIENT_RIGHTS
  /api/roles/15                       403
  POST /prepared-requests             neni povoleno

DUSLEDEK: oficialni NetBox plugin ipfabric_netbox NEFUNGUJE, protoze SDK si
pri startu klienta cte prave tabulku management/snapshots. Reseni je pozadat
IP Fabric o roli s pravem cteni teto tabulky. Do te doby se data tahaji
primo pres API vlastnim skriptem (kapitola 11 a 12).

DALSI OMEZENI DEMA: tabulka management/configuration je prazdna (count 0),
demo nema zapnutou spravu konfiguraci. Batfish tedy nema z ceho stavet model.
Batfish pouzit az na firemni instanci, kde konfigurace k dispozici budou.

ZJISTENI SLOUPCU TABULKY: poslat neexistujici sloupec, API vrati vycet
povolenych hodnot.

  {'columns': ['NEEXISTUJE'], 'snapshot': '$last',
   'format': {'dataType': 'json'}, 'pagination': {'limit': 1, 'start': 0}}

SLOUPCE security/acl:
  hostname, siteName, sn, policyName, ruleNumber, ruleName, ruleId, action,
  actionOriginal, description, ipSrc, ipDst, ipProtocol, srcPorts, dstPorts,
  tcpSrc, tcpDst, udpSrc, udpDst, icmpType, icmpCode, interfaceIn,
  interfaceOut, interfaceInZone, interfaceOutZone, interfaceVrf, active, ...

SLOUPCE management/configuration:
  id, hash, relatedHash, hostname, lastChangeAt, lastCheckAt, reason, sn, status

SNAPSHOTY V DEMU:
  8dc4dd8b-afc0-46ae-995c-38800e1df781  NetLab - Post-Change
  97ad7c58-341a-4e93-9612-8dd259d41672  NetLab - Pre-Change
  22443e66-2430-4a55-b953-d7601b3f5148  Network Audit Evidence Q2/2026
  48ea238d-a49b-43c7-a97f-855aebf0e4d2  S02 - Day 2 - Azure

PATH LOOKUP (simulace cesty):
  POST /api/graphs
  {"snapshot": "<id>", "parameters": { ... }}

Telo parameters se sklada takto (TCP):
  pathLookupType: unicast, networkMode: false, type: pathLookup,
  groupBy: siteName, startingPoint: "10.0.0.30/32", destinationPoint: "10.0.0.40/32",
  protocol: tcp, ttl: 128, fragmentOffset: 0, securedPath: true,
  enableRegions: false, srcRegions: ".*", dstRegions: ".*",
  l4Options: {srcPorts: "1024-65535", dstPorts: "443", flags: []},
  otherOptions: {applications: ".*", tracked: false, category: "", url: ""},
  firstHopAlgorithm: {type: "automatic"}

UDP: l4Options bez pole flags.
ICMP: l4Options = {type: 0, code: 0}.

ODPOVED:
  pathlookup.passingTraffic       "all" = projde, "none" = neprojde
  pathlookup.decisions            pocet zarizeni na ceste
  pathlookup.eventsSummary.topics ACL, ZONEFW, FORWARDING, NAT44, PBR
                                  nenulove = tato vrstva do provozu zasahla


--------------------------------------------------------------------------------
11. KONTROLA KOMUNIKACNI MATICE - SKRIPT NA HOSTITELI
--------------------------------------------------------------------------------

Umisteni: /opt/commatrix/commatrix_check.py
Zavislosti: zadne, jen standardni knihovna Pythonu.

Konfigurace /opt/commatrix/ipf.env (chmod 600):
  IPF_URL=https://guided-demo.eu.ipfabric.io
  IPF_USER=...
  IPF_PASS=...
  IPF_SNAPSHOT=8dc4dd8b-afc0-46ae-995c-38800e1df781

Format matice (CSV, hlavicka povinna):
  name,src,dst,proto,port,expected
  Web z DMZ,10.0.0.30,10.0.0.40,tcp,443,allow
  Telnet odkudkoli,10.0.0.30,10.0.0.40,tcp,23,deny

Spusteni:
  cd /opt/commatrix && python3 commatrix_check.py matrix-vzor.csv
  python3 commatrix_check.py matrix.csv --snapshot <id> --out report.csv

Navratovy kod 1 pri nalezu porusení nebo chybejiciho pravidla, jinak 0.
Vhodne pro CI nebo cron.

VERDIKTY:
  OK                     skutecnost odpovida matici
  PORUSENI MATICE        zakazana komunikace prochazi -> bezpecnostni nalez
  CHYBI PRAVIDLO         povolena komunikace zahozena ACL nebo zonovym FW
  NEDOSTUPNE (routing)   neprojde, ale ne kvuli firewallu -> uloha pro sitare
  CASTECNE               cast cest projde, cast ne -> prohlednout rucne
  CHYBA DOTAZU           API vratilo chybu, detail je ve sloupci error

Sloupec blocked_by rika, ktera vrstva rozhodla: ACL, ZONEFW, FORWARDING,
NAT44 nebo PBR. To rozliseni je duvod, proc pouzivat simulaci misto cteni
pravidel ocima.


--------------------------------------------------------------------------------
12. KONTROLA KOMUNIKACNI MATICE - NETBOX SCRIPT
--------------------------------------------------------------------------------

Stejna logika, ale bezi uvnitr NetBoxu. Spousti se z webu, ma historii behu,
da se naplanovat a vysledek je videt v UI.

NAHRANI SKRIPTU:
  Prizpusobeni -> Skripty -> Add -> nahrat commatrix_script.py

NENAHRAVAT pres 'docker compose cp'. Soubor by patril rootovi a NetBox
(uid 999, uzivatel netbox) by ho nemohl prepsat -- konci to chybou
PermissionError. Kdyz uz se to stane:

  docker compose exec -u root netbox rm -f /opt/netbox/netbox/scripts/<soubor>.py
  docker compose exec -u root netbox chown -R netbox:root /opt/netbox/netbox/scripts

PRIHLASOVACI UDAJE se ctou z promennych prostredi kontejneru, doplnenych
do env/netbox.env: IPF_URL, IPF_USER, IPF_PASS, IPF_SNAPSHOT.
Musi byt videt i ve WORKERU, protoze skript bezi tam:

  docker compose exec netbox-worker printenv IPF_URL IPF_USER IPF_SNAPSHOT

SPUSTENI:
  Prizpusobeni -> Skripty -> Kontrola komunikacni matice
  do pole "matice" nahrat CSV, pole "snapshot" prazdne = z promenne prostredi

VYSTUP:
  kazdy radek matice jako jeden log (zelene OK, cervene nalez, oranzove
  varovani), na konci shrnuti a cely report v CSV jako navratova hodnota.

PLANOVANI:
  Skript ma scheduling_enabled = True, takze si ho v NetBoxu muzes nastavit
  na pravidelny beh a mit prubeznou kontrolu s historii.


--------------------------------------------------------------------------------
13. RESENI PROBLEMU
--------------------------------------------------------------------------------

Kontejner netbox je "unhealthy", ostatni bezi
  docker compose logs --tail=60 netbox
  Nejcastejsi priciny:
    redis.exceptions.AuthenticationError  -> nesedi Redis hesla, kapitola 8
    password authentication failed        -> nesedi DB hesla, kapitola 8
  Pri prvnim startu po prestavbe bezi migrace, kontejner muze byt minutu
  "starting". Neni to chyba.

Sluzby po restartu stroje nenaskocily
  Byly zastavene rucne (down/stop). Restart policy takove kontejnery
  nestartuje. Staci docker compose up -d.

Kontejner ve stavu "Created" a nestartuje
  Byl vytvoren, ale nikdy nespusten (preruseny docker compose up).
  docker compose up -d

Build pada na "operation timed out" u uv pip install
  Pomala linka. UV_HTTP_TIMEOUT je uz nastaveny na 300.
  Pustit build ve smycce (kapitola 7).

Build pada na collectstatic s GraphQL chybou
  Nekompatibilni verze pluginu s verzi NetBoxu. Viz kapitola 1.

Build pada s "Plugin netbox_branching requires NetBox minimum version X"
  Branching je novejsi nez NetBox. Omezit v plugin_requirements.txt:
  netboxlabs-netbox-branching<1.2

Tlacitko Synchronizovat u IP Fabric zdroje je zasedle
  ready_for_sync je False. U zdroje to znamena probihajici sync, u Sync
  objektu chybejici data snapshotu. Diagnostika:
    docker compose exec netbox /opt/netbox/netbox/manage.py shell -c "
    from ipfabric_netbox.models import IPFabricSource, IPFabricSync
    for s in IPFabricSource.objects.all(): print(s.name, s.status, s.ready_for_sync)
    for y in IPFabricSync.objects.all(): print(y.name, y.status, y.ready_for_sync)
    "

IP Fabric sync konci "Authentication not provided"
  Zdroj nema ulozeny token. Formular v UI pole pro token nema, uklada se do
  JSON pole parameters. IPFClient zna JEN klic 'auth' (ne username/password):
    docker compose exec -T netbox /opt/netbox/netbox/manage.py shell <<'PY'
    from ipfabric_netbox.models import IPFabricSource
    src = IPFabricSource.objects.get(name='demo')
    src.parameters = {'auth': 'TOKEN', 'timeout': 30}
    src.save()
    PY
  Heslo se do parameters uklada v citelne podobe. Na produkci pouzit token
  s pravy jen pro cteni.

Docker nema DNS ("dial tcp: lookup ... server misbehaving")
  Hostitel pouziva systemd-resolved stub 127.0.0.53, ktery kontejner pouzit
  nemuze, a Docker podstrci vlastni resolvery. Reseno natvrdo v
  /etc/docker/daemon.json:
    {"dns": ["8.8.8.8", "1.1.1.1"], "max-concurrent-downloads": 1,
     "max-download-attempts": 10}
  Po zmene: systemctl restart docker
  Test: docker run --rm busybox nslookup pypi.org

Pomaly internet
  4.-5. 9. 2026 byla pricinou USB Wi-Fi TP-Link TL-WN722N v2 (cip RTL8188EUS,
  ovladac rtl8xxxu) na LTE hotspotu TP-Link M7000. Signal i rychlost spojeni
  vypadaly dobre (-31 dBm, 0 retries, 48 Mbit/s), propustnost ale klesla na
  250 kbit/s a fronty pretekaly (ping: sendmsg: No buffer space available,
  odezva az 48 sekund). Po zapojeni ethernetoveho kabelu 29/26 Mbps.
  ZAVER: pouzivat kabel. Wi-Fi adapter je nahradni reseni, ne cilovy stav.

  Diagnostika, kdyby se to opakovalo:
    ping -c 10 <brana>                       odezva na router
    traceroute -n -m 6 1.1.1.1               druhy hop 10.x = mobilni sit
    iw dev <if> link                         signal a rychlost spojeni
    iw dev <if> station dump | grep retries  opakovane prenosy
    curl -o /dev/null -w "%{speed_download} B/s\n" "https://speed.cloudflare.com/__down?bytes=25000000"
  Zmirneni bufferbloatu (netrvale):
    tc qdisc replace dev <if> root fq_codel


--------------------------------------------------------------------------------
14. UKLID A MISTO NA DISKU
--------------------------------------------------------------------------------

Prehled:
  docker system df
  df -h /
  docker images
  docker volume ls

Bezpecne:
  docker builder prune -f

NIKDY nemazat bez rozmyslu:
  netboxcommunity/netbox:v4.6.10-5.0.2    zaklad pro prestavby
  volumes netbox-docker_*                 data

POZOR: na tomto stroji jsou i CIZI DATA. Volumes misp_*, misp2_* a
misp-docker_mysql_data (dohromady cca 1,8 GB) patri majiteli stroje.
NEMAZAT bez domluvy.


--------------------------------------------------------------------------------
15. VZDALENA PLOCHA (RDP)
--------------------------------------------------------------------------------

Nainstalovan xrdp, port 3389. Z macOS pouzit aplikaci Windows App
(driv Microsoft Remote Desktop) -- Sdileni obrazovky v macOS mluvi VNC,
kdezto Ubuntu 24.04 pouziva RDP.

  systemctl status xrdp --no-pager
  ss -lntp | grep 3389

Pripojeni na <WIREGUARD_IP> (WireGuard) nebo <LAN_IP> (LAN).
Pres Tailscale (<TAILSCALE_IP>) byva rychlejsi, pokud je spojeni primé:
  tailscale status        hledat "direct" versus "relay"

Kdyz je RDP pomale:
  - pripojit se pres LAN nebo Tailscale, ne pres WireGuard s prubehem pres VPS
  - v klientovi vypnout Retina/vysoke DPI a nastavit pevne rozliseni
  - snizit barevnou hloubku v /etc/xrdp/xrdp.ini: max_bpp=16

Cerna obrazovka po prihlaseni (GNOME versus xrdp):
  su - <uzivatel> -c 'echo "gnome-session" > ~/.xsession'
  systemctl restart xrdp
Kdyz nepomuze, lehci prostredi jen pro RDP:
  apt install xfce4 xfce4-goodies
  su - <uzivatel> -c 'echo "startxfce4" > ~/.xsession'
  systemctl restart xrdp
Pri instalaci XFCE ponechat gdm3, ne lightdm.


--------------------------------------------------------------------------------
16. HISTORIE ZASAHU NA STROJI
--------------------------------------------------------------------------------

4.-6. 9. 2026:

Systém:
  - Doinstalovano 64 balicku, ktere apt upgrade odmital (prechod na t64 ABI,
    rozdeleni gnupg 2.4). Reseno pres apt full-upgrade.
  - Kernel povysen z 6.5.0-28 (bez bezpecnostnich oprav od 7/2024) na
    6.8.0-139. Pricinou zaseknuti byl metabalicek linux-generic-hwe-22.04
    zbyly po upgradu z 22.04; nahrazen za linux-generic.
  - VirtualBox: Oracle 7.1.4 nahrazen distribucnim 7.0.16 s DKMS, moduly se
    nove prekladaji automaticky pri kazdem novem kernelu.
  - Docker: repozitar opraven z "mantic" (Ubuntu 23.10) na "noble",
    doplneny DNS resolvery do daemon.json.
  - Firmware: UEFI db na 2023, UEFI dbx na 20260402. BIOS zadnou
    aktualizaci nenabizi.
  - Ubuntu Pro pripojeno (bezplatne osobni predplatne): esm-infra, esm-apps
    a livepatch. 37 balicku z universe doinstalovano, podpora do 2034.
  - Nainstalovan xrdp pro vzdalenou plochu.

NetBox:
  - Puvodni rucne psany stack /opt/fw_stack mel chybnou konfiguraci workeru
    (volal manage.py celery, coz NetBox nezna -- pouziva RQ). Nikdy nebezel.
  - Nahrazen oficialnim netbox-docker, ktery umi instalaci pluginu.
  - Nasazeny pluginy ipfabric_netbox 6.1.0 a netbox-branching 1.1.3.
  - Stary stack archivovan do /root/fw_stack-archiv-2026-09-05.tar.gz,
    jeho volumes a image smazany.

IP Fabric:
  - Napojeni na guided demo (7.9.4). Plugin nefunguje kvuli omezenym
    opravnenim demo uctu (403 na management/snapshots).
  - Data se tahaji primo pres API. Overeno: 95 zarizeni, 263 ACL pravidel,
    4 snapshoty, funkcni path lookup.
  - Postaven retez komunikacni matice: CSV -> simulace cesty -> verdikt
    s odduvodnenim -> CSV report, jako skript na hostiteli i jako NetBox Script.


--------------------------------------------------------------------------------
17. RYCHLY TAHAK
--------------------------------------------------------------------------------

  cd /opt/netbox-docker

  docker compose ps                             co bezi
  docker compose up -d                          nastartovat
  docker compose down                           zastavit
  docker compose restart netbox                 restart aplikace
  docker compose logs --tail=60 netbox          log
  docker compose logs -f netbox-worker          log workeru zive
  docker compose build                          prestavet image
  docker compose exec netbox bash               shell v kontejneru

  docker compose exec netbox /opt/netbox/netbox/manage.py showmigrations ipfabric_netbox | tail -5
  docker compose exec netbox /opt/netbox/netbox/manage.py createsuperuser
  docker compose exec netbox /opt/netbox/netbox/manage.py changepassword admin

  curl -sI http://localhost:8000/ | head -3     test dostupnosti

  cd /opt/commatrix && python3 commatrix_check.py matrix-vzor.csv

================================================================================


================================================================================
18. IMPORT DAT Z IP FABRIC DO NETBOXU
================================================================================

18.1 Jak to funguje
-------------------
Plugin ipfabric_netbox umi dva rezimy zdroje (IP Fabric -> Sources):

  local   = plugin si data tahne sam pres API, potrebuje token s pravem
            na /api/tables/management/snapshots
  remote  = data do NetBoxu nekdo nacpe zvenku, plugin je jen zpracuje

Demo server nam pravo na snapshots nedava (403 API_INSUFFICIENT_RIGHTS),
proto jedeme rezim "remote". Retezec vypada takto:

  IP Fabric API  ->  push_ipf_data.py  ->  IPFabricData  ->  ingesce
                                                              |
                                        transform mapy  ------+
                                                              |
                                            branch (vetev)  <-+
                                                              |
                                                  merge  ->  Main

Ingesce nezapisuje rovnou do hlavni databaze, ale do vetve (plugin
netbox_branching). Teprve merge ji preklopi do Main.

18.2 Predpoklady
----------------
Zdroj "demo" musi byt typu remote:

  IP Fabric -> Sources -> demo -> Edit -> Type = Remote

Pristupove udaje k IP Fabricu jsou v /opt/commatrix/ipf.env (chmod 600)
a soucasne v env/netbox.env, odkud je cte kontejner.

18.3 Krok 1 - nacteni dat do NetBoxu
------------------------------------
  cd /opt/netbox-docker
  docker compose exec -T netbox /opt/netbox/netbox/manage.py shell \
      < /opt/commatrix/push_ipf_data.py

Skript pred vlozenim smaze stara data toho snapshotu, takze opakovany beh
nic nezdvoji. Ocekavany vysledek je 1647 zaznamu v 11 endpointech.

18.4 Krok 2 - ingesce
---------------------
V UI:  IP Fabric -> Syncs -> pokus1 -> Synchronize

Z prikazove radky:

  docker compose exec -T netbox /opt/netbox/netbox/manage.py shell <<'PY'
  from ipfabric_netbox.models import IPFabricSync
  from users.models import User
  s = IPFabricSync.objects.get(name='pokus1')
  u = User.objects.filter(is_superuser=True).order_by('pk').first()
  print('job:', s.enqueue_sync_job(adhoc=True, user=u))
  PY

Trva zhruba tri minuty. Prubeh je videt na IP Fabric -> Ingestions.

18.5 Krok 3 - merge
-------------------
Sync ma zapnuty auto_merge, takze se vetev slouci sama a po merge se
smaze. Rucne zasahovat netreba.

DULEZITE: nikdy nemergovat vetev primo pres branch.merge(). Obejde to
stavovy automat pluginu, sync uvazne ve stavu ready_to_merge a tlacitko
Synchronize prestane fungovat. Spravna cesta je
ingestion.enqueue_merge_job(user=..., remove_branch=True), coz dela
auto_merge automaticky.

Kdyby sync presto uvazl:

  docker compose exec -T netbox /opt/netbox/netbox/manage.py shell <<'PY'
  from ipfabric_netbox.models import IPFabricSync
  from ipfabric_netbox.choices import IPFabricSyncStatusChoices
  s = IPFabricSync.objects.get(name='pokus1')
  s.status = IPFabricSyncStatusChoices.COMPLETED
  s.save(update_fields=['status'])
  print(s.status)
  PY

18.6 Kontrola vysledku
----------------------
  docker compose exec -T netbox /opt/netbox/netbox/manage.py shell <<'PY'
  from ipfabric_netbox.models import IPFabricSync
  from dcim.models import Device, Site, Interface, InventoryItem
  from ipam.models import IPAddress, VLAN, VRF
  s = IPFabricSync.objects.get(name='pokus1')
  i = s.last_ingestion
  print('status:', s.status, '| ingestion:', i.pk, '| issues:', i.issues.count())
  for x in i.issues.all()[:10]:
      print('  -', str(x)[:150])
  for p, m in (('site', Site), ('zarizeni', Device), ('interfacy', Interface),
               ('inventar', InventoryItem), ('IP', IPAddress), ('VLAN', VLAN), ('VRF', VRF)):
      print(f'{p:>12}: {m.objects.count()}')
  print('IP bez rozhrani:', IPAddress.objects.filter(assigned_object_id__isnull=True).count())
  PY

Referencni cisla pro demo snapshot:

  site 13 | zarizeni 95 | typy zarizeni 15 | vyrobci 6 | platformy 8
  interfacy 873 | inventar 98 | IP 389 | VLAN 25 | VRF 51
  issues 6 | IP bez rozhrani 0

VRF musi zustat na 51. Kdyby po kazdem syncu rostlo, je rozbite parovani
(viz 18.7).

18.7 Upravy transform map a proc
--------------------------------
Vychozi mapy pluginu na demo datech neprojdou. Zmeny jsou ulozene v
databazi, prezijou restart i rebuild kontejneru, ale NEprezijou obnovu
databaze ze zalohy porizene pred nimi.

(a) Device -> serial

    Puvodne:  {{ object | serial }}

    Filtr serial() vraci prazdno, kdyz je sn delsi nez 50 znaku (limit
    pole v NetBoxu), a nahradi ho sloupcem id. Jenze strip_source_data()
    ridi predavane sloupce podle get_required_source_columns() a id mezi
    nimi neni - fallback tedy sahne do prazdna a vysledek je NULL.
    Ingesce pak spadne na "null value in column serial". Tyka se
    cloudovych objektu (AWS NLB, VPC endpoint), jejichz sn je cely ARN.

    Nove:
    {% set S = object.sn if object.sn else '' %}{% if S|length > 0 and S|length < 50 %}{{ S }}{% else %}{{ object.hostname[:50] }}{% endif %}

(b) Interface -> relace device

    Vyhledani zarizeni podle serialu selze u tech objektu, kde je serial
    podle (a) odvozeny z hostname. Doplneno stejne pravidlo:

    {% set SN = object.stackMemberSn or object.sn %}{% if SN and SN|length < 50 %}{{ dcim.Device.objects.get(serial=SN).pk }}{% else %}{{ dcim.Device.objects.get(name=object.hostname).pk }}{% endif %}

(c) IP address -> assigned_object_id

    Totez pro vyhledani rozhrani:

    {% set NAME = object.nameOriginal or object.intName %}{% if object.sn and object.sn|length < 50 %}{{ dcim.Interface.objects.filter(device__serial=object.sn, name=NAME).first().pk }}{% else %}{{ dcim.Interface.objects.filter(device__name=object.hostname, name=NAME).first().pk }}{% endif %}

Poznamka: pouziti object.hostname v sablone soucasne zaridi, ze se
hostname dostane do get_required_source_columns() a strip_source_data()
ho neodrizne. Bez toho by oprava nefungovala.

Vypis aktualnich map:

  docker compose exec -T netbox /opt/netbox/netbox/manage.py shell <<'PY'
  from ipfabric_netbox.models import IPFabricTransformMap
  for tm in IPFabricTransformMap.objects.all():
      print('==', tm, '| required:', sorted(tm.get_required_source_columns()))
      for fm in tm.field_maps.all():
          print('   FM', repr(fm.source_field), '->', fm.target_field, '|', fm.template)
      for rm in tm.relationship_maps.all():
          print('   REL ->', rm.target_field, '|', rm.template)
  PY

18.8 Duplicitni VRF - pozor na prazdne retezce
----------------------------------------------
VRF se paruje na dvojici name + rd. V demo datech je rd u vetsiny VRF
prazdne. Pokud push posle prazdny RETEZEC, NetBox si ulozi NULL a dalsi
sync uz shodu nenajde - pri kazdem behu tedy pribyde 50 novych VRF.

Proto v push_ipf_data.py NESMI byt "rd" v mnozine TEXTOVE_SLOUPCE.
Prazdna hodnota musi zustat None, aby se v coalesce prelozila na
rd__isnull=True.

Uklid duplicit, kdyby k tomu nekdy doslo:

  docker compose exec -T netbox /opt/netbox/netbox/manage.py shell <<'PY'
  from ipam.models import VRF
  from collections import defaultdict
  skupiny = defaultdict(list)
  for v in VRF.objects.order_by('pk'):
      skupiny[(v.name, v.rd)].append(v)
  ids = [v.pk for g in skupiny.values() for v in g[1:]]
  print('mazu:', len(ids))
  VRF.objects.filter(pk__in=ids).delete()
  print('zbylo:', VRF.objects.count())
  PY

18.9 Nastaveni NetBoxu
----------------------
Demo obsahuje stejne IP adresy ve vice VRF, proto musi byt vypnute
ENFORCE_GLOBAL_UNIQUE:

  Admin -> Configuration -> Config Revision -> Enforce global unique = ne

Bez toho ingesce padne na "Duplicate IP address found in global table".

18.10 Znama omezeni
-------------------
- 6 issues pri kazdem behu: IPv6 link-local adresy (fe80::) na IOS
  routerech. IP tabulka udava zkracene jmeno rozhrani (Gi0/1), NetBox ma
  GigabitEthernet0/1, shoda tedy nevznikne. Pro komunikacni matici jsou
  link-local adresy nepodstatne, neresime.
- Endpoint /technology/networks/managed-networks nemame namapovany,
  spravny nazev tabulky v API 7.9 zatim neznamy. Prefixy se proto
  neimportuji.
- Rezim local (plugin si data tahne sam) vyzaduje na strane IP Fabricu
  pravo na /api/tables/management/snapshots. Na demo serveru ho nemame.
  Na firemni instanci 7.5 o nej pozadat.
