from acteurs.contexte import service_metier
"""Prestations à unités explicites : autoriser, remettre, constater l'usage.

Quatre natures fixes ; aucun tarif ni trajet effectué n'est déduit d'un titre.
Les snapshots d'accord gardent le libellé et l'unité au moment de l'autorisation.
"""
from decimal import Decimal
from uuid import uuid4
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from . import models as m, bd6, suivi
from .verrous_metier import serialiser
from .series_personnelles import valeur_journal

LECTURE=('personnes.view_personne','personnes.view_menage','personnes.view_accompagnement','personnes.view_accordaide','personnes.view_remiseaide','personnes.view_revisionaide','personnes.view_typeaide','personnes.view_usageaide','personnes.view_partenaire')
CATALOGUE=('nature','libelle','unite','fractionnable','precision','actif')
CHAMPS=('debut','fin','quantite','prestataire','financeur','valeur_bon','devise','source')


@service_metier
def droit(acteur,*actions):
    from django.core.exceptions import PermissionDenied
    if not acteur.has_perms(LECTURE):raise PermissionDenied
    suivi.exiger(acteur,*actions)


def source_valide(source,motif='',obligatoire=False):
    if not source.strip() or len(source)>160:raise ValidationError({'source':'Précisez la source (160 caractères au plus).'})
    if len(motif)>240 or obligatoire and not motif.strip():raise ValidationError({'motif':'Expliquez cette correction ou annulation (240 caractères au plus).'})


def jeton_catalogue():return signing.dumps(str(uuid4()),salt='type-aide-creation')


@service_metier
def _cataloguer(acteur,attendu,motif,objet=None,**valeurs):
    suivi.exiger(acteur,'view_typeaide','view_revisiontypeaide','change_typeaide' if objet else 'add_typeaide')
    if set(valeurs)!=set(CATALOGUE):raise ValidationError('Précisez le schéma complet du type d’aide.')
    if not motif.strip() or len(motif)>240:raise ValidationError({'motif':'Expliquez la définition ou la modification.'})
    if not valeurs['libelle'].strip() or not valeurs['unite'].strip():raise ValidationError('Le libellé et l’unité sont obligatoires.')
    with transaction.atomic():
        avant=[]
        if objet:
            bd6.reserver(objet,attendu);avant=[{c:valeur_journal(getattr(objet,c)) for c in CATALOGUE}]
        else:
            try:pk=signing.loads(attendu,salt='type-aide-creation',max_age=86400)
            except (signing.BadSignature,TypeError):raise ValidationError('Création non vérifiable ; rechargez le formulaire.')
            objet=m.TypeAide(pk=pk,cree_par=acteur)
        for c,v in valeurs.items():setattr(objet,c,v)
        apres=[{c:valeur_journal(getattr(objet,c)) for c in CATALOGUE}]
        if avant==apres:raise ValidationError('Aucune modification.')
        objet.full_clean();objet.save(force_insert=not bool(avant))
        m.RevisionTypeAide.objects.create(type_aide=objet,action='correction' if avant else 'ajout',avant=avant,apres=apres,motif=motif.strip(),auteur=acteur)
        return objet


def photo(accord,remise=None):
    x=remise or accord
    champs=('date','quantite','source','annule_le','motif_annulation') if remise else (*CHAMPS,'nature','libelle','unite','fractionnable','precision','annule_le','motif_annulation')
    return [{'id':str(x.pk),**{c:valeur_journal(getattr(x,c)) for c in champs},'beneficiaires':[valeur_journal(p) for p in x.beneficiaires.all()]}]


def total(accord):return accord.remises.filter(annule_le__isnull=True).aggregate(s=Sum('quantite'))['s'] or Decimal('0')


def bornes(accord,date):
    a=accord.accompagnement
    if date<accord.debut or accord.fin and date>=accord.fin or date<a.debut or a.fin and date>=a.fin:
        raise ValidationError('La réalisation doit être dans l’accord et la prise en charge.')
    if date>timezone.localdate():raise ValidationError({'date':'Une réalisation ne peut pas être future.'})


