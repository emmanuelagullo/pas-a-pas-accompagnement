from acteurs.contexte import service_metier
"""Rôles professionnels datés, distincts de l'auteur et du contact de ménage."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from . import bd6, suivi
from .models import AffectationIntervenant, RevisionAffectationIntervenant, Intervenant, Partenaire
from .verrous_metier import serialiser

DROITS_LECTURE = ('personnes.view_personne', 'personnes.view_menage', 'personnes.view_accompagnement',
    'personnes.view_affectationintervenant', 'personnes.view_revisionaffectationintervenant',
    'personnes.view_intervenant', 'personnes.view_ficheintervenant', 'personnes.view_partenaire')


def photographie(x):
    return {'debut': x.debut.isoformat(), 'fin': x.fin.isoformat() if x.fin else None, 'role': x.role,
        'intervenant': {'id': str(x.intervenant_id), 'libelle': str(x.intervenant)} if x.intervenant_id else None,
        'organisme': {'id': str(x.organisme_id), 'libelle': str(x.organisme)} if x.organisme_id else None, 'source': x.source,
        'annule_le':x.annule_le.isoformat() if x.annule_le else None,'motif_annulation':x.motif_annulation}


@service_metier
@serialiser('accompagnement')
@transaction.atomic
def affecter(acteur, accompagnement, debut, fin, role, intervenant, organisme, source, attendu,
             motif='', correction=None, cloture=False):
    suivi.exiger(acteur, 'view_personne', 'view_menage', 'view_accompagnement',
        'view_affectationintervenant', 'view_revisionaffectationintervenant', 'add_affectationintervenant')
    bd6.reserver(accompagnement, attendu)
    if cloture and correction is None:
        raise ValidationError('Choisissez l’affectation dont la mission se termine.')
    if not source.strip() or len(source) > 160:
        raise ValidationError({'source': 'Indiquez une source (160 caractères maximum).'})
    if len(motif) > 240:
        raise ValidationError({'motif': 'Le motif est limité à 240 caractères.'})
    if debut > timezone.localdate() or fin and fin > timezone.localdate():
        raise ValidationError('Une affectation effective ne peut pas être future.')
    if debut < accompagnement.debut or accompagnement.fin and (debut >= accompagnement.fin or fin and fin > accompagnement.fin):
        raise ValidationError('L’affectation doit rester dans la prise en charge.')
    if (intervenant is None) == (organisme is None):
        raise ValidationError('Choisissez un professionnel ou un organisme, pas les deux.')
    if intervenant is not None and not isinstance(intervenant, Intervenant) or organisme is not None and not isinstance(organisme, Partenaire):
        raise ValidationError('La cible professionnelle ou l’organisme n’est pas valide.')
    if intervenant is not None:
        suivi.exiger(acteur, 'view_intervenant', 'view_ficheintervenant')
    if organisme is not None:
        suivi.exiger(acteur, 'view_partenaire')
    x = AffectationIntervenant(accompagnement=accompagnement, auteur=acteur)
    avant = {}
    action = 'ajout'
    if correction is not None:
        suivi.exiger(acteur, 'change_affectationintervenant')
        try:
            x = accompagnement.interventions.select_related('intervenant', 'organisme').get(pk=correction)
        except AffectationIntervenant.DoesNotExist:
            raise ValidationError('Affectation étrangère à cette prise en charge.')
        avant = photographie(x)
        if x.annule_le:
            raise ValidationError('Cette affectation est annulée ; son historique reste conservé.')
        if cloture:
            if x.fin is not None or fin is None or any([debut != x.debut, role != x.role, intervenant != x.intervenant, organisme != x.organisme, source != x.source]):
                raise ValidationError('La fin de mission conserve la cible, le début, le rôle et la source.')
            action = 'cloture'
        else:
            action = 'correction'
        if not motif.strip():
            raise ValidationError({'motif': 'Expliquez cette fin de mission ou correction.'})
    elif accompagnement.interventions.filter(role=role, debut__gt=debut,annule_le__isnull=True).exists():
        action = 'insertion'
        if not motif.strip():
            raise ValidationError({'motif': 'Expliquez l’ajout de cette affectation antérieure.'})
    x.debut, x.fin, x.role, x.intervenant, x.organisme, x.source = debut, fin, role, intervenant, organisme, source.strip()
    x.full_clean()
    voisins = accompagnement.interventions.filter(role=role, intervenant=intervenant, organisme=organisme,annule_le__isnull=True).exclude(pk=x.pk)
    voisins = voisins.filter(Q(fin__isnull=True) | Q(fin__gt=debut))
    if fin:
        voisins = voisins.filter(debut__lt=fin)
    if voisins.exists():
        raise ValidationError('Cette même affectation recouvre déjà la période choisie.')
    apres = photographie(x)
    if apres == avant:
        raise ValidationError('Aucune modification.')
    x.save()
    RevisionAffectationIntervenant.objects.create(accompagnement=accompagnement, affectation=x,
        action=action, avant=avant, apres=apres, motif=motif.strip(), auteur=acteur)
    return x


def a_date(accompagnement, jour):
    if jour < accompagnement.debut or accompagnement.fin and jour >= accompagnement.fin:
        return accompagnement.interventions.none()
    return accompagnement.interventions.filter(debut__lte=jour,annule_le__isnull=True).filter(Q(fin__isnull=True) | Q(fin__gt=jour)).select_related('intervenant', 'organisme')


@service_metier
@serialiser('accompagnement')
@transaction.atomic
def annuler(acteur,accompagnement,affectation,motif,attendu):
    suivi.exiger(acteur,'view_personne','view_menage','view_accompagnement','view_affectationintervenant',
        'view_revisionaffectationintervenant','annuler_affectationintervenant')
    bd6.reserver(accompagnement,attendu)
    try:x=accompagnement.interventions.select_related('intervenant','organisme').get(pk=affectation.pk)
    except AffectationIntervenant.DoesNotExist:raise ValidationError('Affectation étrangère à cette prise en charge.')
    if x.annule_le or not motif.strip() or len(motif)>240:
        raise ValidationError('Affectation déjà annulée ou motif manquant/invalide.')
    avant=photographie(x);x.annule_le=timezone.now();x.annule_par=acteur;x.motif_annulation=motif.strip()
    x.full_clean();x.save(update_fields=['annule_le','annule_par','motif_annulation'])
    RevisionAffectationIntervenant.objects.create(accompagnement=accompagnement,affectation=x,action='annulation',
        avant=avant,apres=photographie(x),motif=motif.strip(),auteur=acteur)


@service_metier
def presentation(acteur, accompagnement, jour):
    if not acteur.has_perms(DROITS_LECTURE):
        return []
    from . import intervenants
    lignes = list(a_date(accompagnement, jour))
    profils = {f.intervenant_id: f for f in intervenants.a_date(
        [x.intervenant_id for x in lignes if x.intervenant_id], jour).select_related('organisme')}
    for x in lignes:
        x.fiche_professionnelle = profils.get(x.intervenant_id)
        x.nom_affiche = x.fiche_professionnelle.nom if x.fiche_professionnelle else str(x.intervenant or x.organisme)
    return lignes
