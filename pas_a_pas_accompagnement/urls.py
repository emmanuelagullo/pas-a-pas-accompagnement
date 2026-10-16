from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path
from .views import accueil, health
from personnes.installation import installer

urlpatterns = [
    path("installer/", installer, name="installation_locale"),
    path("", accueil, name="accueil"),
    path("health/", health, name="health"),
    path("connexion/", LoginView.as_view(template_name="connexion.html"), name="connexion"),
    path("deconnexion/", LogoutView.as_view(), name="deconnexion"),
    path("personnes/", include("personnes.urls")),
]
