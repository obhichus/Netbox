PLUGINS = ["ipfabric_netbox", "netbox_branching"]

from netbox_branching.utilities import DynamicSchemaDict

DATABASES = DynamicSchemaDict({
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'netbox',
        'USER': 'netbox',
        'PASSWORD': '<POSTGRES_PASSWORD>',
        'HOST': 'postgres',
        'PORT': '',
        'CONN_MAX_AGE': 300,
    }
})

DATABASE_ROUTERS = [
    'netbox_branching.database.BranchAwareRouter',
]
