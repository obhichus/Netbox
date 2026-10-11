# Source: assistant message 419 at 2026-09-06T18:40:00.685290Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from ipam.models import VRF
from collections import defaultdict
skupiny = defaultdict(list)
for v in VRF.objects.order_by('pk'):
    skupiny[(v.name, v.rd)].append(v)
ids = [v.pk for g in skupiny.values() for v in g[1:]]
print('mazu zaznamu:', len(ids))
VRF.objects.filter(pk__in=ids).delete()
print('VRF po uklidu:', VRF.objects.count())
