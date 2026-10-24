from django.urls import path
from . import vues_dossiers as vues
from . import vues_prestations_dossier as prestations

from . import vues_bd6 as bd6
from . import vues_famille as famille
from . import vues_coordonnees as coordonnees
from . import vues_contacts_menage as contacts
from . import vues_partenaires as partenaires
from . import vues_intervenants as intervenants
from . import vues_interventions as interventions

from . import vues_propositions as propositions

from . import vues_recherche_intervenants

app_name = 'dossiers'
urlpatterns = [
    path('recherche-intervenants/', vues_recherche_intervenants.rechercher, name='recherche_intervenants'),
    path('propositions/', propositions.liste, name='propositions'),
    path('propositions/nouvelle/', propositions.liste, {'action':'nouvelle'}, name='proposition_nouvelle'),
    path('propositions/<int:pk>/modifier/', propositions.liste, {'action':'modifier'}, name='proposition_modifier'),
    path('prises/<uuid:pk>/interventions/', interventions.gerer, name='interventions'),
    path('prises/<uuid:pk>/interventions/nouvelle/', interventions.gerer, {'action':'nouvelle'}, name='intervention_nouvelle'),
    path('prises/<uuid:pk>/interventions/<int:affectation_pk>/corriger/', interventions.gerer, {'action':'correction'}, name='intervention_corriger'),
    path('prises/<uuid:pk>/interventions/<int:affectation_pk>/clore/', interventions.gerer, {'action':'clore'}, name='intervention_clore'),
    path('prises/<uuid:pk>/interventions/<int:affectation_pk>/annuler/', interventions.gerer, {'action':'annuler'}, name='intervention_annuler'),
    path('intervenants/', intervenants.liste, name='intervenants'),
    path('intervenants/nouveau/', intervenants.fiche, {'action': 'creer'}, name='intervenant_creer'),
    path('intervenants/<uuid:pk>/', intervenants.fiche, name='intervenant'),
    path('intervenants/<uuid:pk>/changer/', intervenants.fiche, {'action': 'changer'}, name='intervenant_changer'),
    path('intervenants/<uuid:pk>/<int:fait_pk>/corriger/', intervenants.fiche, {'action': 'corriger'}, name='intervenant_corriger'),
    path('partenaires/', partenaires.liste, name='partenaires'),
    path('partenaires/nouveau/', partenaires.fiche, {'action': 'creer'}, name='partenaire_creer'),
    path('partenaires/<uuid:pk>/', partenaires.fiche, name='partenaire'),
    path('partenaires/<uuid:pk>/changer/', partenaires.fiche, {'action': 'changer'}, name='partenaire_changer'),
    path('partenaires/<uuid:pk>/<int:fait_pk>/corriger/', partenaires.fiche, {'action': 'corriger'}, name='partenaire_corriger'),
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
