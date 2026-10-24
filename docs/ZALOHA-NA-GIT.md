# 11. Záloha zdrojáků na git – skript zaloha_na_git.sh

Skript je v repu jako [commatrix/zaloha_na_git.sh](../commatrix/zaloha_na_git.sh).

> **Upraveno 2026-10-24 oproti původnímu textu níže** (po Romanově souhlasu):
> - `main` je chráněný, proto skript commituje do větve `zaloha-<datum>` založené z aktuální `main`
>   (při druhém běhu téhož dne naváže na existující větev) a po pushi vypíše odkaz na pull request.
>   Větev jde změnit proměnnou `VETEV`. Pull request se pak sloučí jako každý jiný.
> - Konfigurace z `/opt/netbox-docker` se ukládá do `reference/puvodni-netbox-docker/`, ne do nové složky
>   `netbox-docker/`. `configuration/` v kořeni repa je konfigurace pro RHEL9 a skript ji nepřepisuje.
> - Do `.gitignore` se nepřidává celé `env/` (v repu jsou vzory `env/*.example`, které tam patří).
> - Navíc se zálohují doklady `/opt/commatrix/doklady/*.pdf` do `commatrix/doklady/`
>   (např. [dashboard IP Fabricu ke snímku 22443e66](../commatrix/doklady/ipfabric-dashboard-22443e66.pdf)).
>
> Kde se text níže od toho liší, platí tahle poznámka.

Skript sebere všechny vlastní zdrojáky a konfiguraci ze stroje blue-ThinkCentre-M710s, vytáhne
z databáze NetBoxu to, co nikde v souboru není, a odešle všechno do repozitáře
https://github.com/obhichus/Netbox

Důvod existence: podstatná část práce není v žádném gitem sledovaném souboru. Vlastní skripty ležely
v `/opt/commatrix`, konfigurace v `/opt/netbox-docker` a transformační mapy, registrace skriptů,
nástěnky a konfigurační revize jen v databázi. Bez zálohy všech tří částí nelze prostředí obnovit.


## 11.1 Použití

```sh
chmod +x ~/zaloha_na_git.sh
~/zaloha_na_git.sh --bez-push
~/zaloha_na_git.sh
```

První běh vždy s `--bez-push`. Vypíše se, co se chystá odeslat, a teprve po kontrole se spustí
načisto podruhé už bez té volby.

Volby:

| | |
|---|---|
| `--bez-push` | připraví commit, ale neposílá na GitHub |
| `--bez-exportu` | přeskočí export konfigurace z databáze |
| `--zprava "text"` | vlastní text commitu |
| `-h`, `--help` | vypíše hlavičku skriptu |

Proměnné prostředí, všechny s rozumnou výchozí hodnotou:

| | |
|---|---|
| `REPO` | adresa repozitáře |
| `PRACOVNI` | kam se repozitář klonuje (`$HOME/netbox-git`) |
| `COMMATRIX` | složka s vlastními skripty (`/opt/commatrix`) |
| `NETBOXDOCKER` | složka s nasazením (`/opt/netbox-docker`) |
| `VETEV` | větev pro zálohu (`zaloha-<datum>`), doplněno 2026-10-24 |

Skript je idempotentní. Když se od posledního běhu nic nezměnilo, neudělá žádný commit a skončí
návratovým kódem 0.

Spouštět pod rootem, nebo přes `sudo -E`. Důvod je v 11.4.


## 11.2 Co skript dělá, v pořadí

1. Kontrola prostředí – git, obě složky, dostupnost docker compose.
2. Pracovní kopie – naklonuje repozitář, nebo ji aktualizuje pull.
   *(Nově: fetch a přepnutí na větev `zaloha-<datum>`.)*
3. Kopie zdrojáků z `/opt/commatrix`.
4. Kopie konfigurace z `/opt/netbox-docker`.
5. Export konfigurace z databáze a vyzvednutí z kontejneru.
6. Doplnění `.gitignore`.
7. `git add` a zjištění, co se právě přidává.
8. Tři kontroly úniku přístupových údajů.
9. Commit a push.

Krok 8 je až za krokem 7 záměrně. Kontroly se tím týkají jen toho, co se právě přidává, a neposuzují
obsah, který už v repozitáři je. Dřív to bylo opačně a skript navrhoval mazat soubory, které do
repozitáře patřily.


## 11.3 Co se kopíruje a co ne

