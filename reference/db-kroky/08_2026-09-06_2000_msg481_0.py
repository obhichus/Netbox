# Source: assistant message 481 at 2026-09-06T20:00:26.734339Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from ipfabric_netbox.models import IPFabricSource
from ipfabric_netbox.choices import IPFabricSourceStatusChoices
s = IPFabricSource.objects.get(name='demo')
print('pred:', s.status)
s.status = IPFabricSourceStatusChoices.COMPLETED
s.description = 'Rezim remote - data se vkladaji skriptem push_ipf_data.py'
s.save(update_fields=['status', 'description'])
s.refresh_from_db()
print('po:', s.status, '|', s.description)
