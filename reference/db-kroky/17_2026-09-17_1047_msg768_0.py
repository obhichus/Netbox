# Source: assistant message 768 at 2026-09-17T10:47:31.990043Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

import uuid
from extras.models import Dashboard
from users.models import User

u = User.objects.get(username='admin')

stara = Dashboard.objects.filter(user=u).first()
if stara:
    print('stavajici layout:', stara.layout)
    print('stavajici config klice:', list(stara.config.keys())[:3])
    print('ukazka widgetu:', list(stara.config.values())[0] if stara.config else None)
    print('---')

MODELY = ['dcim.site', 'dcim.device', 'dcim.devicetype', 'dcim.interface',
          'ipam.ipaddress', 'ipam.prefix', 'ipam.vlan', 'ipam.vrf']
POPIS = [{
    'widget': 'extras.ObjectCountsWidget',
    'width': 12,
    'height': 4,
    'title': 'Sit naimportovana z IP Fabricu',
    'config': {'models': MODELY},
}]

nova = None
try:
    from extras.dashboard.utils import get_default_dashboard
    nova = get_default_dashboard(config=POPIS)
    print('pouzita tovarni metoda get_default_dashboard')
except Exception as e:
    print('get_default_dashboard nepouzitelna:', type(e).__name__, e)
    kluc = str(uuid.uuid4())
    nova = Dashboard(
        layout=[{'id': kluc, 'w': 12, 'h': 4, 'x': 0, 'y': 0}],
        config={kluc: {'class': 'extras.ObjectCountsWidget',
                       'title': 'Sit naimportovana z IP Fabricu',
                       'color': None,
                       'config': {'models': MODELY}}},
    )
    print('sestaveno rucne')

Dashboard.objects.filter(user=u).delete()
nova.pk = None
nova.user = u
nova.save()

kontrola = Dashboard.objects.get(user=u)
print('\nulozeno pro uzivatele:', u.username)
print('widgetu na nastence:', len(kontrola.layout))
print('layout:', kontrola.layout)
print('config:', kontrola.config)