Z `/opt/commatrix` vše s příponou py, csv, txt, md a sh (a nově `doklady/*.pdf`).

Výčtem přípon, ne celou složkou. Je to záměr: `ipf.env` se tím nemůže dostat do repozitáře ani omylem
a adresář s dumpem snapshotu se nekopíruje vůbec.

Z `/opt/netbox-docker` jmenovitě (nově do `reference/puvodni-netbox-docker/`):

```
README.txt
plugin_requirements.txt
Dockerfile-Plugins
docker-compose.override.yml
versions.env
configuration/extra.py
configuration/configuration.py
```

Z databáze přes `/opt/commatrix/export_konfigurace.py`:

- transformační mapy pluginu
- registrované NetBox Scripty
- rozložení nástěnek
- aktivní konfigurační revize bez citlivých klíčů

Nekopíruje se NIKDY:

| | |
|---|---|
| `/opt/netbox-docker/env/` | hesla k databázi, Redisu a IP Fabric |
| `/opt/commatrix/ipf.env` | přístup k IP Fabric |
| `IPFabricSource` | obsahuje přístupové údaje |

`versions.env` se naopak kopíruje záměrně. Drží verze obrazů, nic tajného v něm není a do zálohy patří.
Původní verze skriptu ho odmítala, protože soudila soubory podle přípony `.env` – to byla chyba,
viz 11.7.


## 11.4 Tři kontroly úniku přístupových údajů

Kterákoli z nich zastaví commit. Při zastavení se index uklidí přes `git reset`, takže v pracovní
kopii nezůstane napůl připravený commit.

**8a. Tajné soubory podle JMÉNA**

`ipf.env`, `netbox.env`, `postgres.env`, `redis.env`, `redis-cache.env`, `superuser.env`, `ldap.env`

Posuzuje se jméno, nikoli přípona. Jiná pravidla se nepoužívají.

**8b. Konkrétní hodnoty z ipf.env, hledané doslova**

Nejsilnější kontrola. Skript přečte `ipf.env`, vezme hodnoty klíčů obsahujících PASS, TOKEN, SECRET
nebo KEY a hledá je v přidávaných souborech doslovným grepem.

Hledá tedy konkrétní heslo, ne jeho vzor, a hodnotu nikdy nevypisuje – v hlášce je jen jméno klíče
a soubor.

Klíče jako `IPF_URL` nebo `IPF_USER` se záměrně nekontrolují. Adresa demo instance a jméno uživatele
ve skriptech být smí a nesmí commit zastavit.

Tahle kontrola potřebuje číst `ipf.env`, který má práva 600. Když na něj skript nedosáhne, ohlásí to
jako POZOR a pokračuje – ale nejsilnější kontrola se NEPROVEDE. Proto se skript pouští pod rootem
nebo přes `sudo -E`.

**8c. Obecný vzor hesla zapsaného v kódu**

Hledá přiřazení do proměnné, jejíž jméno obsahuje PASS, PASSWORD, PASSWD, TOKEN, SECRET nebo API_KEY,
kde hodnota je v uvozovkách, uzavřená a bez mezer.

Řádky, které hodnotu čtou z prostředí (`os.environ`, `getenv`, `nacti_env`), se ignorují.

Nezachytí heslo zapsané bez uvozovek. Na to je kontrola 8b.


## 11.5 Schválené nálezy – .zaloha-povoleno

Kontrola 8c může označit řádek, který heslo není – typicky ukázku v dokumentaci. Takový nález se
schválí zápisem do souboru `.zaloha-povoleno` v kořenu repozitáře, jeden řádek na nález ve tvaru
`cesta:číslo-řádku`:

```
netbox-docker/Dockerfile-Plugins:8
```

*(S upravenou verzí skriptu je cesta `reference/puvodni-netbox-docker/Dockerfile-Plugins:8`.)*

Soubor se commituje spolu s ostatním, takže schválení platí i při dalších bězích a v repozitáři je
vidět, co a kde se jednou posoudilo jako v pořádku. Při dalším běhu skript vypíše, kolik dříve
schválených nálezů přeskočil.

Schvaluj jen po přečtení toho řádku. Seznam, do kterého se přidává bez kontroly, je horší než žádná
kontrola.


## 11.6 Hlášení a co s nimi

**`klonovani selhalo - je repozitar soukromy a mas tu token?`**
Na stroji nejsou přístupové údaje k GitHubu. Viz 11.8.

