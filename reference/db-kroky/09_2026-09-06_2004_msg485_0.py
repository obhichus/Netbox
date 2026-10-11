# Source: assistant message 485 at 2026-09-06T20:04:17.698103Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from ipfabric_netbox.models import IPFabricSource, IPFabricSync
z = IPFabricSource.objects.get(name='demo')
z.name = 'guided-demo.eu.ipfabric.io'
z.description = 'IP Fabric 7.9.4, rezim remote - data vklada push_ipf_data.py'
z.save(update_fields=['name', 'description'])
s = IPFabricSync.objects.get(name='pokus1')
s.name = 'Import celeho snapshotu'
s.save(update_fields=['name'])
print('zdroj:', z.name, '|', z.description)
print('sync :', s.name)
