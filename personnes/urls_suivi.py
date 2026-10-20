from django.urls import path
from . import vues_suivi as vues
from . import vues_repas
app_name = "suivi"
urlpatterns = [
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
