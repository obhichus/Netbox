# Source: assistant message 447 at 2026-09-06T19:10:10.241388Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from ipfabric_netbox.models import IPFabricSync
from users.models import User
s = IPFabricSync.objects.get(name='pokus1')
u = User.objects.filter(is_superuser=True).order_by('pk').first()
job = s.enqueue_sync_job(adhoc=True, user=u)
print('job:', job)
