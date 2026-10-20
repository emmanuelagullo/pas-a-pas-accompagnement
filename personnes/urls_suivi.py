from django.urls import path
from . import vues_suivi as vues
from . import vues_repas
from . import vues_hebergement as h
app_name = "suivi"
urlpatterns = [
    path("accompagnements/<uuid:pk>/hebergement/accorder/", h.accorder, name="accorder_hebergement"),
    path("hebergement/<uuid:pk>/", h.detail, name="accord_hebergement"),
    path("hebergement/<uuid:pk>/admettre/", h.admettre, name="admettre"),
    path("lieux/creer/", h.lieu, name="creer_lieu"),
    path("sejours/<uuid:pk>/affecter/", h.periode, name="affecter"),
    path("sejours/<uuid:pk>/absence/", h.periode, {"absence":True}, name="absence"),
    path("sejours/<uuid:pk>/sortir/", h.terminer, {"nature":"sejour"}, name="sortir"),
    path("affectations/<int:pk>/clore/", h.terminer, {"nature":"affectation"}, name="clore_affectation"),
    path("absences/<int:pk>/clore/", h.terminer, {"nature":"absence"}, name="clore_absence"),
    path("accompagnements/<uuid:pk>/repas/accorder/", vues_repas.accorder, name="accorder_repas"),
    path("repas/<uuid:pk>/", vues_repas.detail, name="accord_repas"),
    path("repas/<uuid:pk>/distribuer/", vues_repas.distribuer, name="distribuer_repas"),
    path("distributions/<int:pk>/annuler/", vues_repas.annuler, name="annuler_repas"),
    path("", vues.liste, name="liste"),
    path("creer/", vues.creer, name="creer"),
    path("<uuid:pk>/", vues.detail, name="detail"),
    path("<uuid:pk>/ajouter/", vues.ajouter, name="ajouter"),
    path("<uuid:pk>/ouvrir/", vues.ouvrir, name="ouvrir"),
    path("<uuid:pk>/appartenance/<int:objet_pk>/clore/", vues.clore, {"type_objet": "appartenance"}, name="clore_appartenance"),
    path("<uuid:pk>/accompagnement/<uuid:objet_pk>/clore/", vues.clore, {"type_objet": "accompagnement"}, name="clore_accompagnement"),
]
