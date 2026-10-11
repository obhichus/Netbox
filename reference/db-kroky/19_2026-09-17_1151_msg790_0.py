# Source: assistant message 790 at 2026-09-17T11:51:36.989758Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

import uuid
from extras.models import Dashboard, Script
from users.models import User

print('dostupne skripty:')
for s in Script.objects.all().order_by('pk'):
    print(f'   {s.pk}  {s.name}')

hledane = [
    ('KontrolaKomunikacniMaticeV2', 'Kontrola komunikační matice'),
    ('PrehledFirewallovychPravidel', 'Přehled firewallových pravidel'),
]
odkazy = []
for nazev_tridy, popisek in hledane:
    s = Script.objects.filter(name=nazev_tridy).first()
    if s:
        odkazy.append(f'### [{popisek}](/extras/scripts/{s.pk}/)')
    else:
        print(f'VAROVANI: skript {nazev_tridy} nenalezen')

obsah = '\n\n'.join(odkazy) if odkazy else '_Žádný skript nenalezen._'

d = Dashboard.objects.get(user=User.objects.get(username='admin'))
for klic, w in list(d.config.items()):
    if w.get('title') == 'Kontroly':
        d.layout = [x for x in d.layout if x['id'] != klic]
        del d.config[klic]

klic = str(uuid.uuid4())
d.layout.insert(1, {'h': 3, 'w': 12, 'x': None, 'y': None, 'id': klic})
d.config[klic] = {
    'class': 'extras.NoteWidget',
    'color': 'green',
    'title': 'Kontroly',
    'config': {'content': obsah},
}
d.save()

print('\nwidgety na nastence:')
for w in d.layout:
    print('   ', d.config[w['id']]['class'], '|', d.config[w['id']]['title'])
