# Reference z původní instalace

Podklady z původního stroje (Ubuntu 24.04, `/opt/netbox-docker` = netbox-docker 5.0.2, docker compose),
zrekonstruované z pracovní session 4.–18. 9. 2026. Nic z toho se na RHEL9 nespouští automaticky.

| Kde | Co |
|---|---|
| `REKONSTRUKCE.md` | jak bylo vše nainstalováno a nastaveno, krok za krokem, a co se nepodařilo zrekonstruovat |
| `puvodni-netbox-docker/` | `Dockerfile-Plugins`, `docker-compose.override.yml` (vč. Batfish), `plugin_requirements.txt`, `plugins.py`, `README.txt` (provozní příručka, 18 kapitol) |
| `db-kroky/` | `manage.py shell` bloky, které měnily databázi, v pořadí: zdroj IP Fabricu, API token, `ENFORCE_GLOBAL_UNIQUE`, úpravy transform map, sync, úklidy, registrace skriptů, dashboard, retence |
| `ubuntu-host/` | `daemon.json` (DNS pro build), monitor LTE linky `linkmon` |

Hesla a tokeny jsou nahrazená zástupnými hodnotami (`<IPF_USER>`, `<POSTGRES_PASSWORD>` …).
Při přenosu dat přes `migrate/` jsou všechna nastavení z `db-kroky/` už v databázi a znovu se nespouští.
Na čisté instalaci bez přenesených dat je potřeba projít kroky 01, 03, 05, 06, 15 (zdroj, unikátnost
adres, transform mapy, sync).
