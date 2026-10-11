# Source: assistant message 439 at 2026-09-06T19:02:02.501058Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from ipfabric_netbox.models import IPFabricSync
from ipfabric_netbox.choices import IPFabricSyncStatusChoices
s = IPFabricSync.objects.get(name='pokus1')
print('pred:', s.status, '| auto_merge:', s.auto_merge)
s.status = IPFabricSyncStatusChoices.COMPLETED
s.auto_merge = True
s.save(update_fields=['status', 'auto_merge'])
s.refresh_from_db()
print('po:', s.status, '| auto_merge:', s.auto_merge)
