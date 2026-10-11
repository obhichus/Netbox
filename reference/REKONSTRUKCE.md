# NetBox + IP Fabric + Batfish: files and setup rebuilt from session cse_01SNqXzLEe473wav99T37xVt

Source: every user and assistant event of the session (2026-09-04 19:00 to 2026-09-18 07:58), 62 pages.
Each file was rebuilt by replaying, in time order, the `cat > file <<EOF` heredocs, the `python3 - <<'PY'` patch blocks and the `sed -i` edits from the transcript. Every patch block's own `assert`/"usek nenalezen" check passed during the replay. Every `.py` file parses.

**Secrets are NOT included.** Real passwords and tokens are replaced with `<PLACEHOLDER>` values: the IP Fabric user and password, the Postgres, Redis and Redis-cache passwords, SECRET_KEY, the NetBox API token and the admin password. The real values were either generated on the host with `openssl rand` and never shown, or were pasted into chat (IP Fabric login). See "Credentials" below.

## 1. Files (paths mirror the target host)

| Extracted file | Status / origin |
|---|---|
| opt/netbox-docker/Dockerfile-Plugins | exact: user `cat` output 2026-09-05 (508 B, matches host size) |
| opt/netbox-docker/docker-compose.override.yml | final 2026-09-05 21:05, verified applied (all services `restart: unless-stopped`, Batfish included) |
| opt/netbox-docker/plugin_requirements.txt | final 2026-09-06 09:31: `ipfabric_netbox[ipfabric_7_9]` + `netboxlabs-netbox-branching<1.2` (changed from `ipfabric_7_5` because the guided demo runs IPF 7.9.4) |
| opt/netbox-docker/.env | `VERSION=v4.6.10-5.0.2` |
| opt/netbox-docker/configuration/plugins.py | full content as written. DB password placeholder (the real one was set with `sed s/ZMEN_MNE/$PG/`) |
| opt/netbox-docker/configuration/extra.py | upstream netbox-docker 5.0.2 file (unchanged by the session) plus the one line the session appended: `RQ_DEFAULT_TIMEOUT = 7200` (2026-09-15, verified 7200) |
| opt/netbox-docker/env/*.env | **template**: upstream 5.0.2 env files with the session's changes applied (passwords, appended IPF_* vars, `RQ_DEFAULT_TIMEOUT=7200`). Secrets replaced with placeholders |
| opt/netbox-docker/README.txt | v2 (17 chapters, 2026-09-06 13:53, user told to replace whole file) + chapter 18 appended 19:14 ("Import dat z IP Fabric do NetBoxu") |
| opt/commatrix/push_ipf_data.py | 357 heredoc + 6 later edits (normalizuj(), `rd` removed from text columns, default source name `guided-demo.eu.ipfabric.io`, `IPF_DUMP_DIR`/`IPF_LOAD_DIR` offline mode, VLAN-ID>=1 filter, `nb_serial`/`nb_name` computation) |
| opt/commatrix/commatrix_v2.py | NetBox Script "Kontrola komunikační matice — v2 s odkazy na zařízení" (class KontrolaKomunikacniMaticeV2). Edits applied: `cesta` StringVar (FileVar optional), `_log`->`zaloguj` rename, remembers last path and snapshot in `/opt/netbox/netbox/media/matice_posledni.json` |
| opt/commatrix/commatrix_script.py | v1 NetBox Script (class KontrolaKomunikacniMatice, ASCII Czech) = the 2026-09-06 version restored from the container + `cesta` patch 2026-09-08 |
| opt/commatrix/commatrix_check.py, matrix-vzor.csv | the first standalone host script (stdlib, cookie auth to IPF) with its two patches. A different file from the NetBox Script versions |
| opt/commatrix/matice-demo.csv | 36 rows, src changed 10.194.56.83 -> .85 |
| opt/commatrix/matice-demo2.csv | 40 rows, plus 3 later fixes (10.2.254.25->10.192.0.136; L52 src 10.52.98.1; "NTP z L48,10.48.139.136") |
| opt/commatrix/ipf_discover.py, ipf_to_netbox.py | as written 2026-09-06 (ipf_to_netbox.py was the REST-based importer, superseded by plugin + push_ipf_data.py) |
| opt/commatrix/primarni_ip.py (+patch), prefixy.py (final 3rd version) | run via `manage.py shell < file` |
| opt/commatrix/fw_discover.py (+patch), fw_na_matici.py, fw_prehled.py, fw_prehled_script.py | firewall-rule overview work, 2026-09-17. fw_prehled_script.py = NetBox Script "Přehled firewallových pravidel" |
| opt/commatrix/provoz-netbox-ipfabric.txt | operations doc (plain-text version of the web runbook) |
| opt/commatrix/ipf.env | template (chmod 600 on host) |
| etc/docker/daemon.json | `dns 8.8.8.8/1.1.1.1`, `max-concurrent-downloads 1`, `max-download-attempts 10` |
| usr/local/bin/linkmon.sh, etc/systemd/system/linkmon.service | LTE link monitor proposed 2026-09-05. Not confirmed whether the user installed it |
| mnt/user-data/outputs/* | the session-side copies as sent to the user (before host-side edits). Kept for reference |
| setup_snippets/NN_*.py | the `manage.py shell` blocks that changed the database, in order (see section 4) |

## 2. Stack

- Host blue-ThinkCentre-M710s: Ubuntu 24.04 (adresy stroje vynechány).
- `/opt/netbox-docker` is a git checkout of netbox-docker at tag **5.0.2** (detached HEAD 5adc62f).
  - Locally modified tracked files: `configuration/plugins.py`, `env/*.env`.
  - Untracked files: `.env`, `Dockerfile-Plugins`, `plugin_requirements.txt`, `README.txt`, `password.txt`.
- Services:
  - `netbox` and `netbox-worker` use the custom image `netbox:v4.6.10-5.0.2-plugins`, built `FROM netboxcommunity/netbox:v4.6.10-5.0.2`. NetBox 4.6.10, Python 3.14, granian. Port 8000 maps to 8080.
  - Databases and caches: `postgres:18-alpine`, and `valkey/valkey:9.1-alpine` for both `redis` and `redis-cache`.
  - `batfish` runs `batfish/allinone:latest` on ports 8888, 9996 and 9997, with volume `batfish_data:/data`.
  - Every service has `restart: unless-stopped`, set in the override file.
- Volumes: `netbox-docker_batfish_data`, `netbox-media-files`, `netbox-postgres`, `netbox-redis-data`, `netbox-redis-cache-data`, `netbox-reports-files`, `netbox-scripts-files`.
- Plugins: `ipfabric_netbox` 6.1.0 with SDK `ipfabric` 7.9.1 (from extra `ipfabric_7_9`), and `netbox_branching` 1.1.3.
  - Branching is pinned below 1.2 because 1.2.0 needs NetBox 4.7. On 4.7 the build broke in `collectstatic`/GraphQL on `core.Job.execution_time`, which is why the stack was downgraded from 4.7 to 4.6.10.
- Old stack: the hand-written compose in `/opt/fw_stack` (NetBox, Batfish, postgres 15, celery) was replaced, then archived to `/root/fw_stack-archiv-<date>.tar.gz`. MISP volumes on the host belong to the user's boss and must not be deleted.

## 3. How the plugin was installed (in order)

1. `git clone netbox-docker`, then `git checkout 5.0.2`, then `echo VERSION=v4.6.10-5.0.2 > .env`.
2. Create `plugin_requirements.txt`, `Dockerfile-Plugins` (uv install with `UV_HTTP_TIMEOUT=300 UV_CONCURRENT_DOWNLOADS=1`, needed on the slow LTE link), `configuration/plugins.py` (PLUGINS, plus `DynamicSchemaDict` DATABASES and `BranchAwareRouter` for branching), and `docker-compose.override.yml`.
3. Generate secrets: `openssl rand` into `env/postgres.env`, `DB_PASSWORD`, `env/redis*.env`, `SECRET_KEY`, and the `plugins.py` password.
   - Fix found later: `REDIS_PASSWORD` and `REDIS_CACHE_PASSWORD` in `env/netbox.env` must also be synced, otherwise Redis AuthenticationError.
4. Configure Docker: `/etc/docker/daemon.json` (DNS fix for container builds), and change the Docker apt repo from mantic to noble.
5. Build and start: `docker compose build && docker compose up -d`. A retry loop was run with nohup because of the LTE link.
6. On 2026-09-06, switch the plugin extra to `ipfabric_7_9`, then `build` and `up -d` again.

## 4. Setup steps done in NetBox (DB/UI, not files). See setup_snippets/

1. **Create the IP Fabric source**: name `demo`, base_url `https://guided-demo.eu.ipfabric.io`. The only accepted form is `parameters = {'auth': [user, pass] or 'TOKEN', 'timeout': 30}`, because IPFClient accepts only `auth` (snippet 01). The demo account gets 403 on `/api/tables/management/snapshots`, so the source runs in **remote** mode: `push_ipf_data.py` fills `IPFabricData` from inside the container:
   `docker compose exec -T -e IPF_SNAPSHOT=<id> netbox /opt/netbox/netbox/manage.py shell < /opt/commatrix/push_ipf_data.py`
2. **NetBox API token** for the host scripts (snippet 02).
3. **ENFORCE_GLOBAL_UNIQUE = False**, set through a new ConfigRevision because the demo data has duplicate IPs (snippet 03).
4. **Transform map fixes**. The plugin's 14 default maps were changed in the DB:
   - interface->device and ipaddress->assigned_object lookups by serial or hostname (snippet 05)
   - from 2026-09-16, device `name` <- `{{ object.nb_name }}`, `serial` <- `{{ object.nb_serial }}`, and interface/IP lookups by `nb_serial` (snippet 15). This pairs with the `nb_name`/`nb_serial` columns computed in push_ipf_data.py.
   - Cleanup snippets: 04 removes VRF duplicates, 14 removes devices from old ingestions, 16 removes orphan device types.
5. **Sync**: `pokus1` was renamed to "Import celeho snapshotu" and given `auto_merge = True` (snippets 06, 09).
   - Start a sync with `IPFabricSync.objects.first().enqueue_sync_job(adhoc=True, user=<superuser>)` (07, 13).
   - Do not call `branch.merge()` directly. The plugin's merge job closes the state machine.
   - The source was renamed to `guided-demo.eu.ipfabric.io` and its status set to completed with a description (08, 09).
6. **RQ timeout**: `RQ_DEFAULT_TIMEOUT = 7200` in `extra.py` (the env var alone was not read). After that, unfinished branches were deleted (11, 12).
7. **Snapshot 2**: `22443e66-2430-4a55-b953-d7601b3f5148` ("Network Audit Evidence"), 365 devices.
8. **Scripts**:
   - Upload `commatrix_v2.py` and `fw_prehled_script.py` with `docker compose cp` into BOTH `netbox` and `netbox-worker` at `/opt/netbox/netbox/scripts/`, then run `chown netbox:root`.
   - Register them with `ScriptModule.objects.get_or_create(file_root='scripts', file_path=...)` (10, 18), then `docker compose restart netbox netbox-worker`.
   - Copy the CSV matrices the same way. In the form, give the path `/opt/netbox/netbox/scripts/matice-demo2.csv`.
9. **Primary IPs**: `primarni_ip.py` gave 264 of 365 devices a primary IP. Devices with exactly one IPv4 were then set ad hoc. Prefixes come from `prefixy.py`.
10. **Dashboard**: the admin dashboard was rebuilt, with a NoteWidget "Kontroly" linking both scripts (17, 19).
11. **Retention**:
    - The user asked for `CHANGELOG_RETENTION = 0` and `JOB_RETENTION = 0` (0 means never delete), through a new ConfigRevision (snippet 20).
    - **No confirmation in the transcript**: it ends with that command, and the earlier 365/365 command was never run either. Check it in Admin -> Configuration.
    - Baseline at the time: 39,856 changelog rows, 92 jobs, database 123 MB.
12. **Custom fields**: no manual CustomField creation in the session. The plugin's own fields (for example `ipfabric_ingestion` on Device) were used as they came.
13. **Scheduling**: nothing set up. No cron or systemd timer was created for NetBox. The scripts have `scheduling_enabled` and could be scheduled in NetBox, but that was only proposed. The only systemd unit written was `linkmon.service`. A `netbox-build.service` was proposed and declined by the user.

Last verdict tally for the matrix run (matice-demo2, snapshot 2): OK 20, PORUŠENÍ MATICE 8, CHYBÍ PRAVIDLO 2, NEDOSTUPNÉ 10. A run with findings ends with `log_failure`, so NetBox shows "Script failed". This is expected.

## 5. Credentials handling

- `env/*.env`, `configuration/plugins.py` (DB password hard-coded; it must equal `POSTGRES_PASSWORD`) and `password.txt` in `/opt/netbox-docker` (chmod 600 advised) hold the real secrets on the host. README says passwords live in `password.txt`.
- IP Fabric credentials are in three places:
  - `env/netbox.env` as `IPF_URL`, `IPF_USER`, `IPF_PASS`, `IPF_SNAPSHOT`, for scripts inside the container
  - `/opt/commatrix/ipf.env` (chmod 600), together with `NETBOX_URL` and `NETBOX_TOKEN`
  - `/opt/netbox-docker/ipf.env` (an earlier variant)
- They are also stored **in plain text** in `IPFabricSource.parameters` in the database.
- The IP Fabric password was pasted into the chat. The assistant advised changing it. It should be rotated.
- **Security gap**: `API_TOKEN_PEPPER_1` in `env/netbox.env` was never changed and is still the public upstream default. Replace it.
- `SUPERUSER_PASSWORD` was set with sed, but upstream 5.0.2 has no such line (`SKIP_SUPERUSER=true`), so that sed did nothing. The admin login was handled separately (`changepassword admin` was suggested).

## 6. Known issues

- `LOGIN_REQUIRED` FutureWarning on every start. It comes from the config and is harmless.
- The demo IPF account gets 403 on the snapshots table. Because of that, the source shows "failed" unless its status is reset (snippet 08).
- Azure `VNet-Spoke.1` and other names longer than 64 characters failed until the `nb_name` change. IPv6 link-local IPs on IOS interfaces are left unassigned (6 issues, accepted).
- When copying with `docker compose cp`, you must chown and restart, or NetBox gets a PermissionError or uses a stale module.
- The Browse (file upload) button does not work in Firefox snap over RDP (xdg-desktop-portal). This is why the `cesta` path field exists.
- With retention set to 0 the database grows without limit (about 2k changelog rows per import). Watch its size.
- The NetBox branching/plugin ecosystem did not support NetBox 4.7 at the time. To upgrade later, change the tag in `Dockerfile-Plugins` and `.env`, lift the `<1.2` pin, and rebuild.

## 7. What could not be rebuilt exactly, and why

- **env/*.env**: the session never printed the full files. They were changed with `sed`/`>>` on top of upstream 5.0.2. The extracted files are upstream 5.0.2 (fetched from GitHub tag 5.0.2) with those changes replayed and secrets as placeholders.
- **configuration/configuration.py, logging.py, docker-compose.yml**: unchanged upstream 5.0.2, so not included.
- **opt/commatrix/matice-z-firewallu.csv**: generated on the host by `fw_na_matici.py`. Only one `sed '/Allow-VM-traffic/d'` edit is known. Regenerate it with the script.
- **snapshot-22443e66/** JSON dump, `report.csv`, `ipf_prehled.csv`: generated data, not in the transcript.
- **password.txt**: secrets, intentionally not reproduced.
- **README v1** (2026-09-05): fully replaced by v2. Not reproduced.
- **ipf_discover.py**: the user restored an `ipf_discover.py-old` backup after accidentally overwriting the file. The extracted file is the version the session wrote (2026-09-06 13:54), assumed identical to that backup.
- **Web runbooks and pptx** (`/tmp/demo/matice-runbook.html`, `netbox-ipfabric-provoz.html`, `netbox-sz-vedeni.pptx`): session-side artifacts, not host files. Their text equivalent is `provoz-netbox-ipfabric.txt`.
- Whether the user ran each proposed DB snippet: assumed yes where a later user paste shows the effect. The final retention change is unconfirmed (see section 4, step 11).
