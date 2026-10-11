#!/usr/bin/python3
"""Konfigurator napojeni NetBoxu na IP Fabric (SZ) na RHEL9 bez internetu.

Zjisti verzi IP Fabricu, prepne SDK pluginu ipfabric_netbox na odpovidajici verzi
(offline, z wheelu v obrazu), zapise pristupove udaje pro skripty a nastavi zdroj
IP Fabric v NetBoxu.

    sudo /opt/netbox-offline/deploy/configure-ipfabric.py          # interaktivne
    sudo /opt/netbox-offline/deploy/configure-ipfabric.py --apply  # znovu pouzit ulozene nastaveni
                                                                   # (vola install.sh po upgradu)

Proc na verzi zalezi: SDK `ipfabric` musi mit stejnou verzi major.minor jako server
IP Fabricu, jinak plugin odmitne komunikovat nebo cte spatne sloupce tabulek.
Plugin ipfabric_netbox 6.1.0 podporuje IP Fabric 7.0, 7.2, 7.3, 7.5, 7.8, 7.9, 7.10, 7.11.

Ulozene nastaveni:
  /opt/netbox-offline/env/ipfabric.conf   URL, verze, nazev zdroje, rezim, CA (bez hesel)
  /opt/netbox-offline/env/netbox.env      IPF_URL, IPF_USER, IPF_PASS, IPF_TOKEN (pro skripty v kontejneru)
  /opt/netbox-offline/commatrix/ipf.env   totez pro skripty na hostiteli
"""
import argparse
import getpass
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

DEST = "/opt/netbox-offline"
CONF = DEST + "/env/ipfabric.conf"
NETBOX_ENV = DEST + "/env/netbox.env"
HOST_ENV = DEST + "/commatrix/ipf.env"
CA_BUNDLE = DEST + "/env/ca-bundle.crt"
CA_IN_CONTAINER = "/etc/netbox-ca/ca-bundle.crt"
CA_IPF = DEST + "/env/ipfabric-ca.crt"
QUADLETS = ["/etc/containers/systemd/netbox.container", "/etc/containers/systemd/netbox-worker.container"]
SYSTEM_CA = ["/etc/pki/tls/certs/ca-bundle.crt", "/etc/ssl/certs/ca-certificates.crt"]

# verze IP Fabricu (major.minor), pro ktere ma plugin 6.1.0 extra a obraz wheel SDK
PODPOROVANE = ["7.0", "7.2", "7.3", "7.5", "7.8", "7.9", "7.10", "7.11"]


def info(msg):
    print("== " + msg, flush=True)


def chyba(msg):
    print("CHYBA: " + msg, file=sys.stderr)
    sys.exit(1)


def run(cmd, check=True, capture=False, stdin=None):
    r = subprocess.run(cmd, check=False, text=True, input=stdin,
                       stdout=subprocess.PIPE if capture else None,
                       stderr=subprocess.STDOUT if capture else None)
    if check and r.returncode != 0:
        if capture:
            print(r.stdout)
        chyba("prikaz selhal: " + " ".join(cmd))
    return r


def nacti_env(path):
    data = {}
    if os.path.exists(path):
        for radek in open(path, encoding="utf-8"):
            radek = radek.rstrip("\n")
            if "=" in radek and not radek.lstrip().startswith("#"):
                k, v = radek.split("=", 1)
                data[k.strip()] = v
    return data


def zapis_env(path, hodnoty, mode=0o600):
    """Nahradi nebo prida klice KEY=hodnota, ostatni radky necha jak jsou."""
    radky = open(path, encoding="utf-8").read().splitlines() if os.path.exists(path) else []
    zbyva = dict(hodnoty)
    out = []
    for radek in radky:
        klic = radek.split("=", 1)[0].strip() if "=" in radek and not radek.lstrip().startswith("#") else None
        if klic in zbyva:
            out.append("%s=%s" % (klic, zbyva.pop(klic)))
        else:
            out.append(radek)
    out += ["%s=%s" % (k, v) for k, v in zbyva.items()]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    os.chmod(path, mode)


def zeptej(otazka, vychozi="", tajne=False):
    napoveda = " [%s]" % ("***" if tajne and vychozi else vychozi) if vychozi else ""
    while True:
        odp = (getpass.getpass if tajne else input)("%s%s: " % (otazka, napoveda)).strip()
        if odp:
            return odp
        if vychozi or vychozi == "" and tajne:
            return vychozi


def major_minor(verze):
    m = re.match(r"v?(\d+)\.(\d+)", verze or "")
    return "%s.%s" % (m.group(1), m.group(2)) if m else None


