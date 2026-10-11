# Source: assistant message 788 at 2026-09-17T11:41:12.345482Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from extras.models import ScriptModule, Script
m, novy = ScriptModule.objects.get_or_create(file_root='scripts', file_path='fw_prehled_script.py')
print('modul:', m.pk, '| nove vytvoren:', novy)
for s in Script.objects.all().order_by('pk'):
    print('  ', s.pk, '|', s.name, '| modul:', s.module_id)
