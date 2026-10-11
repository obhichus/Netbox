# Source: assistant message 547 at 2026-09-15T22:06:19.221719Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from netbox_branching.models import Branch
from dcim.models import Device
print('zarizeni pred:', Device.objects.count())
for b in Branch.objects.order_by('pk'):
    print('mazu', b.pk, b.status)
    b.delete()
print('vetvi zbylo:', Branch.objects.count(), '| zarizeni po:', Device.objects.count())
