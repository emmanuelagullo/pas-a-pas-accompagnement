from django.urls import path
from . import vues_suivi as vues
from . import vues_informations
from . import vues_resume
from . import vues_admission
from . import vues_hebergement_collectif
from . import vues_repas
from . import vues_hebergement as h
from . import vues_social as social
from . import vues_jour
from . import vues_transmissions
from . import vues_trajectoire
from . import vues_corrections
app_name = "suivi"
urlpatterns = [
    path("accompagnements/<uuid:pk>/repas/services/", vues_repas.accorder_services, name="accorder_services_repas"),
    path("accompagnements/<uuid:pk>/accueillir/", vues_admission.accueillir, name="admission_guidee"),
    path("accompagnements/<uuid:pk>/resume/", vues_resume.resume, name="resume"),
    path("hebergement/<uuid:pk>/selection/", vues_hebergement_collectif.selection, name="selection_sejours"),
    path("accompagnements/<uuid:pk>/informations/", vues_informations.modifier, name="informations"),
    path("liaison/", vues_transmissions.cahier, name="cahier"),
    path("notes/<str:nature>/<uuid:pk>/", vues_transmissions.notes, name="notes"),
    path("contributions/<str:nature>/<int:pk>/corriger/", vues_transmissions.corriger, name="corriger_contribution"),
    path("corrections/<str:nature>/<str:pk>/", vues_corrections.corriger, name="corriger_saisie"),
    path("accompagnements/<uuid:pk>/corrections/", vues_corrections.historique, name="corrections"),
    path("jour/", vues_jour.jour, name="jour"),
    path("jour/actions/", vues_jour.actions, name="actions_relais"),
    path("jour/actions/<int:pk>/terminer/", vues_jour.terminer_action, name="terminer_action_relais"),
    path("accompagnements/<uuid:pk>/", vues.accompagnement, name="accompagnement"),
    path("accompagnements/<uuid:pk>/social/", social.detail, name="social"),
    path("accompagnements/<uuid:pk>/trajectoire/", vues_trajectoire.detail, name="trajectoire"),
    path("accompagnements/<uuid:pk>/social/situation/<str:dimension>/", social.renseigner, name="situation_sociale"),
    path("situations/<int:pk>/corriger/", social.corriger, name="corriger_situation"),
    path("accompagnements/<uuid:pk>/social/evenement/", social.ecrire, {"nature":"evenement"}, name="evenement_social"),
    path("accompagnements/<uuid:pk>/social/bilan/", social.ecrire, {"nature":"bilan"}, name="bilan_social"),
    path("accompagnements/<uuid:pk>/hebergement/accorder/", h.accorder, name="accorder_hebergement"),
    path("hebergement/<uuid:pk>/", h.detail, name="accord_hebergement"),
    path("hebergement/<uuid:pk>/admettre/", h.admettre, name="admettre"),
    path("lieux/creer/", h.lieu, name="creer_lieu"),
    path("sejours/<uuid:pk>/affecter/", h.periode, name="affecter"),
    path("sejours/<uuid:pk>/absence/", h.periode, {"absence":True}, name="absence"),
    path("sejours/<uuid:pk>/sortir/", h.terminer, {"nature":"sejour"}, name="sortir"),
    path("affectations/<int:pk>/changer-lieu/", h.changer_lieu, name="changer_lieu"),
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
