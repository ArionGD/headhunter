from django.apps import AppConfig
from django.db.models.signals import post_migrate


def sync_turso_on_migrate(sender, **kwargs):
    try:
        from core.turso_sync import init_turso_schema, sync_from_turso
        init_turso_schema()
        sync_from_turso()
    except Exception:
        pass


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        post_migrate.connect(sync_turso_on_migrate, sender=self)


