from . import precisions_correction as precision
from acteurs.contexte import service_metier
"""Appels autonomes : faits, versions et liaisons explicites, aucune admission implicite."""
from uuid import uuid4
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction,IntegrityError
from django.utils import timezone
from . import models as m,bd6,suivi,textes_riches as tr
from .series_personnelles import valeur_journal

LECTURE=('view_appel115','view_versionappel115','view_revisionappel115','view_lienappelparcours')
CHAMPS=('adultes_declares','enfants_declares','grossesses_declarees','date','heure','type_appelant','appelant_personne','appelant_intervenant','appelant_organisme','appelant_libre','telephone','lieu_appel','menage','motif_principal','details','demandes_secondaires','reponses','etat_reponse','orientation','orientation_declaree','information_complementaire','source')


@service_metier
def droit(acteur,*actions):suivi.exiger(acteur,*LECTURE,*actions)


@service_metier
def cibles(acteur,v):
    if v.menage_id:suivi.exiger(acteur,'view_menage','view_personne')
    if v.appelant_personne_id or v.beneficiaires.exists():suivi.exiger(acteur,'view_personne')
    if v.appelant_intervenant_id:suivi.exiger(acteur,'view_intervenant','view_ficheintervenant')
    if v.appelant_organisme_id or v.orientation_id:suivi.exiger(acteur,'view_partenaire','view_fichepartenaire')


@service_metier
def lire(acteur,appel):
    droit(acteur);v=appel.versions.first()
    if v:cibles(acteur,v)
    return v


def creation():return signing.dumps(str(uuid4()),salt='appel115-creation')


def jeton(appel):return bd6.jeton(appel)


def motif_valide(motif):
    if not motif.strip() or len(motif)>240:raise ValidationError({'motif':'Expliquez cette action (240 caractères au plus).'})


@service_metier
@transaction.atomic
def _ecrire(acteur,attendu,beneficiaires,action,motif='',appel=None,**valeurs):
    droit(acteur,'add_versionappel115')
    if set(valeurs)!=set(CHAMPS):raise ValidationError('Informations d’appel incomplètes.')
    if appel:
        bd6.reserver(appel,attendu);lire(acteur,appel)
        if appel.annule_le:raise ValidationError('Cet appel est annulé.')
        if action not in ('suite','correction'):raise ValidationError('Distinguez suite et correction d’erreur.')
        if action=='correction':motif=precision.valider(motif)
        else:motif_valide(motif)
        precedente=appel.versions.first()
        if action=='suite' and (valeurs['date']!=precedente.date or precedente.heure is not None and valeurs['heure']!=precedente.heure):raise ValidationError({'date':'Corriger une date ou heure connue exige « Correction d’erreur ». Un rappel effectué est un nouvel appel.'})
        if action=='suite' and not set(precedente.beneficiaires.values_list('pk',flat=True)).issubset({p.pk for p in beneficiaires}):raise ValidationError({'beneficiaires':'Une erreur de personnes se corrige explicitement ; une suite peut compléter leur identification.'})
        n=precedente.version+1
    else:
        droit(acteur,'add_appel115')
        if action!='saisie':raise ValidationError('Commencez par la saisie de cet appel.')
        try:pk=signing.loads(attendu,salt='appel115-creation',max_age=86400)
        except (signing.BadSignature,TypeError):raise ValidationError('Création non vérifiable ; rechargez le formulaire.')
        if m.Appel115.objects.filter(pk=pk).exists():raise ValidationError('Appel déjà enregistré.')
        appel=m.Appel115(pk=pk,auteur=acteur);appel.save(force_insert=True);n=1
    if not valeurs['source'].strip():raise ValidationError({'source':'Indiquez la source de cet appel ou de sa correction.'})
    details=valeurs.pop('details');valeurs.update(tr.colonnes('details',details,max_length=4000))
    v=m.VersionAppel115(appel=appel,version=n,auteur=acteur,action=action,motif=motif.strip(),**valeurs);v.full_clean();v.save()
    ids={p.pk for p in beneficiaires}
    if ids:suivi.exiger(acteur,'view_personne')
    v.beneficiaires.set(ids);cibles(acteur,v)
    # Un rattachement déjà confirmé ne doit pas devenir incohérent en corrigeant les personnes.
    for lien in appel.liens.filter(annule_le__isnull=True):
        cible=lien.demande or lien.accompagnement
        verifier_lien(acteur,v,cible)
    return appel


def ecrire(*args,**kwargs):
    try:return _ecrire(*args,**kwargs)
    except IntegrityError as e:raise ValidationError('Confirmation déjà utilisée ; rechargez le journal des appels.') from e


@service_metier
@transaction.atomic
def annuler(acteur,appel,attendu,motif):
    droit(acteur,'annuler_appel115');bd6.reserver(appel,attendu);lire(acteur,appel);motif_valide(motif)
    if appel.annule_le:raise ValidationError('Appel déjà annulé.')
    if appel.liens.filter(annule_le__isnull=True).exists() or appel.actions.filter(terminee_le__isnull=True,annule_le__isnull=True).exists():raise ValidationError('Traitez ou annulez les actions et annulez les liens erronés avant d’annuler cet appel.')
    appel.annule_le=timezone.now();appel.annule_par=acteur;appel.motif_annulation=motif.strip();appel.save()
    m.RevisionAppel115.objects.create(appel=appel,action='annulation',avant=[],apres=[{'annule_le':valeur_journal(appel.annule_le)}],motif=motif.strip(),auteur=acteur)
    return appel


@service_metier
def droits_lien(acteur,cible):
    if isinstance(cible,m.DemandeAccueil):
        from .parcours import exiger
        exiger(acteur,'demandes')
    else:suivi.exiger(acteur,'view_personne','view_menage','view_accompagnement')


@service_metier
def verifier_lien(acteur,v,cible):
    droits_lien(acteur,cible)
    ids=set(v.beneficiaires.values_list('pk',flat=True));autres=set(cible.beneficiaires.values_list('pk',flat=True))
    if not ids or not ids.issubset(autres) or v.menage_id and getattr(cible,'menage_id',None)!=v.menage_id:raise ValidationError('Identifiez d’abord les personnes concernées ; le lien doit porter sur les mêmes bénéficiaires et le même ménage éventuel.')
    if getattr(cible,'annule_le',None):raise ValidationError('La demande cible est annulée.')


@service_metier
@transaction.atomic
def lier(acteur,appel,attendu,motif,demande=None,accompagnement=None):
    droit(acteur,'add_lienappelparcours');bd6.reserver(appel,attendu);v=lire(acteur,appel);motif_valide(motif)
    if appel.annule_le or (demande is None)==(accompagnement is None):raise ValidationError('Choisissez une demande ou une prise en charge pour cet appel actif.')
    verifier_lien(acteur,v,demande or accompagnement)
    x=m.LienAppelParcours(appel=appel,demande=demande,accompagnement=accompagnement,auteur=acteur,motif=motif.strip());x.full_clean();x.save();return x


@service_metier
@transaction.atomic
def delier(acteur,appel,lien,attendu,motif):
    droit(acteur,'annuler_lienappelparcours');bd6.reserver(appel,attendu);v=lire(acteur,appel);motif_valide(motif)
    lien=m.LienAppelParcours.objects.get(pk=lien.pk,appel=appel)
    if lien.annule_le:raise ValidationError('Lien déjà annulé.')
    droits_lien(acteur,lien.demande or lien.accompagnement)
    lien.annule_le=timezone.now();lien.annule_par=acteur;lien.motif_annulation=motif.strip();lien.save();return appel
