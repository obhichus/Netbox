# Source: assistant message 431 at 2026-09-06T18:54:25.880813Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from ipfabric_netbox.models import IPFabricTransformMap
tm_int = [t for t in IPFabricTransformMap.objects.all() if t.target_model.model == 'interface'][0]
rm = tm_int.relationship_maps.get(target_field='device')
rm.template = '{% set SN = object.stackMemberSn or object.sn %}{% if SN and SN|length < 50 %}{{ dcim.Device.objects.get(serial=SN).pk }}{% else %}{{ dcim.Device.objects.get(name=object.hostname).pk }}{% endif %}'
rm.save()
print('interface REL device:', rm.template)

tm_ip = [t for t in IPFabricTransformMap.objects.all() if t.target_model.model == 'ipaddress']
for t in tm_ip:
    fm = t.field_maps.filter(target_field='assigned_object_id').first()
    if not fm:
        continue
    fm.template = '{% set NAME = object.nameOriginal or object.intName %}{% if object.sn and object.sn|length < 50 %}{{ dcim.Interface.objects.filter(device__serial=object.sn, name=NAME).first().pk }}{% else %}{{ dcim.Interface.objects.filter(device__name=object.hostname, name=NAME).first().pk }}{% endif %}'
    fm.save()
    print(t, '-> FM assigned_object_id prepsan')

for t in [tm_int] + list(tm_ip):
    print(t, '| required cols:', sorted(t.get_required_source_columns()))