def beneficiaires_valides(selection,parents):
    ids={p.pk for p in selection}
    if not ids or not ids.issubset(set(parents.values_list('pk',flat=True))):raise ValidationError({'beneficiaires':'Sélectionnez les personnes explicitement concernées de cette prestation.'})
    return ids


@service_metier
@serialiser('accompagnement')
def accorder(acteur,accompagnement,type_aide,beneficiaires,attendu,**valeurs):
    droit(acteur,'add_accordaide')
    bd6.reserver(accompagnement,attendu)
    if set(valeurs)!=set(CHAMPS):raise ValidationError('Précisez toutes les informations de l’accord.')
    type_aide.refresh_from_db()
    if not type_aide.actif:raise ValidationError('Ce type d’aide n’est plus proposé ; choisissez un type actif.')
    ids=beneficiaires_valides(beneficiaires,accompagnement.beneficiaires)
    source_valide(valeurs['source'])
    if valeurs['debut']<accompagnement.debut or accompagnement.fin and (not valeurs['fin'] or valeurs['fin']>accompagnement.fin):raise ValidationError('L’accord doit rester dans la prise en charge.')
    a=m.AccordAide(accompagnement=accompagnement,type_aide=type_aide,cree_par=acteur,**valeurs,
        **{c:getattr(type_aide,c) for c in ('nature','libelle','unite','fractionnable','precision')})
    entier(a,a.quantite)
    a.full_clean();a.save();a.beneficiaires.set(ids)
    m.RevisionAide.objects.create(accord=a,action='ajout',avant=[],apres=photo(a),auteur=acteur)
    return a


@service_metier
@serialiser('accord')
def modifier(acteur,accord,attendu,motif,prolongation=False,**valeurs):
    droit(acteur,'change_accordaide');bd6.reserver(accord,attendu)
    source_valide(valeurs.get('source',''),motif,True)
    if accord.annule_le or set(valeurs)!=set(CHAMPS):raise ValidationError('Accord annulé ou données incomplètes.')
    avant=photo(accord);ancienne_fin=accord.fin;ancien_debut=accord.debut
    if prolongation:
        if accord.fin is None or valeurs['fin'] is not None and valeurs['fin']<=accord.fin:raise ValidationError('Prolonger étend une fin bornée ; une prévision erronée se corrige avec motif.')
        if any(getattr(accord,c)!=valeurs[c] for c in CHAMPS if c not in ('fin','source')):raise ValidationError('Une prolongation conserve les autres données.')
    for c,v in valeurs.items():setattr(accord,c,v)
    entier(accord,accord.quantite)
    accord.full_clean();a=accord.accompagnement
    if accord.debut<a.debut:raise ValidationError('L’accord commence avant la prise en charge.')
    if (accord.fin!=ancienne_fin or accord.debut!=ancien_debut) and a.fin and (accord.fin is None or accord.fin>a.fin):raise ValidationError('La nouvelle période doit respecter la prise en charge close ; les anciennes prévisions restent conservées.')
    if accord.quantite is not None and total(accord)>accord.quantite:raise ValidationError('La quantité autorisée ne peut être inférieure aux remises actives.')
    for r in accord.remises.filter(annule_le__isnull=True):bornes(accord,r.date)
    apres=photo(accord)
    if avant==apres:raise ValidationError('Aucune modification.')
    accord.save();m.RevisionAide.objects.create(accord=accord,action='changement' if prolongation else 'correction',avant=avant,apres=apres,motif=motif.strip(),auteur=acteur)
    return accord


