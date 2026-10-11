# Source: assistant message 506 at 2026-09-08T13:40:05.016066Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from extras.models import ScriptModule, Script
m, novy = ScriptModule.objects.get_or_create(file_root='scripts', file_path='commatrix_v2.py')
print('modul:', m.pk, '| nove vytvoren:', novy, '|', m.file_path)
print('--- skripty v databazi')
for s in Script.objects.all().order_by('pk'):
    print(' ', s.pk, '|', s.name, '| modul:', s.module_id)
