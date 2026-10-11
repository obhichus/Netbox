# Source: assistant message 549 at 2026-09-15T22:08:16.520392Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from ipfabric_netbox.models import IPFabricSync
from users.models import User
s = IPFabricSync.objects.first()
u = User.objects.filter(is_superuser=True).order_by('pk').first()
print('thread_count:', s.thread_count, '| job:', s.enqueue_sync_job(adhoc=True, user=u))
