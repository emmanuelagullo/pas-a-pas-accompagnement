from django.contrib.auth.views import LogoutView
from django.urls import include, path
from .views import accueil, health
from personnes.installation import installer
from personnes.views import decouverte
from identites import vues as identites

from .copies_locales import copies

urlpatterns = [
    path("decouverte/", decouverte, name="decouverte"),
    path("copies-locales/", copies, name="copies_locales"),
    path("menages/", include("personnes.urls_suivi")),
    path("installer/", installer, name="installation_locale"),
    path("", accueil, name="accueil"),
    path("health/", health, name="health"),
    path("connexion/", identites.Connexion.as_view(), name="connexion"),
    path("connexion/verification/", identites.verification, name="connexion_verification"),
    path("mon-compte/securite/", identites.securite, name="securite_compte"),
    path("mon-compte/mot-de-passe/", identites.ChangerMotDePasse.as_view(), name="changer_mot_de_passe"),
    path("deconnexion/", LogoutView.as_view(), name="deconnexion"),
    path("personnes/", include("personnes.urls")),
]
