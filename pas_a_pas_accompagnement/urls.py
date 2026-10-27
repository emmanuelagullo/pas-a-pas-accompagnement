from django.contrib.auth.views import LogoutView
from django.urls import include, path
from .views import accueil, health, choisir_espace_local
from personnes.installation import installer
from personnes.views import decouverte
from personnes.vues_statistiques import statistiques, enregistrer_modele_rapport, supprimer_modele_rapport
from identites import vues as identites

from .copies_locales import copies

urlpatterns = [
    path("organisation/", include("acteurs.urls")),
    path("essai-local/", choisir_espace_local, name="choisir_espace_local"),
    path("decouverte/", decouverte, name="decouverte"),
    path("copies-locales/", copies, name="copies_locales"),
    path("dossiers/", include("personnes.urls_dossiers")),
    path("menages/", include("personnes.urls_suivi")),
    path("statistiques/", statistiques, name="statistiques"),
    path("statistiques/modeles/ajouter/", enregistrer_modele_rapport, name="statistiques_modele_ajouter"),
    path("statistiques/modeles/<int:pk>/supprimer/", supprimer_modele_rapport, name="statistiques_modele_supprimer"),
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
