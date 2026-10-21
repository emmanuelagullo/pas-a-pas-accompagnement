from django.urls import path
from . import vues_dossiers as vues
from . import vues_prestations_dossier as prestations

app_name = 'dossiers'
urlpatterns = [
    path('<str:nature>/<uuid:pk>/nouveau/<str:prestation>/', prestations.nouveau, name='nouveau'),
    path('transferts/', vues.transferts, name='transferts'),
    path('<str:nature>/nouveau/', vues.creer, name='creer'),
    path('<str:nature>/<uuid:pk>/prestation/<str:prestation>/', vues.choisir_periode, name='choisir'),
    path('<str:nature>/<uuid:pk>/', vues.detail, name='detail'),
]
