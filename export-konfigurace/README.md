# export-konfigurace

Sem patří JSONy z [commatrix/export_konfigurace.py](../commatrix/export_konfigurace.py): konfigurace
NetBoxu, která existuje jen v databázi (transformační mapy pluginu ipfabric_netbox, registrované
NetBox Scripty, rozložení nástěnek, aktivní konfigurační revize). Bez nich není obnova od nuly úplná.

```sh
cd /opt/netbox-docker
docker compose exec -T netbox \
  /opt/netbox/netbox/manage.py shell < /opt/commatrix/export_konfigurace.py
docker compose cp netbox:/opt/netbox/netbox/media/export-konfigurace ./export-konfigurace
```

Na RHEL9: `deploy/nb-shell.sh /opt/commatrix/export_konfigurace.py`, výstup je ve svazku media
(`/opt/netbox/netbox/media/export-konfigurace` v kontejneru).

Skript záměrně neexportuje `IPFabricSource` (přístupové údaje) ani provozní data (data, snímky,
synchronizace, ingesce) a z konfigurační revize vynechá klíče s PASSWORD/SECRET/TOKEN/KEY/CREDENTIAL.
Před commitem přesto zkontroluj, že v JSONech nejsou hesla ani tokeny.

Stav: skript je v repu, **JSONy zatím ne** (čeká se na spuštění na Ubuntu stroji).