@service_metier
@serialiser('accord')
def remettre(acteur,accord,beneficiaires,date,quantite,source,attendu,motif='',correction=None):
    droit(acteur,'change_remiseaide' if correction else 'add_remiseaide');bd6.reserver(accord,attendu)
    source_valide(source,motif,bool(correction));bornes(accord,date)
    if accord.annule_le:raise ValidationError('Cet accord est annulé.')
    ids=beneficiaires_valides(beneficiaires,accord.beneficiaires)
    x=m.RemiseAide(accord=accord,auteur=acteur);avant=[];ancien=Decimal('0')
    if correction:
        try:x=accord.remises.get(pk=correction)
        except m.RemiseAide.DoesNotExist:raise ValidationError('Remise étrangère à cet accord.')
        if x.annule_le:raise ValidationError('Cette remise est annulée.')
        if ids!=set(x.beneficiaires.values_list('pk',flat=True)):raise ValidationError('Une erreur de personnes se traite par annulation et nouvelle remise.')
        avant=photo(accord,x);ancien=x.quantite
        usage=x.usages.first()
        if usage and (usage.date<date or usage.quantite is not None and usage.quantite>quantite):raise ValidationError('Le constat d’utilisation serait incohérent ; corrigez-le d’abord.')
    if accord.quantite is not None and total(accord)-ancien+quantite>accord.quantite:raise ValidationError({'quantite':'La remise dépasse la quantité totale autorisée ; corrigez explicitement l’autorisation si nécessaire.'})
    entier(accord,quantite)
    x.date=date;x.quantite=quantite;x.source=source.strip();x.full_clean();x.save();x.beneficiaires.set(ids)
    apres=photo(accord,x)
    if avant==apres:raise ValidationError('Aucune modification.')
    m.RevisionAide.objects.create(accord=accord,remise=x,action='correction' if correction else 'ajout',avant=avant,apres=apres,motif=motif.strip(),auteur=acteur)
    return accord


@service_metier
@serialiser('accord')
def annuler(acteur,accord,attendu,motif,remise=None):
    droit(acteur,'annuler_remiseaide' if remise else 'annuler_accordaide');bd6.reserver(accord,attendu)
    source_valide('Annulation',motif,True)
    if remise:
        try:x=accord.remises.get(pk=remise)
        except m.RemiseAide.DoesNotExist:raise ValidationError('Remise étrangère à cet accord.')
    else:
        x=accord
        if accord.remises.exists():raise ValidationError('Un accord ayant eu des remises se conserve ; corrigez ou terminez sa période, sans effacer l’histoire.')
    if x.annule_le:raise ValidationError('Saisie déjà annulée.')
    avant=photo(accord,x if remise else None)
    x.annule_le=timezone.now();x.annule_par=acteur;x.motif_annulation=motif.strip();x.full_clean();x.save()
    m.RevisionAide.objects.create(accord=accord,remise=x if remise else None,action='annulation',avant=avant,apres=photo(accord,x if remise else None),motif=motif.strip(),auteur=acteur)
    return accord


@service_metier
@serialiser('accord')
def constater(acteur,accord,remise,date,quantite,source,attendu,motif=''):
    droit(acteur,'add_usageaide');bd6.reserver(accord,attendu);source_valide(source)
    try:r=accord.remises.get(pk=remise)
    except m.RemiseAide.DoesNotExist:raise ValidationError('Remise étrangère à cet accord.')
    dernier=r.usages.first()
    if r.annule_le or date<r.date or date>timezone.localdate() or quantite is not None and quantite>r.quantite:raise ValidationError('Constat d’usage incompatible avec la remise, sa date ou sa quantité.')
    if dernier:
        source_valide(source,motif,True)
        if date<dernier.date and r.usages.filter(date__gt=date).exclude(pk=dernier.pk).exists():raise ValidationError('Une correction de date ne traverse pas un autre constat.')
    entier(accord,quantite)
    x=m.UsageAide(remise=r,version=dernier.version+1 if dernier else 1,date=date,quantite=quantite,source=source.strip(),motif=motif.strip(),auteur=acteur)
    x.full_clean();x.save()
    champs=('date','quantite','source','version')
    m.RevisionAide.objects.create(accord=accord,remise=r,action='changement',avant=[{c:valeur_journal(getattr(dernier,c)) for c in champs}] if dernier else [],apres=[{c:valeur_journal(getattr(x,c)) for c in champs}],motif=motif.strip(),auteur=acteur)
    return accord


def entier(accord,quantite):
    if quantite is not None and not accord.fractionnable and Decimal(quantite)!=Decimal(quantite).to_integral_value():
        raise ValidationError({'quantite':'Cette unité se compte en nombres entiers ; les fractions ne sont pas autorisées.'})


def cataloguer(*args,**kwargs):
    from django.db import IntegrityError
    try:return _cataloguer(*args,**kwargs)
    except IntegrityError as exc:raise ValidationError('Cette confirmation a déjà été utilisée ; rechargez le catalogue.') from exc
