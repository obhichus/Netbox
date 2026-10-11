# Doplnkova konfigurace NetBoxu (nacita se z /etc/netbox/config/extra.py).

# Ingesce velkeho snimku IP Fabricu trva i 25 minut; vychozich 300 s nestaci.
RQ_DEFAULT_TIMEOUT = 7200

# Offline instalace: zadna kontrola novych verzi na GitHubu.
RELEASE_CHECK_URL = None
