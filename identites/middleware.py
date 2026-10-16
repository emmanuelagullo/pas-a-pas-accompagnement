"""Les sessions sans preuve actuelle n’accèdent jamais aux fiches fictives."""
from django.contrib.auth import logout
from django.shortcuts import redirect
from . import double_facteur as facteur
from .configuration import disponible, service_indisponible


class DoubleFacteurMiddleware:
    def __init__(self,get_response):
        self.get_response=get_response

    def __call__(self,request):
        return self.get_response(request)

    def process_view(self,request,view_func,view_args,view_kwargs):
        if not request.user.is_authenticated:
            return None
        nom = request.resolver_match.url_name if request.resolver_match else None
        if nom in {"deconnexion", "health"}:
            return None
        from .vues import PREUVE, indisponible
        if service_indisponible():
            logout(request)
            return indisponible()
        ligne = facteur.compte(request.user)
        if ligne and (ligne.inscrit or ligne.a_reinscrire) and not disponible():
            logout(request)
            return indisponible()
        if ligne and ligne.inscrit:
            if request.session.get(PREUVE) != str(ligne.revision):
                logout(request)
                return redirect("connexion")
        elif ligne and request.session.get(PREUVE) and request.session[PREUVE] != str(ligne.revision):
            logout(request)
            return redirect("connexion")
        if facteur.requis(request.user) and not (ligne and ligne.inscrit):
            request.inscription_2fa_requise = True
            if nom != "securite_compte":
                return redirect("securite_compte")
        return None
