from . import vues_chronologie
from . import vues_rapports
from . import vues_appels115 as appels115,vues_exploration as exploration,vues_releve as releve
from . import vues_financements as financements
from . import vues_aides as aides, vues_complements_c as complements_c
from . import vues_parcours as parcours
from . import vues_modeles_personnels
from . import vues_parametrage
from django.urls import path
from . import vues_annulations_arrivees as annulations_arrivees
from . import vues_trajectoire
from . import vues_retraits_chronologiques
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

from . import vues_complements_identite as identite_declaree
from . import vues_relations_personnelles as relations

from . import vues_dossier_complet as complet
from . import exports_rapports

app_name = 'dossiers'
from . import vues_pieces_dossier as pieces

urlpatterns = [
    path('<str:nature>/<uuid:pk>/chronologie/', vues_chronologie.detail, name='chronologie'),
    path('rapports/exporter/',exports_rapports.exporter,name='rapport_exporter'),
    path('rapports/conserver/',vues_rapports.conserver,name='rapport_conserver'),
    path('rapports/',vues_rapports.accueil,name='rapports_accueil'),
    path('rapports/nouveau/',vues_rapports.nouveau,name='rapport_nouveau'),
    path('rapports/composer/<str:source>/',vues_rapports.composer,name='rapport_composer'),
    path('personne/<uuid:pk>/condition/<str:code>/<int:fait_pk>/retirer/', vues_retraits_chronologiques.retirer, name='condition_retirer'),
    path('rapports/gerer/',vues_modeles_personnels.liste,name='rapports_gerer'),
    path('modeles/<int:pk>/gerer/', vues_modeles_personnels.gerer, name='modele_gerer'),
    path('rapports/<str:source>/personnaliser/', exploration.personnaliser, name='personnaliser_rapport'),
    path('explorer/justificatifs/', exploration.justificatifs, name='explorer_justificatifs'),
    path('explorer/fait/', exploration.justificatifs, {'fait':True}, name='explorer_fait'),
    path('parametrage/', vues_parametrage.catalogue, name='parametrage'),
    path('arrivees/<uuid:pk>/annulation/',annulations_arrivees.retirer,name='annuler_arrivee'),
    path('pieces/<str:nature>/<uuid:pk>/',pieces.pieces,name='pieces'),
    path('pieces/fichier/<int:pk>/',pieces.telecharger,name='piece_telecharger'),
    path('appels115/',appels115.journal,name='appels115'),
    path('appels115/nouveau/',appels115.saisir,name='appel115_nouveau'),
    path('appels115/<uuid:pk>/',appels115.fiche,name='appel115'),
    path('appels115/<uuid:pk>/modifier/',appels115.saisir,name='appel115_modifier'),
    path('appels115/<uuid:pk>/lier/',appels115.action,{'action':'lier'},name='appel115_lier'),
    path('appels115/<uuid:pk>/annuler/',appels115.action,{'action':'annuler'},name='appel115_annuler'),
    path('appels115/<uuid:pk>/liens/<int:lien_pk>/annuler/',appels115.action,{'action':'delier'},name='appel115_delier'),
    path('appels115/<uuid:pk>/pdf/',appels115.pdf,name='appel115_pdf'),
    path('explorer/modeles/importer/',exploration.echanger_modele,name='explorer_importer_modele'),
    path('explorer/modeles/<int:pk>/exporter/',exploration.echanger_modele,name='explorer_exporter_modele'),
    path('explorer/nouveau/',exploration.nouveau,name='explorer_nouveau'),
    path('explorer/',exploration.explorer,name='explorer'),
    path('explorer/modeles/<int:pk>/supprimer/',exploration.supprimer_modele,name='explorer_supprimer_modele'),
    path('releve/recherche/',releve.recherche,name='releve_recherche'),
    path('releve/<str:nature>/<int:pk>/annuler/',releve.annuler,name='contribution_annuler'),
    path('releve/actions/<int:pk>/',releve.action,name='action_corriger'),
    path('tarifs/', financements.tarifs, name='tarifs'),
    path('tarifs/<uuid:pk>/', financements.tarifs, name='tarif'),
    path('financement/<str:nature>/<uuid:pk>/', financements.fiche, name='financement'),
    path('financement/<str:nature>/<uuid:pk>/calcul/', financements.calcul, name='financement_calcul'),
    path('financement/<str:nature>/<uuid:pk>/emettre/', financements.emission, name='financement_emission'),
    path('documents-financement/<int:pk>/', financements.document, name='document_financement'),
    path('rapports/financements/', financements.rapport, name='rapport_financements'),
    path('aides/<uuid:pk>/pdf/', aides.pdf, name='aide_pdf'),
    path('repas/<uuid:pk>/service/corriger/', complements_c.service_repas, name='corriger_service_repas'),
    path('rapports/hebergement-individuel/', complements_c.rapport_hebergement, name='rapport_hebergement_individuel'),
    path('lieux/', complements_c.lieu, name='lieux_c'),
    path('lieux/<int:pk>/corriger/', complements_c.lieu, name='lieu_c_corriger'),
    path('aides/types/', aides.catalogue, name='types_aides'),
    path('aides/types/<uuid:pk>/', aides.catalogue, name='type_aide'),
    path('rapports/aides/', aides.rapport, name='rapport_aides'),
    path('prise/<uuid:pk>/aides/<str:nature>/accorder/', aides.accorder, name='aide_accorder'),
    path('aides/<uuid:pk>/', aides.fiche, name='aide'),
    path('aides/<uuid:pk>/remettre/', aides.action, {'action':'remettre'}, name='aide_remettre'),
    path('aides/<uuid:pk>/corriger/', aides.action, {'action':'corriger'}, name='aide_corriger'),
    path('aides/<uuid:pk>/prolonger/', aides.action, {'action':'prolonger'}, name='aide_prolonger'),
    path('aides/<uuid:pk>/annuler/', aides.action, {'action':'annuler'}, name='aide_annuler'),
    path('aides/<uuid:pk>/remise/<int:remise_pk>/corriger/', aides.action, {'action':'corriger_remise'}, name='aide_remise_corriger'),
    path('aides/<uuid:pk>/remise/<int:remise_pk>/annuler/', aides.action, {'action':'annuler'}, name='aide_remise_annuler'),
    path('aides/<uuid:pk>/remise/<int:remise_pk>/usage/', aides.action, {'action':'usage'}, name='aide_usage'),
    path('sejour/<uuid:pk>/continuer/', complements_c.individualiser, name='individualiser_sejour'),
    path('repas/<int:pk>/corriger/', complements_c.repas, name='corriger_distribution'),

    path('rapports/parcours/', parcours.rapport, name='rapport_parcours'),
    path('<str:nature>/<uuid:pk>/parcours/', parcours.hub, name='parcours'),
    path('<str:nature>/<uuid:pk>/parcours/<str:code>/nouveau/', parcours.nouveau, name='parcours_nouveau'),
    path('parcours/<str:code>/<uuid:pk>/', parcours.element, name='parcours_element'),
    path('parcours/<str:code>/<uuid:pk>/changer/', parcours.modifier, {'action':'changer'}, name='parcours_changer'),
    path('parcours/<str:code>/<uuid:pk>/<int:version_pk>/corriger/', parcours.modifier, {'action':'corriger'}, name='parcours_corriger'),
    path('parcours/<str:code>/<uuid:pk>/annuler/', parcours.modifier, {'action':'annuler'}, name='parcours_annuler'),
    path('demande/<uuid:pk>/liaison/', parcours.liaison, name='demande_liaison'),

    path('rapports/dossier-complet/',complet.rapport,name='rapport_a'),
    path('personnes/<uuid:pk>/rubriques/<str:groupe>/',complet.fiche,name='fiche_a'),
    path('personnes/<uuid:pk>/administration/nouvelle/',complet.administration,{'action':'nouveau'},name='administration_nouvelle'),
    path('personnes/<uuid:pk>/administration/<int:fait_pk>/corriger/',complet.administration,{'action':'corriger'},name='administration_corriger'),
    path('personnes/<uuid:pk>/declarations/<str:code>/nouveau/',complet.modifier,{'action':'nouveau'},name='fait_a_nouveau'),
    path('personnes/<uuid:pk>/declarations/<str:code>/absence/',complet.modifier,{'action':'absence'},name='fait_a_absence'),
    path('personnes/<uuid:pk>/declarations/<str:code>/<int:fait_pk>/changer/',complet.modifier,{'action':'changer'},name='fait_a_changer'),
    path('personnes/<uuid:pk>/declarations/<str:code>/<int:fait_pk>/clore/',complet.modifier,{'action':'clore'},name='fait_a_clore'),
    path('personnes/<uuid:pk>/declarations/<str:code>/<int:fait_pk>/corriger/',complet.modifier,{'action':'corriger'},name='fait_a_corriger'),
    path('personnes/<uuid:pk>/declarations/<str:code>/<int:fait_pk>/annuler/',complet.modifier,{'action':'annuler'},name='fait_a_annuler'),

    path('rapports/identite/',identite_declaree.rapport,name='rapport_complements_identite'),
    path('rapports/relations/',relations.rapport,name='rapport_relations'),
    path('personnes/<uuid:pk>/identite-declaree/',identite_declaree.histoire,name='complements_identite'),
    path('personnes/<uuid:pk>/identite-declaree/nouveau/',identite_declaree.histoire,{'action':'nouveau'},name='complements_identite_nouveaux'),
    path('personnes/<uuid:pk>/identite-declaree/<int:fait_pk>/corriger/',identite_declaree.histoire,{'action':'corriger'},name='complements_identite_corriger'),
    path('personnes/<uuid:pk>/relations/',relations.histoire,name='relations_personnelles'),
    path('personnes/<uuid:pk>/relations/nouvelle/',relations.histoire,{'action':'nouvelle'},name='relation_nouvelle'),
    path('personnes/<uuid:pk>/relations/<int:fait_pk>/corriger/',relations.histoire,{'action':'corriger'},name='relation_corriger'),
    path('personnes/<uuid:pk>/relations/<int:fait_pk>/changer/',relations.histoire,{'action':'changer'},name='relation_changer'),
    path('personnes/<uuid:pk>/relations/<int:fait_pk>/clore/',relations.histoire,{'action':'clore'},name='relation_clore'),
    path('personnes/<uuid:pk>/relations/<int:fait_pk>/annuler/',relations.histoire,{'action':'annuler'},name='relation_annuler'),

    path('recherche-intervenants/', vues_recherche_intervenants.rechercher, name='recherche_intervenants'),
    path('propositions/echanger/',propositions.echanger,name='propositions_echanger'),
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
    path('<str:nature>/<uuid:pk>/trajectoire/', vues_trajectoire.dossier_detail, name='trajectoire'),
    path('<str:nature>/<uuid:pk>/', vues.detail, name='detail'),
]
