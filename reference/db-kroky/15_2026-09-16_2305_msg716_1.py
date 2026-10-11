# Source: assistant message 716 at 2026-09-16T23:05:00.442182Z (transcript of session cse_01SNqXzLEe473wav99T37xVt)
# Run: cd /opt/netbox-docker && docker compose exec -T netbox /opt/netbox/netbox/manage.py shell < THIS_FILE
# Applied-by-user status: see NOTES.md

from ipfabric_netbox.models import IPFabricTransformMap
tm_dev = [t for t in IPFabricTransformMap.objects.all() if t.target_model.model == 'device'][0]
fm = tm_dev.field_maps.get(target_field='name')
fm.source_field, fm.template = '', '{{ object.nb_name }}'
fm.save()
fm = tm_dev.field_maps.get(target_field='serial')
fm.template = '{{ object.nb_serial }}'
fm.save()

tm_int = [t for t in IPFabricTransformMap.objects.all() if t.target_model.model == 'interface'][0]
rm = tm_int.relationship_maps.get(target_field='device')
rm.template = '{{ dcim.Device.objects.get(serial=object.nb_serial).pk }}'
rm.save()

for t in [x for x in IPFabricTransformMap.objects.all() if x.target_model.model == 'ipaddress']:
    f = t.field_maps.filter(target_field='assigned_object_id').first()
    if f:
        f.template = ('{% set NAME = object.nameOriginal or object.intName %}'
                      '{{ dcim.Interface.objects.filter(device__serial=object.nb_serial, name=NAME).first().pk }}')
        f.save()
print('mapy prepsany')
for t in (tm_dev, tm_int):
    print(t, '| required:', sorted(t.get_required_source_columns()))
