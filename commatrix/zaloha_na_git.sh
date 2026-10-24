#!/usr/bin/env bash
#
# Zaloha zdrojaku NetBox + IP Fabric ze stroje blue-ThinkCentre-M710s do gitu.
#
# Spusteni:
#     chmod +x zaloha_na_git.sh
#     ./zaloha_na_git.sh
#
# Volby:
#     --bez-push            pripravi commit, ale neposila na GitHub
#     --bez-exportu         preskoci export konfigurace z databaze
#     --zprava "text"       vlastni text commitu
#
# Vetev main je chranena (zmeny jen pres pull request), proto skript
# commituje do vetve zaloha-<datum> zalozene z aktualni main a po pushi
# vypise odkaz, kterym se pull request otevre.
#
# Promenne prostredi (vsechny maji rozumnou vychozi hodnotu):
#     REPO            adresa repozitare
#     PRACOVNI        kam se repozitar klonuje
#     COMMATRIX       slozka s vlastnimi skripty
#     NETBOXDOCKER    slozka s nasazenim NetBoxu
#     VETEV           vetev pro zalohu (vychozi zaloha-<datum>)
#
# Skript je idempotentni - lze ho poustet opakovane. Pokud se nic nezmenilo,
# neudela zadny commit.
#
# Kontroly uniku pristupovych udaju se tykaji toho, co skript do repozitare
# prave pridava. Co uz v repozitari je, neposuzuje a nenavrhuje mazat.

set -euo pipefail

REPO="${REPO:-https://github.com/obhichus/Netbox.git}"
PRACOVNI="${PRACOVNI:-$HOME/netbox-git}"
COMMATRIX="${COMMATRIX:-/opt/commatrix}"
NETBOXDOCKER="${NETBOXDOCKER:-/opt/netbox-docker}"
VETEV="${VETEV:-zaloha-$(date +%Y-%m-%d)}"
ZPRAVA=""
PUSH=1
EXPORT=1

# Soubory, ktere opravdu nesou tajemstvi. Posuzuje se jmeno, ne pripona -
# versions.env v netbox-dockeru drzi jen verze obrazu a tajne neni.
TAJNE_SOUBORY="ipf.env netbox.env postgres.env redis.env redis-cache.env superuser.env ldap.env"

while [ $# -gt 0 ]; do
    case "$1" in
        --bez-push)    PUSH=0 ;;
        --bez-exportu) EXPORT=0 ;;
        --zprava)      shift; ZPRAVA="${1:-}" ;;
        -h|--help)     sed -n '3,29p' "$0"; exit 0 ;;
        *)             printf 'Neznama volba: %s\n' "$1" >&2; exit 2 ;;
    esac
    shift
done

if [ -z "$ZPRAVA" ]; then
    ZPRAVA="Zaloha zdrojaku z $(hostname -s) ze dne $(date +%Y-%m-%d)"
fi

info()     { printf '\n== %s\n' "$*"; }
detail()   { printf '   %s\n' "$*"; }
varovani() { printf '   POZOR: %s\n' "$*" >&2; }

# Pri chybe se rozpracovany index vzdy uklidi, aby v pracovni kopii
# nezustal napulce pripraveny commit.
chyba() {
    if [ -d "${PRACOVNI:-/nic}/.git" ]; then
        git -C "$PRACOVNI" reset -q 2>/dev/null || true
    fi
    printf '\nCHYBA: %s\n' "$*" >&2
    exit 1
}

je_tajny() {
    local jmeno="$1" t
    for t in $TAJNE_SOUBORY; do
        [ "$jmeno" = "$t" ] && return 0
    done
    return 1
}


# ------------------------------------------------------------------
# 1. Kontrola prostredi
# ------------------------------------------------------------------

info "Kontrola prostredi"

command -v git >/dev/null || chyba "git neni nainstalovan"
[ -d "$COMMATRIX" ] || chyba "slozka $COMMATRIX neexistuje"
[ -d "$NETBOXDOCKER" ] || chyba "slozka $NETBOXDOCKER neexistuje"

COMPOSE=""
if docker compose version >/dev/null 2>&1; then
    COMPOSE="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE="docker-compose"
fi

