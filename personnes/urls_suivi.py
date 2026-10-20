from django.urls import path
from . import vues_suivi as vues
app_name = "suivi"
urlpatterns = [
    path("", vues.liste, name="liste"),
    path("creer/", vues.creer, name="creer"),
    path("<uuid:pk>/", vues.detail, name="detail"),
    path("<uuid:pk>/ajouter/", vues.ajouter, name="ajouter"),
    path("<uuid:pk>/ouvrir/", vues.ouvrir, name="ouvrir"),
    path("<uuid:pk>/appartenance/<int:objet_pk>/clore/", vues.clore, {"type_objet": "appartenance"}, name="clore_appartenance"),
    path("<uuid:pk>/accompagnement/<uuid:objet_pk>/clore/", vues.clore, {"type_objet": "accompagnement"}, name="clore_accompagnement"),
]
