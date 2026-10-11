#!/usr/bin/env bash
# Zalozi administratora NetBoxu (na novem serveru bez prenesenych dat).
exec podman exec -it netbox /opt/netbox/netbox/manage.py createsuperuser