if [ -z "$COMPOSE" ] && [ "$EXPORT" -eq 1 ]; then
    varovani "docker compose neni dostupny, export konfigurace se preskoci"
    EXPORT=0
fi

detail "repozitar      $REPO"
detail "pracovni kopie $PRACOVNI"
detail "zdrojaky       $COMMATRIX"


# ------------------------------------------------------------------
# 2. Pracovni kopie repozitare
# ------------------------------------------------------------------

info "Pracovni kopie repozitare"

if [ -d "$PRACOVNI/.git" ]; then
    detail "existuje, aktualizuji"
else
    detail "klonuji"
    git clone "$REPO" "$PRACOVNI" || chyba "klonovani selhalo - je repozitar soukromy a mas tu token?"
fi

# Zaloha jde do vlastni vetve, main je chranena. Kdyz vetev dnesniho dne
# uz na GitHubu je (druhy beh tentyz den), navaze se na ni, jinak se
# zalozi z aktualni main.
git -C "$PRACOVNI" fetch -q origin || varovani "fetch selhal, pokracuji s lokalnim stavem"
if git -C "$PRACOVNI" rev-parse -q --verify "refs/remotes/origin/$VETEV" >/dev/null; then
    zaklad="origin/$VETEV"
else
    zaklad="origin/main"
fi
git -C "$PRACOVNI" checkout -q -B "$VETEV" "$zaklad" \
    || chyba "nelze prepnout na vetev $VETEV - neni v $PRACOVNI rozpracovana zmena?"
detail "vetev          $VETEV (z $zaklad)"

# Konfigurace z netbox-dockeru patri do reference/, stejne jako v repozitari.
# configuration/ v koreni repozitare je konfigurace pro RHEL9 a neprepisuje se.
CIL_KONFIGURACE="$PRACOVNI/reference/puvodni-netbox-docker"
mkdir -p "$PRACOVNI/commatrix" "$CIL_KONFIGURACE"


# ------------------------------------------------------------------
# 3. Kopie vlastnich skriptu a dat
#
# Zamerne vyctem pripon, ne celou slozkou. Tim se do repozitare nemuze
# dostat ipf.env ani adresar s dumpem snapshotu.
# ------------------------------------------------------------------

info "Kopie zdrojaku z $COMMATRIX"