def ssl_kontext(ca):
    return ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()


def zjisti_verzi(url, token, ca):
    """IP Fabric vraci verzi na /api/version (zkusime i s tokenem)."""
    hlavicky = {"Accept": "application/json"}
    if token:
        hlavicky["X-API-Token"] = token
    try:
        req = urllib.request.Request(url.rstrip("/") + "/api/version", headers=hlavicky)
        with urllib.request.urlopen(req, timeout=15, context=ssl_kontext(ca)) as r:
            data = json.loads(r.read().decode("utf-8"))
        return data.get("releaseVersion") or data.get("apiVersion")
    except Exception as e:  # sit, TLS, prava - verzi pak zada clovek
        print("   verzi se nepodarilo zjistit automaticky: %s" % e)
        return None


def muze_cist_snapshoty(url, token, user, pwd, ca):
    """Rezim 'local' (plugin si snimky taha sam) potrebuje pravo na tabulku snapshotu."""
    telo = json.dumps({"columns": ["id"], "limit": 1}).encode()
    hlavicky = {"Content-Type": "application/json"}
    if token:
        hlavicky["X-API-Token"] = token
    else:
        try:
            req = urllib.request.Request(url.rstrip("/") + "/api/auth/login",
                                         data=json.dumps({"username": user, "password": pwd}).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15, context=ssl_kontext(ca)) as r:
                cookie = "; ".join(c.split(";", 1)[0] for c in r.headers.get_all("Set-Cookie") or [])
            hlavicky["Cookie"] = cookie
        except Exception:
            return False
    try:
        req = urllib.request.Request(url.rstrip("/") + "/api/tables/management/snapshots", data=telo, headers=hlavicky)
        with urllib.request.urlopen(req, timeout=15, context=ssl_kontext(ca)) as r:
            return r.status == 200
    except Exception:
        return False


def sdk_v_obrazu(image):
    r = run(["podman", "run", "--rm", "--network", "none", "--entrypoint", "/opt/netbox/venv/bin/python",
             image, "-c", "import ipfabric; print(ipfabric.__version__)"], capture=True, check=False)
    return r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else None


def priprav_obraz(zaklad, verze):
    """Vrati obraz se SDK pro danou verzi; kdyz je potreba, postavi ho offline z wheelu."""
    if major_minor(sdk_v_obrazu(zaklad)) == verze:
        return zaklad
    cil = "%s-ipf%s" % (zaklad, verze)
    if run(["podman", "image", "exists", cil], check=False).returncode == 0 and major_minor(sdk_v_obrazu(cil)) == verze:
        return cil
    m = int(verze.split(".")[1])
    spec = "ipfabric>=%s.0,<7.%d.0" % (verze, m + 1)
    info("stavim %s (SDK %s, bez internetu)" % (cil, spec))
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "Containerfile"), "w") as f:
            f.write("FROM %s\n" % zaklad)
            f.write("RUN /usr/local/bin/uv pip install --no-index --find-links /opt/ipfabric-wheels '%s' \\\n" % spec)
            f.write(" && /opt/netbox/venv/bin/python -c 'import ipfabric, ipfabric_netbox; print(ipfabric.__version__)'"
                    " > /opt/ipfabric-wheels/INSTALLED\n")
        run(["podman", "build", "--pull=never", "--network", "none", "-t", cil, "-f", os.path.join(d, "Containerfile"), d])
    nova = sdk_v_obrazu(cil)
    if major_minor(nova) != verze:
        chyba("v obrazu %s je SDK %s, ocekavano %s" % (cil, nova, verze))
    return cil


def nastav_quadlety(image):
    zmeneno = False
    for q in QUADLETS:
        if not os.path.exists(q):
            chyba("chybi %s - nejdriv spustte deploy/install.sh" % q)
        text = open(q, encoding="utf-8").read()
        novy = re.sub(r"(?m)^Image=.*$", "Image=" + image, text)
        if novy != text:
            open(q, "w", encoding="utf-8").write(novy)
            zmeneno = True
    if zmeneno:
        run(["systemctl", "daemon-reload"])


def priprav_ca(ca_soubor):
    """Systemove certifikaty + CA IP Fabricu do jednoho souboru, ktery vidi kontejnery."""
    systemovy = next((p for p in SYSTEM_CA if os.path.exists(p)), None)
    with open(CA_BUNDLE, "w", encoding="utf-8") as out:
        if systemovy:
            out.write(open(systemovy, encoding="utf-8").read().rstrip("\n") + "\n")
        if ca_soubor:
            out.write(open(ca_soubor, encoding="utf-8").read().rstrip("\n") + "\n")
    os.chmod(CA_BUNDLE, 0o644)


