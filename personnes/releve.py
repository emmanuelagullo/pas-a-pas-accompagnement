from acteurs.contexte import service_metier
"""Recherche chronologique de contributions ; les droits de cible restent nécessaires."""
from datetime import timedelta
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from . import models as m,transmissions as s,bd6,suivi


def date_de(x):return x.date_fait or timezone.localdate(x.cree_le)


@service_metier
def lecture(acteur,x):
    s._droit(acteur,'view','transmission' if isinstance(x,m.Transmission) else 'notepartagee')
    if isinstance(x,m.NotePartagee):s._droit(acteur,'view',s.cible_note(x)._meta.model_name)


@service_metier
def contributions(acteur,debut=None,fin=None,q='',auteur=None,annules=False,notes=False):
    model=m.NotePartagee if notes else m.Transmission
    s._droit(acteur,'view','notepartagee' if notes else 'transmission')
    qs=model.objects.select_related('auteur','annulation').prefetch_related('revisions__auteur')
    if notes:qs=qs.select_related(*s.CIBLES_NOTE)
    if auteur:qs=qs.filter(auteur=auteur)
    resultat=[]
    for x in qs:
        if hasattr(x,'annulation') and not annules:continue
        try:lecture(acteur,x)
        except PermissionDenied:continue
        date=date_de(x)
        if debut and date<debut or fin and date>=fin:continue
        if any(mot.casefold() not in x.contenu.casefold() for mot in q.split()):continue
        resultat.append(x)
    return sorted(resultat,key=lambda x:(date_de(x),x.cree_le,x.pk),reverse=True)


@service_metier
@transaction.atomic
def creer_action(acteur,libelle,echeance,transmission=None,note=None,appel=None):
    suivi.exiger(acteur,'view_actionrelais','add_actionrelais')
    if sum(x is not None for x in (transmission,note,appel))>1:raise ValidationError('Une action a au plus un contexte explicite.')
    if transmission or note:lecture(acteur,transmission or note)
    if appel:
        from .appels115 import lire
        # Même verrou d’agrégat que l’annulation : pas de tâche ajoutée après elle.
        m.Appel115.objects.filter(pk=appel.pk).update(revision_sociale=F('revision_sociale')+1)
        appel.refresh_from_db();lire(acteur,appel)
        if appel.annule_le:raise ValidationError('Cet appel est annulé ; choisissez un contexte actif pour la nouvelle action.')
    x=m.ActionRelais(libelle=libelle,auteur=acteur,echeance=echeance,transmission=transmission,note=note,appel=appel);x.full_clean();x.save()
    m.RevisionActionRelais.objects.create(action_relais=x,action='ajout',avant=[],apres=photo(x),motif='Action saisie explicitement',auteur=acteur);return x


def photo(x):
    from .series_personnelles import valeur_journal
    return [{c:valeur_journal(getattr(x,c)) for c in ('libelle','echeance','terminee_le','terminee_par','annule_le','annule_par','motif_annulation')}]


@service_metier
@transaction.atomic
def changer_action(acteur,action,attendu,motif,libelle=None,echeance=None,terminer=False,reouvrir=False,annuler=False):
    suivi.exiger(acteur,'view_actionrelais','change_actionrelais','view_revisionactionrelais');bd6.reserver(action,attendu)
    if not motif.strip() or len(motif)>240:raise ValidationError({'motif':'Expliquez la correction ou le changement.'})
    avant=photo(action)
    if annuler:
        suivi.exiger(acteur,'annuler_actionrelais')
        if action.terminee_le or action.annule_le:raise ValidationError('Action déjà réalisée ou annulée.')
        action.annule_le=timezone.now();action.annule_par=acteur;action.motif_annulation=motif.strip()
    elif terminer:
        if action.terminee_le:raise ValidationError('Action déjà terminée.')
        action.terminee_le=timezone.now();action.terminee_par=acteur
    elif reouvrir:
        if action.annule_le:suivi.exiger(acteur,'annuler_actionrelais')
        if not action.terminee_le and not action.annule_le:raise ValidationError('Action déjà ouverte.')
        action.terminee_le=None;action.terminee_par=None;action.annule_le=None;action.annule_par=None;action.motif_annulation=''
    else:action.libelle=libelle;action.echeance=echeance
    action.full_clean()
    if photo(action)==avant:raise ValidationError('Aucune modification.')
    action.save();m.RevisionActionRelais.objects.create(action_relais=action,action='annulation' if annuler else 'changement' if terminer or reouvrir else 'correction',avant=avant,apres=photo(action),motif=motif.strip(),auteur=acteur);return action


@service_metier
@transaction.atomic
def terminer(acteur,action,attendu=None):
    suivi.exiger(acteur,'view_actionrelais','change_actionrelais')
    if attendu:bd6.reserver(action,attendu)
    else:action.refresh_from_db()
    if action.annule_le:raise ValidationError('Action annulée ; aucune réalisation à enregistrer.')
    if action.terminee_le:return action
    avant=photo(action)
    if m.ActionRelais.objects.filter(pk=action.pk,terminee_le__isnull=True,revision_sociale=action.revision_sociale).update(terminee_le=timezone.now(),terminee_par=acteur,revision_sociale=F('revision_sociale')+1)!=1:raise ValidationError('Action modifiée ; rechargez avant de confirmer.')
    action.refresh_from_db();m.RevisionActionRelais.objects.create(action_relais=action,action='cloture',avant=avant,apres=photo(action),motif='Action explicitement marquée réalisée',auteur=acteur);return action
