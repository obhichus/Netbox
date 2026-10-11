# Source: assistant message 389 at 2026-09-06T14:39:55.199953Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from core.models import ConfigRevision
from netbox.config import get_config, clear_config
cur = ConfigRevision.objects.order_by('-created').first()
data = dict(cur.data) if cur else {}
data['ENFORCE_GLOBAL_UNIQUE'] = False
rev = ConfigRevision.objects.create(comment='vypnuto kvuli IP Fabric demo datum', data=data)
rev.activate()
clear_config()
print('nova revize:', rev.pk, '/ ENFORCE_GLOBAL_UNIQUE:', get_config().ENFORCE_GLOBAL_UNIQUE)
