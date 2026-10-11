# Source: assistant message 798 at 2026-09-18T07:58:43.316188Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from core.models import ConfigRevision
from netbox.config import get_config, clear_config

posledni = ConfigRevision.objects.order_by('-created').first()
data = dict(posledni.data) if posledni else {}
data['CHANGELOG_RETENTION'] = 0
data['JOB_RETENTION'] = 0

rev = ConfigRevision.objects.create(
    comment='Historie zmen i behu se neuchovava casove omezene - nemazat',
    data=data)
rev.activate()
clear_config()

novy = get_config()
print('CHANGELOG_RETENTION:', novy.CHANGELOG_RETENTION, '(0 = nemazat)')
print('JOB_RETENTION:', novy.JOB_RETENTION, '(0 = nemazat)')
print('revize:', rev.pk)