def pockej_na_netbox():
    for _ in range(90):
        if run(["podman", "healthcheck", "run", "netbox"], check=False, capture=True).returncode == 0:
            return
        time.sleep(10)
    chyba("NetBox neni zdravy, viz: journalctl -u netbox -n 200")


def nastav_zdroj(conf, sec):
    """Zdroj v pluginu (IP Fabric -> Sources), test spojeni pres SDK pluginu a nacteni snimku."""
    auth = sec.get("IPF_TOKEN") or [sec.get("IPF_USER", ""), sec.get("IPF_PASS", "")]
    params = {"auth": auth, "timeout": 30, "verify": CA_IN_CONTAINER if conf.get("IPF_CA") else True}
    kod = """
import json, os, ipfabric
from django.utils.module_loading import import_string
from core.models import Job
from ipfabric_netbox.models import IPFabricSource
from ipfabric_netbox.utilities.ipfutils import IPFabric
d = json.loads(os.environ["IPF_SRC"])
src = IPFabricSource.objects.filter(name=d["name"]).first() or IPFabricSource(name=d["name"])
src.url = d["url"].rstrip("/")
src.type = d["type"]
src.parameters = d["parameters"]
src.full_clean()
src.save()
print("zdroj IP Fabric v NetBoxu:", src.name, src.url, src.type)
try:
    ipf = IPFabric(parameters=dict(src.parameters, base_url=src.url)).ipf
    print("SPOJENI OK: server", getattr(ipf, "os_version", "?"), "| SDK", ipfabric.__version__,
          "| snimku", len([k for k in ipf.snapshots if not k.startswith("$")]))
except Exception as e:
    print("SPOJENI SELHALO:", type(e).__name__, str(e)[:300])
else:
    if src.type == "local":
        src.status = "queued"
        IPFabricSource.objects.filter(pk=src.pk).update(status="queued")
        Job.enqueue(import_string("ipfabric_netbox.jobs.sync_ipfabricsource"),
                    name=f"{src.name} Snapshot Sync", instance=src, user=None)
        print("NACITANI SNIMKU zarazeno")
"""
    data = json.dumps({"name": conf["IPF_SOURCE_NAME"], "url": conf["IPF_URL"],
                       "type": conf["IPF_SOURCE_TYPE"], "parameters": params})
    r = run(["podman", "exec", "-i", "-e", "IPF_SRC=" + data, "netbox",
             "/opt/netbox/netbox/manage.py", "shell"], stdin=kod, capture=True)
    vystup = "\n".join(l for l in r.stdout.splitlines() if not l.startswith(("🧬", "/opt/netbox", "  warn")))
    print(vystup)
    if "SPOJENI SELHALO" in vystup:
        print("""
POZOR: NetBox se na IP Fabric nepripojil, import dat z IP Fabricu nepobezi.
Zkontrolujte URL, ucet/token, CA certifikat a pruchod firewallem z RHEL9 na IP Fabric (443),
pak spustte konfigurator znovu (--apply staci, kdyz se nastaveni nemeni).""")
        return False
    if "NACITANI SNIMKU" in vystup:
        info("cekam na nacteni snimku z IP Fabricu")
        dotaz = ("from ipfabric_netbox.models import IPFabricSource as S; s=S.objects.get(name=%r); "
                 "print('STAV', s.status, s.snapshots.count())" % conf["IPF_SOURCE_NAME"])
        for _ in range(30):
            time.sleep(10)
            r = run(["podman", "exec", "netbox", "/opt/netbox/netbox/manage.py", "shell", "-c", dotaz],
                    capture=True, check=False)
            stav = [l for l in r.stdout.splitlines() if l.startswith("STAV")]
            if stav and stav[-1].split()[1] in ("completed", "failed", "timeout"):
                print("   " + stav[-1].replace("STAV", "zdroj:") + " snimku v NetBoxu")
                return stav[-1].split()[1] == "completed"
        print("   nacitani jeste bezi, stav viz IP Fabric -> Sources")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="bez dotazu pouzit ulozene nastaveni")
    args = ap.parse_args()
    if os.geteuid() != 0:
        chyba("spustte jako root (sudo)")

    versions = nacti_env(DEST + "/versions.env")
    zaklad = versions.get("NETBOX_IMAGE", "localhost/netbox-ipfabric:4.6.10")
    conf = nacti_env(CONF)
    sec = nacti_env(NETBOX_ENV)

    if args.apply:
        if not conf.get("IPF_VERSION"):
            print("IP Fabric jeste neni nakonfigurovany (%s chybi), preskakuji." % CONF)
            return
    else:
        print("Konfigurace napojeni na IP Fabric. Enter = ponechat hodnotu v hranatych zavorkach.\n")
        url = zeptej("URL IP Fabricu (napr. https://ipfabric.szdc.cz)", conf.get("IPF_URL") or sec.get("IPF_URL", ""))
        if not url.startswith("http"):
            url = "https://" + url
        ca = zeptej("Soubor s CA certifikatem IP Fabricu (interni CA; '-' = systemove certifikaty)",
                    conf.get("IPF_CA") or "-")
        ca = "" if ca == "-" else ca
        if ca and not os.path.exists(ca):
            chyba("soubor %s neexistuje" % ca)
        if ca and os.path.abspath(ca) != CA_IPF:
            shutil.copyfile(ca, CA_IPF)  # kopie, aby --apply fungovalo i po smazani originalu
            ca = CA_IPF
        token = zeptej("API token IP Fabricu pro plugin (Enter = pouzit jmeno a heslo)", sec.get("IPF_TOKEN", ""), tajne=True)
        user = zeptej("Uzivatel IP Fabricu (pro skripty kontroly matice)", sec.get("IPF_USER", ""))
        pwd = zeptej("Heslo", sec.get("IPF_PASS", ""), tajne=True)

        info("zjistuji verzi IP Fabricu")
        zjistena = major_minor(zjisti_verzi(url, token, ca or None))
        if zjistena:
            print("   server hlasi verzi %s" % zjistena)
        verze = major_minor(zeptej("Verze IP Fabricu (major.minor, SZ ma 7.5)",
                                   zjistena or conf.get("IPF_VERSION", "7.5")))
        if verze not in PODPOROVANE:
            chyba("verze %s neni podporovana pluginem ipfabric_netbox 6.1.0 (podporovane: %s)"
                  % (verze, ", ".join(PODPOROVANE)))

        info("overuji pravo cist snapshoty")
        local = muze_cist_snapshoty(url, token, user, pwd, ca or None)
        print("   %s" % ("ano: zdroj v rezimu local (plugin taha snimky sam)" if local else
                         "ne: zdroj v rezimu remote (data vklada push_ipf_data.py)"))
        conf = {
            "IPF_URL": url,
            "IPF_VERSION": verze,
            "IPF_CA": ca,
            "IPF_SOURCE_NAME": zeptej("Nazev zdroje v NetBoxu", conf.get("IPF_SOURCE_NAME") or re.sub(r"^https?://", "", url).rstrip("/")),
            "IPF_SOURCE_TYPE": "local" if local else "remote",
        }
        sec = {"IPF_URL": url, "IPF_USER": user, "IPF_PASS": pwd, "IPF_TOKEN": token,
               "IPF_SOURCE_NAME": conf["IPF_SOURCE_NAME"]}
        if ca:
            sec.update({"SSL_CERT_FILE": CA_IN_CONTAINER, "REQUESTS_CA_BUNDLE": CA_IN_CONTAINER})
        zapis_env(CONF, conf, 0o644)
        zapis_env(NETBOX_ENV, sec)
        host = dict(sec)
        host.pop("SSL_CERT_FILE", None)
        host.pop("REQUESTS_CA_BUNDLE", None)
        if ca:
            host["SSL_CERT_FILE"] = CA_BUNDLE
        host.setdefault("NETBOX_URL", "http://127.0.0.1:%s" % versions.get("NETBOX_PORT", "8000"))
        zapis_env(HOST_ENV, host)

    priprav_ca(conf.get("IPF_CA"))
    image = priprav_obraz(zaklad, conf["IPF_VERSION"])
    nastav_quadlety(image)
    info("restartuji NetBox (%s)" % image)
    run(["systemctl", "restart", "netbox.service", "netbox-worker.service"])
    pockej_na_netbox()
    spojeni = nastav_zdroj(conf, nacti_env(NETBOX_ENV))

    if not spojeni:
        sys.exit(2)
    print("""
Hotovo. IP Fabric %(IPF_VERSION)s, SDK v obrazu %(sdk)s, zdroj "%(IPF_SOURCE_NAME)s" (%(IPF_SOURCE_TYPE)s).
Import dat: v NetBoxu IP Fabric -> Syncs -> Add (zdroj, snimek, co importovat) a Run; plugin vytvori
vetev (branching), ze ktere se po kontrole zmeny slouci. Potom
/opt/netbox-offline/deploy/install-commatrix.sh a kontrola matice v Customization -> Scripts.""" %
          dict(conf, sdk=sdk_v_obrazu(image)))


if __name__ == "__main__":
    main()
