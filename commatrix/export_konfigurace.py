"""Export konfigurace NetBoxu, ktera existuje jen v databazi.

Spusteni:
    cd /opt/netbox-docker
    docker compose exec -T netbox \
      /opt/netbox/netbox/manage.py shell < /opt/commatrix/export_konfigurace.py

Vysledek vyzvedni z kontejneru:
    docker compose cp netbox:/opt/netbox/netbox/media/export-konfigurace ./export-konfigurace

Exportuje:
    transformacni mapy pluginu ipfabric_netbox (vcetne poli a relaci)
    registrovane NetBox Scripty
    rozlozeni nastenek
    aktivni konfiguracni revizi

Zamerne NEEXPORTUJE IPFabricSource (obsahuje pristupove udaje),
IPFabricData, IPFabricSnapshot, IPFabricSync, IPFabricIngestion
a IPFabricIngestionIssue (provozni data, nikoli konfigurace).
"""

import json
import pathlib

from django.apps import apps
from django.core import serializers

CIL = pathlib.Path("/opt/netbox/netbox/media/export-konfigurace")
CIL.mkdir(parents=True, exist_ok=True)

VYNECHAT = {
    "ipfabricsource",
    "ipfabricdata",
    "ipfabricsnapshot",
    "ipfabricsync",
    "ipfabricingestion",
    "ipfabricingestionissue",
}

CITLIVE = ("PASSWORD", "SECRET", "TOKEN", "KEY", "CREDENTIAL")


def zapis(nazev, data):
    cesta = CIL / nazev
    cesta.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    print(f"  {cesta.name}")


print("transformacni mapy pluginu:")
try:
    konfigurace = apps.get_app_config("ipfabric_netbox")
except LookupError:
    print("  plugin ipfabric_netbox neni nainstalovan, preskakuji")
else:
    for model in konfigurace.get_models():
        nazev = model._meta.model_name
        if nazev in VYNECHAT:
            continue
        objekty = list(model.objects.all())
        if not objekty:
            continue
        text = serializers.serialize("json", objekty, indent=2)
        (CIL / f"plugin-{nazev}.json").write_text(text)
        print(f"  plugin-{nazev}.json ({len(objekty)})")

print("registrovane skripty:")
from extras.models import Script, ScriptModule  # noqa: E402

zapis(
    "skripty.json",
    [
        {
            "file_root": m.file_root,
            "file_path": m.file_path,
            "skripty": sorted(Script.objects.filter(module=m).values_list("name", flat=True)),
        }
        for m in ScriptModule.objects.all()
    ],
)

print("nastenky:")
from extras.models import Dashboard  # noqa: E402

zapis(
    "nastenky.json",
    [
        {"uzivatel": d.user.username, "layout": d.layout, "config": d.config}
        for d in Dashboard.objects.select_related("user")
    ],
)

print("konfiguracni revize:")
from core.models import ConfigRevision  # noqa: E402

revize = ConfigRevision.objects.order_by("-created").first()
if revize is None:
    print("  zadna revize neexistuje, plati vychozi hodnoty")
else:
    data = {
        k: v
        for k, v in revize.data.items()
        if not any(slovo in k.upper() for slovo in CITLIVE)
    }
    vynechano = sorted(set(revize.data) - set(data))
    zapis(
        "konfiguracni-revize.json",
        {
            "created": revize.created,
            "comment": revize.comment,
            "data": data,
            "vynechane_citlive_klice": vynechano,
        },
    )
    if vynechano:
        print(f"  vynechano jako citlive: {', '.join(vynechano)}")

print()
print(f"hotovo, vystup v {CIL}")
