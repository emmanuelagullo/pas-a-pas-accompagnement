from django.urls import path
from . import vues_dossiers as vues
from . import vues_prestations_dossier as prestations

from . import vues_bd6 as bd6
from . import vues_famille as famille
from . import vues_coordonnees as coordonnees
from . import vues_contacts_menage as contacts

app_name = 'dossiers'
urlpatterns = [
    path('menage/<uuid:pk>/contact/', contacts.histoire, name='contact_menage'),
    path('menage/<uuid:pk>/contact/nouveau/', contacts.histoire, {'action': 'nouveau'}, name='contact_nouveau'),
    path('menage/<uuid:pk>/contact/<int:fait_pk>/corriger/', contacts.histoire, {'action': 'correction'}, name='contact_corriger'),
    path('rapports/coordonnees/', coordonnees.rapport, name='rapport_coordonnees'),
    path('personne/<uuid:pk>/coordonnees/', coordonnees.histoire, name='coordonnees'),
    path('personne/<uuid:pk>/coordonnees/nouvelles/', coordonnees.histoire, {'action': 'nouvelles'}, name='coordonnees_nouvelles'),
    path('personne/<uuid:pk>/coordonnees/<int:fait_pk>/corriger/', coordonnees.histoire, {'action': 'correction'}, name='coordonnees_corriger'),
    path('rapports/familles/', famille.rapport, name='rapport_familles'),
    path('personne/<uuid:pk>/famille/', famille.histoire, name='famille'),
    path('personne/<uuid:pk>/famille/nouvelle/', famille.histoire, {'action': 'nouvelle'}, name='famille_nouvelle'),
    path('personne/<uuid:pk>/famille/<int:fait_pk>/corriger/', famille.histoire, {'action': 'correction'}, name='famille_corriger'),
    path('personne/<uuid:pk>/social/', bd6.social, name='social'),
    path('personne/<uuid:pk>/social/<str:dimension>/nouveau/', bd6.social, name='social_nouveau'),
    path('personne/<uuid:pk>/social/<str:dimension>/<int:fait_pk>/corriger/', bd6.social, name='social_corriger'),
    path('menage/<uuid:pk>/membre/', bd6.membre, name='membre'),
    path('<str:nature>/<uuid:pk>/commentaire/', bd6.commentaire, name='commentaire'),
    path('<str:nature>/<uuid:pk>/prises/nouvelle/', bd6.nouvelle, name='nouvelle_prise'),
    path('<str:nature>/<uuid:pk>/prises/<uuid:prise_pk>/prolonger/', bd6.prolonger, name='prolonger_prise'),
    path('<str:nature>/<uuid:pk>/prises/<uuid:prise_pk>/prevision/corriger/', bd6.corriger_prevision, name='corriger_prevision'),
    path('<str:nature>/<uuid:pk>/prises/<uuid:prise_pk>/clore/', bd6.clore, name='clore_prise'),
    path('<str:nature>/<uuid:pk>/prises/<uuid:prise_pk>/commentaire/', bd6.commentaire, name='commentaire_prise'),
    path('<str:nature>/<uuid:pk>/prises/<uuid:prise_pk>/', vues.detail, name='prise'),
    path('<str:nature>/<uuid:pk>/nouveau/<str:prestation>/', prestations.nouveau, name='nouveau'),
    path('transferts/', vues.transferts, name='transferts'),
    path('<str:nature>/nouveau/', vues.creer, name='creer'),
    path('<str:nature>/<uuid:pk>/prestation/<str:prestation>/', vues.choisir_periode, name='choisir'),
    path('<str:nature>/<uuid:pk>/', vues.detail, name='detail'),
]