**`v COMMATRIX se nenasel zadny zdrojak`**
Špatná hodnota `COMMATRIX`, nebo prázdná složka. Skript zastavuje záměrně – prázdný commit by vypadal
jako úspěšná záloha.

**`export v kontejneru selhal, pokracuji bez nej`**
NetBox neběží, nebo chybí `export_konfigurace.py`. Záloha souborů proběhne, ale BEZ transformačních
map. Dořešit.

**`commit by pridal tajny soubor X`**
V pracovní kopii je soubor ze seznamu 8a. Odstranit a spustit znovu.

**`soubor X obsahuje hodnotu klice Y z ipf.env`**
Skutečný únik. Heslo je v souboru, který se chystal odejít na GitHub. Opravit soubor a zvážit změnu
hesla v IP Fabric – pokud ten soubor někdy někomu odešel, heslo už není tajné.

**`vyse vypsane radky vypadaji jako heslo zapsane v kodu`**
Přečti ty řádky. Buď je to skutečně heslo a opraví se, nebo ukázka a přidá se do `.zaloha-povoleno`.

**`ipf.env neni citelny - zkus skript pod sudo -E`**
Nejsilnější kontrola se neprovedla. Spustit znovu s právy.

**`push selhal, commit ale zustal v PRACOVNI`**
Commit existuje lokálně, jen neodešel. Viz 11.8.

**`nelze prepnout na vetev ...`** *(nové)*
V pracovní kopii je rozpracovaná změna, která koliduje s větví. Prohlédnout `git -C ~/netbox-git status`.


## 11.7 Dvě chyby, které skript už nedělá

Obě stojí za zapamatování, protože stejné chyby se dají udělat v jakékoli podobné kontrole.

**Soudit soubor podle přípony**

První verze odmítla jakýkoli soubor `*.env` a navrhla smazat `versions.env` – soubor, který do
repozitáře patří a už v něm byl. Kontrola, která uživateli říká, aby mazal správné soubory, je horší
než žádná. Posuzuje se jméno.

**Brát za hodnotu vše do další uvozovky**

Vzor v 8c hlásil poplach nad dokumentací. V řádku

```
grep -E '^POSTGRES_PASSWORD=' env/postgres.env | cut -d= -f2-
```

je za `POSTGRES_PASSWORD=` uzavírací apostrof toho grepu a jako hodnota se tvářilo
`" env/postgres.env | cut -d"`. Opraveno požadavkem na uzavřenou hodnotu bez mezer.


## 11.8 Push a přístup ke GitHubu

Na blue žádné přístupové údaje k GitHubu nejsou, takže push nejspíš selže. Commit tím nezmizí, zůstane
v pracovní kopii a odešle se později.

Tři možnosti:

1. `git -C ~/netbox-git push -u origin zaloha-<datum>`
   a zadat uživatele obhichus a osobní token jako heslo
2. nainstalovat gh a přihlásit se: `gh auth login`
3. odeslat z Windows DC, kde už je gh přihlášený

Na Windows DC je klon v `C:\claude\work\Netbox`, aktualizuje se přes `git pull`.

*(Původně stálo v bodě 1 jen `git push`; push do `main` by ale chráněná větev odmítla.)*


## 11.9 Údržba skriptu

**Přidat soubor do zálohy**
Nový soubor v `/opt/commatrix` s příponou py, csv, txt, md nebo sh se zálohuje sám (PDF jen ze složky
`doklady/`). Soubor z `/opt/netbox-docker` se musí doplnit do výčtu v kroku 4.

**Přidat tajný soubor**
Doplnit jeho jméno do proměnné `TAJNE_SOUBORY`. Tím se zároveň dostane do `.gitignore` a do kontroly 8a.

**Změnit cílový repozitář**
`REPO=https://github.com/... ~/zaloha_na_git.sh`


## 11.10 Co skript nekontroluje

Kontroly se týkají toho, co se právě přidává. Pokud už nějaký tajný soubor v repozitáři JE a nemění
se, skript si ho nevšimne – na historii nekouká.

Jednorázové ověření:

```sh
git -C ~/netbox-git ls-files | grep -E \
  '(^|/)(ipf|netbox|postgres|redis|redis-cache|superuser|ldap)\.env$'
```

Když se něco vypíše, samotné smazání souboru nestačí – zůstane v historii. Nejdřív změnit příslušné
heslo, teprve potom řešit přepis historie.
