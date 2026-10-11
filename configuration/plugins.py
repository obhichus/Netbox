# Pluginy NetBoxu: IP Fabric a jeho povinna zavislost netbox_branching.
# Soubor se nacita z /etc/netbox/config/ (je v obrazu a na RHEL9 se primountuje
# z /opt/netbox-offline/configuration/plugins.py, aby sel upravit bez prestaveni).

from netbox.configuration.configuration import DATABASES as _DATABASES
from netbox_branching.utilities import DynamicSchemaDict

# netbox_branching potrebuje vlastni router databaze kvuli vetvim ingesce.
DATABASES = DynamicSchemaDict(_DATABASES)
DATABASE_ROUTERS = ["netbox_branching.database.BranchAwareRouter"]

# netbox_branching musi byt v seznamu posledni.
PLUGINS = [
    "ipfabric_netbox",
    "netbox_branching",
]

PLUGINS_CONFIG = {}