pocet=0
for pripona in py csv txt md sh; do
    for soubor in "$COMMATRIX"/*."$pripona"; do
        [ -f "$soubor" ] || continue
        cp -p "$soubor" "$PRACOVNI/commatrix/"
        detail "$(basename "$soubor")"
        pocet=$((pocet + 1))
    done
done
[ "$pocet" -gt 0 ] || chyba "v $COMMATRIX se nenasel zadny zdrojak"
detail "celkem $pocet souboru"


# ------------------------------------------------------------------
# 4. Kopie konfigurace nasazeni
#
# Slozka env/ se nekopiruje nikdy - obsahuje heslo k IP Fabric.
# versions.env se kopiruje zamerne, drzi verze obrazu.
# ------------------------------------------------------------------

info "Kopie konfigurace z $NETBOXDOCKER"

for rel in README.txt plugin_requirements.txt Dockerfile-Plugins \
           docker-compose.override.yml versions.env \
           configuration/extra.py configuration/configuration.py
do
    if [ -f "$NETBOXDOCKER/$rel" ]; then
        if je_tajny "$(basename "$rel")"; then
            varovani "$rel je na seznamu tajnych souboru, preskakuji"
            continue
        fi
        cp -p "$NETBOXDOCKER/$rel" "$CIL_KONFIGURACE/$(basename "$rel")"
        detail "$rel"
    else
        detail "$rel - neni, preskakuji"
    fi
done


# ------------------------------------------------------------------
# 5. Export konfigurace, ktera zije jen v databazi
#
# Transformacni mapy, registrace skriptu, nastenky a konfiguracni revize
# nejsou v zadnem souboru. Bez nich neni obnova ze zalohy uplna.
# ------------------------------------------------------------------

if [ "$EXPORT" -eq 1 ]; then
    info "Export konfigurace z databaze"

    if [ ! -f "$COMMATRIX/export_konfigurace.py" ]; then
        varovani "$COMMATRIX/export_konfigurace.py chybi, export se preskoci"
    else
        if (cd "$NETBOXDOCKER" && $COMPOSE exec -T netbox \
                /opt/netbox/netbox/manage.py shell \
                < "$COMMATRIX/export_konfigurace.py")
        then
            rm -rf "$PRACOVNI/export-konfigurace"
            if (cd "$NETBOXDOCKER" && $COMPOSE cp \
                    netbox:/opt/netbox/netbox/media/export-konfigurace \
                    "$PRACOVNI/export-konfigurace")
            then
                detail "vyzvednuto do $PRACOVNI/export-konfigurace"
            else
                varovani "kopie z kontejneru selhala"
            fi
        else
            varovani "export v kontejneru selhal, pokracuji bez nej"
        fi
    fi
fi


# ------------------------------------------------------------------
# 6. .gitignore
#
# Jmenovite, ne pres *.env - jinak by pravidlo zahrnovalo i versions.env.
# Ne cele env/ - v repozitari jsou v env/ vzory *.example, ktere tam patri.
# ------------------------------------------------------------------

info "Kontrola .gitignore"

for vzor in $TAJNE_SOUBORY '__pycache__/' '*.pyc' 'dump/' '*.swp'; do
    if ! grep -qxF "$vzor" "$PRACOVNI/.gitignore" 2>/dev/null; then
        printf '%s\n' "$vzor" >> "$PRACOVNI/.gitignore"
        detail "pridano $vzor"
    fi
done


# ------------------------------------------------------------------
# 7. Priprava indexu
# ------------------------------------------------------------------

info "Priprava commitu"

cd "$PRACOVNI"
git add -A

if git diff --cached --quiet; then
    detail "nic se nezmenilo, commit se nedela"
    exit 0
fi

PRIDAVANE="$(git diff --cached --name-only)"
detail "menenych souboru: $(printf '%s\n' "$PRIDAVANE" | grep -c .)"


# ------------------------------------------------------------------
# 8. Kontrola uniku pristupovych udaju
#
# Vse se tyka jen souboru z kroku 7, tedy toho, co prave pridavame.
# Obsah, ktery uz v repozitari byl, se neposuzuje.
# ------------------------------------------------------------------

info "Kontrola uniku pristupovych udaju"

# 8a. Pridavame nejaky soubor ze seznamu tajnych?
while IFS= read -r soubor; do
    [ -n "$soubor" ] || continue
    if je_tajny "$(basename "$soubor")"; then
        chyba "commit by pridal tajny soubor $soubor - odstran ho z pracovni kopie"
    fi
done <<< "$PRIDAVANE"
detail "zadny tajny soubor se nepridava"

# 8b. Hodnoty z ipf.env hledane doslova v pridavanych souborech.
#     Nejsilnejsi kontrola - hleda konkretni heslo, ne jeho vzor.
#     Hodnota se nikdy nevypisuje.
if [ -r "$COMMATRIX/ipf.env" ]; then
    kontrolovano=0
    while IFS= read -r radek || [ -n "$radek" ]; do
        case "$radek" in ''|'#'*) continue ;; esac
        case "$radek" in *=*) ;; *) continue ;; esac

        klic="${radek%%=*}"
        klic="${klic#export }"
        hodnota="${radek#*=}"
        hodnota="${hodnota%\"}"; hodnota="${hodnota#\"}"
        hodnota="${hodnota%\'}"; hodnota="${hodnota#\'}"

        # Jen klice, ktere nesou tajemstvi. URL a jmeno uzivatele ve
        # skriptech byt smi a nesmi commit zastavit.
        case "$(printf '%s' "$klic" | tr '[:lower:]' '[:upper:]')" in
            *PASS*|*TOKEN*|*SECRET*|*KEY*) ;;
            *) continue ;;
        esac

        [ "${#hodnota}" -ge 6 ] || continue
        kontrolovano=$((kontrolovano + 1))

        while IFS= read -r soubor; do
            [ -n "$soubor" ] && [ -f "$soubor" ] || continue
            if grep -qF -- "$hodnota" "$soubor" 2>/dev/null; then
                chyba "soubor $soubor obsahuje hodnotu klice $klic z ipf.env"
            fi
        done <<< "$PRIDAVANE"
    done < "$COMMATRIX/ipf.env"
    detail "overeno $kontrolovano tajnych hodnot z ipf.env, zadna se nenasla"
else
    varovani "$COMMATRIX/ipf.env neni citelny - zkus skript pod sudo -E."
    varovani "Kontrola na konkretni hodnoty se NEPROVEDLA."
fi

# 8c. Obecny vzor prirazeni hesla do promenne s literalem.
#
#     Hodnota musi byt v uvozovkach, uzavrena a bez mezer. Bez te podminky
#     vzor chytal i dokumentaci: v radku
#         grep -E '^POSTGRES_PASSWORD=' env/postgres.env | cut -d= -f2-
#     je za POSTGRES_PASSWORD= uzaviraci apostrof grepu a jako hodnota se
#     tvarilo " env/postgres.env | cut -d".
#
#     Nezachyti heslo zapsane bez uvozovek. Na to je kontrola 8b, ktera
#     hleda konkretni hodnoty z ipf.env.
#
#     Radky, ktere hodnotu ctou z prostredi, se ignoruji. Opravneny nalez
#     lze schvalit zapisem "cesta/k/souboru:cislo-radku" do souboru
#     .zaloha-povoleno v korenu repozitare.
VZOR='(PASS|PASSWORD|PASSWD|TOKEN|SECRET|API_?KEY)[A-Za-z_]*[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"'[:space:]]{4,}["'"'"']'
VYJIMKY='os\.environ|getenv|nacti_env|input\(|CITLIVE|vynechane|example|zmen_me|sys\.argv'
POVOLENE="$PRACOVNI/.zaloha-povoleno"

nalezy=""
schvaleno=0
while IFS= read -r soubor; do
    [ -n "$soubor" ] && [ -f "$soubor" ] || continue
    while IFS= read -r radek; do
        [ -n "$radek" ] || continue
        cislo="${radek%%:*}"

        if printf '%s' "$radek" | grep -qE -- "$VYJIMKY"; then
            continue
        fi
        if [ -f "$POVOLENE" ] && grep -qxF -- "$soubor:$cislo" "$POVOLENE"; then
            schvaleno=$((schvaleno + 1))
            continue
        fi

        nalezy="$nalezy$soubor:$cislo
"
    done <<< "$(grep -InE -- "$VZOR" "$soubor" 2>/dev/null || true)"
done <<< "$PRIDAVANE"

if [ -n "$(printf '%s' "$nalezy" | tr -d '[:space:]')" ]; then
    printf '\n'
    printf '%s' "$nalezy"
    printf '\n'
    printf 'Zkontroluj ty radky. Kdyz jde o dokumentaci nebo ukazku, pridej je\n'
    printf 've tvaru soubor:radek do %s\n' "$POVOLENE"
    chyba "vyse vypsane radky vypadaji jako heslo zapsane v kodu"
fi

if [ "$schvaleno" -gt 0 ]; then
    detail "zadne nove heslo v kodu ($schvaleno drive schvalenych nalezu)"
else
    detail "zadne heslo zapsane primo v kodu"
fi


# ------------------------------------------------------------------
# 9. Commit a push
# ------------------------------------------------------------------

info "Commit"

git diff --cached --stat | tail -n 25

git commit -q -m "$ZPRAVA"
detail "commit vytvoren: $(git log -1 --format=%h)"

if [ "$PUSH" -eq 0 ]; then
    info "Push preskocen (--bez-push)"
    detail "odeslat lze pozdeji: git -C $PRACOVNI push -u origin $VETEV"
    exit 0
fi

info "Push na GitHub"
if git push -q -u origin "$VETEV"; then
    detail "hotovo, vetev $VETEV"
    WEB="${REPO%.git}"
    case "$WEB" in https://github.com/*)
        detail "pull request: $WEB/compare/main...$VETEV?expand=1" ;;
    esac
else
    printf '\n'
    varovani "push selhal, commit ale zustal v $PRACOVNI"
    varovani "Nejcastejsi pricina: na tomhle stroji nejsou pristupove udaje k GitHubu."
    varovani "Moznosti:"
    varovani "  1) git -C $PRACOVNI push -u origin $VETEV  a zadat uzivatele obhichus a osobni token"
    varovani "  2) nainstalovat gh a prihlasit se: gh auth login"
    varovani "  3) odeslat z Windows DC, kde uz gh prihlaseny je"
    exit 1
fi
