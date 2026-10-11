# Source: assistant message 561 at 2026-09-15T22:45:50.776045Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from dcim.models import Device, Interface
from ipam.models import IPAddress
print('pred:', Device.objects.count(), 'zarizeni |', Interface.objects.count(), 'rozhrani |', IPAddress.objects.count(), 'IP')
stare = [d.pk for d in Device.objects.all() if d.custom_field_data.get('ipfabric_ingestion') != 15]
print('mazu zarizeni:', len(stare))
Device.objects.filter(pk__in=stare).delete()
print('po:', Device.objects.count(), 'zarizeni |', Interface.objects.count(), 'rozhrani |', IPAddress.objects.count(), 'IP')
