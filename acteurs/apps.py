from django.apps import AppConfig

class ActeursConfig(AppConfig):
    name='acteurs'
    def ready(self):
        from django.db.models.signals import m2m_changed
        from .liens import verifier
        m2m_changed.connect(verifier,dispatch_uid='acteurs-liens',weak=False)
