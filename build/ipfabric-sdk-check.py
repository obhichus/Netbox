"""Overi, ze SDK ipfabric v obrazu jde pouzit: vytvori klienta proti nedostupne adrese.
Chyba spojeni je v poradku, jakakoli jina (import, pydantic, ...) znamena nefunkcni SDK.
V obrazu jako /opt/ipfabric-wheels/check.py."""
import sys

import ipfabric
from ipfabric import IPFClient

try:
    IPFClient(base_url="http://127.0.0.1:9", auth="x", unloaded=True, timeout=1)
except Exception as e:  # noqa: BLE001
    if not (isinstance(e, OSError) or "connect" in type(e).__name__.lower()):
        print("SDK %s NEFUNKCNI: %s: %s" % (ipfabric.__version__, type(e).__name__, str(e)[:200]))
        sys.exit(1)
print("SDK %s OK" % ipfabric.__version__)
