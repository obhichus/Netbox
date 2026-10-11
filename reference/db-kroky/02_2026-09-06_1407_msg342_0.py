# Source: assistant message 342 at 2026-09-06T14:07:26.831896Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md


from django.contrib.auth import get_user_model
from users.models import Token
u = get_user_model().objects.get(username='admin')
t = Token.objects.create(user=u, write_enabled=True, description='ipf import')
print(t.key)

