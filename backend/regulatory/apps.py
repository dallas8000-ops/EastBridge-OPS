from django.apps import AppConfig


class RegulatoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'regulatory'

    def ready(self):
        import regulatory.signals  # noqa: F401
