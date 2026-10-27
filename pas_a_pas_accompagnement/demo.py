"""Identifiants publics fictifs ; jamais utilisés par le profil persistant."""
IDENTIFIANT = 'essai'
MOT_DE_PASSE = 'Demonstration-fictive-2026!'


def contexte(request):
    from django.conf import settings
    if not getattr(settings, 'DEMONSTRATION_PUBLIQUE', False):
        return {}
    from acteurs.models import ConfigurationAcces
    return {'demonstration_acteurs': ConfigurationAcces.objects.filter(pk=1, active=True).exists(),
            'demonstration_publique': True, 'identifiant_demo': IDENTIFIANT,
            'mot_de_passe_demo': MOT_DE_PASSE}


class ProtegerComptePublic:
    """Un visiteur ne doit pas changer les accès du compte partagé."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.http import HttpResponseForbidden
        from django.conf import settings
        protege = getattr(settings, 'DEMONSTRATION_PUBLIQUE', False) or getattr(settings, 'ESPACE_ESSAI', False)
        if protege and request.path_info.startswith('/mon-compte/'):
            return HttpResponseForbidden('Le compte public de démonstration ne peut pas être modifié.')
        return self.get_response(request)
