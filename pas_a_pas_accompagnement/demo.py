"""Identifiants publics fictifs ; jamais utilisés par le profil persistant."""
IDENTIFIANT = 'essai'
MOT_DE_PASSE = 'Demonstration-fictive-2026!'


def contexte(request):
    from django.conf import settings
    if not getattr(settings, 'DEMONSTRATION_PUBLIQUE', False):
        return {}
    return {'demonstration_publique': True, 'identifiant_demo': IDENTIFIANT,
            'mot_de_passe_demo': MOT_DE_PASSE}


class ProtegerComptePublic:
    """Un visiteur ne doit pas changer les accès du compte partagé."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.http import HttpResponseForbidden
        if request.path.startswith('/mon-compte/'):
            return HttpResponseForbidden('Le compte public de démonstration ne peut pas être modifié.')
        return self.get_response(request)
