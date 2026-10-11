# Source: assistant message 545 at 2026-09-15T22:05:13.736971Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from ipfabric_netbox.models import IPFabricSync
s = IPFabricSync.objects.first()
print('pred:', s.thread_count)
s.thread_count = 4
s.save(update_fields=['thread_count'])
print('po:', s.thread_count)
