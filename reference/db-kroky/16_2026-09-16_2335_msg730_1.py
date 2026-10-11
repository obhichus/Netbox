# Source: assistant message 730 at 2026-09-16T23:35:05.223759Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from dcim.models import DeviceType
sirotci = [t.pk for t in DeviceType.objects.all()
           if t.instances.count() == 0 and ('  ' in t.model or t.model != t.model.strip(' -'))]
print('mazu nepouzitych typu:', len(sirotci))
DeviceType.objects.filter(pk__in=sirotci).delete()
print('typu zbylo:', DeviceType.objects.count())
