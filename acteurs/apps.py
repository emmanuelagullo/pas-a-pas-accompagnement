from django.apps import AppConfig

class ActeursConfig(AppConfig):
    name='acteurs'
    def ready(self):
        from django.db.models.signals import m2m_changed,post_save,post_delete
        from .liens import verifier
        m2m_changed.connect(verifier,dispatch_uid='acteurs-liens',weak=False)
        from .notifications import attribution
        post_save.connect(attribution,dispatch_uid='acteurs-notification-attribution',weak=False)
        from .cache import mutation_organisation
        post_save.connect(mutation_organisation,dispatch_uid='acteurs-cache-save',weak=False)
        post_delete.connect(mutation_organisation,dispatch_uid='acteurs-cache-delete',weak=False)
