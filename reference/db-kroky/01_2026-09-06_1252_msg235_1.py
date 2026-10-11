# Source: assistant message 235 at 2026-09-06T12:52:34.420151Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from ipfabric_netbox.models import IPFabricSource
usr = '<IPF_USER>'
pwd = 'NOVE_HESLO'
src = IPFabricSource.objects.get(name='demo')
src.parameters = {'auth': [usr, pwd], 'timeout': 30}
src.save()
print('parametry:', sorted(src.parameters.keys()))
