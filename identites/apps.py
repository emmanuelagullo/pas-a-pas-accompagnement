from django.apps import AppConfig


class IdentitesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "identites"

    def ready(self):
        from .configuration import verifier
        verifier()
