from acteurs.contexte import service_metier
"""Demandes, orientations et objectifs : quatre chronologies métier typées.

Aucun état ne clôture une prise ou ne crée une prestation. Une cible et ses
bénéficiaires sont immuables ; l'erreur de cible s'annule puis se ressaisit.
"""
from collections import namedtuple
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from . import models as m, bd6, suivi, textes_riches as tr
from .series_personnelles import valeur_journal

Rubrique = namedtuple('Rubrique', 'racine version journal titre champs')
RUBRIQUES = {
    'demandes': Rubrique(m.DemandeAccueil, m.VersionDemande, m.RevisionDemande, 'Demandes d’accueil',
        ('etat','groupe_demande','motif_demande','motif_decision','demandeur','demandeur_professionnel','demandeur_organisme','precision_demandeur','prescripteur','organisme_orienteur','provenance','dernier_hebergement_type','dernier_hebergement_lieu','dernier_hebergement_duree','accueil_prevu','activite')),
    'orientations': Rubrique(m.OrientationParcours, m.VersionOrientation, m.RevisionOrientation, 'Orientations',
        ('etat','destination','type_destination','organisme','interlocuteur','motif_orientation','resultat','date_prevue')),
    'objectifs': Rubrique(m.ObjectifParcours, m.VersionObjectif, m.RevisionObjectif, 'Objectifs et progression',
        ('etat','theme','titre','horizon','echeance','texte')),
    'suivi': Rubrique(m.RepereDossier, m.VersionRepereDossier, m.RevisionRepereDossier, 'Suivi du dossier', ('etat','raison')),
}


def droits(code):
    r = RUBRIQUES[code]
    ds = ['view_personne', 'view_'+r.racine._meta.model_name, 'view_'+r.version._meta.model_name, 'view_'+r.journal._meta.model_name]
    if code in ('demandes','orientations'):
        ds += ['view_partenaire','view_fichepartenaire','view_intervenant','view_ficheintervenant']
    return tuple('personnes.'+d for d in ds)


@service_metier
def exiger(acteur, code, *actions):
    if not acteur.has_perms(droits(code)):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    suivi.exiger(acteur, *(a+'_'+RUBRIQUES[code].racine._meta.model_name for a in actions))


def cible_q(objet):
    return {'personne': objet} if isinstance(objet, m.Personne) else {'menage': objet}


def elements(code, objet):
    return RUBRIQUES[code].racine.objects.filter(**cible_q(objet)).select_related('personne','menage').prefetch_related('beneficiaires')


def a_date(code, jour):
    return RUBRIQUES[code].version.objects.filter(element__annule_le__isnull=True, debut__lte=jour).filter(Q(fin__isnull=True)|Q(fin__gt=jour))


def photographie(code, element):
    r = RUBRIQUES[code]
    beneficiaires=[valeur_journal(p) for p in element.beneficiaires.all()]
    return [{'cible':valeur_journal(element.cible),'beneficiaires':beneficiaires,'annulation':element.motif_annulation,'id':x.pk,'debut':x.debut.isoformat(),'fin':x.fin.isoformat() if x.fin else None,
        **{c:valeur_journal(getattr(x,c)) for c in (*r.champs, *(['texte_document'] if code=='objectifs' else []))},'source':x.source}
        for x in element.versions.order_by('debut','pk')]


def contexte_valide(objet, beneficiaires, accompagnement=None, demande=None):
    ids = {p.pk for p in beneficiaires}
    if not ids: raise ValidationError({'beneficiaires':'Choisissez les personnes concernées.'})
    if isinstance(objet,m.Personne) and ids != {objet.pk}:
        raise ValidationError({'beneficiaires':'Le dossier individuel concerne seulement cette personne.'})
    if isinstance(objet,m.Menage) and not ids.issubset(set(objet.appartenances.values_list('personne_id',flat=True))):
        raise ValidationError({'beneficiaires':'Les personnes doivent être explicitement rattachées à ce ménage.'})
    if accompagnement:
        if isinstance(objet,m.Menage) and accompagnement.menage_id != objet.pk or not ids.issubset(set(accompagnement.beneficiaires.values_list('pk',flat=True))):
            raise ValidationError({'accompagnement':'La prise en charge ne correspond pas à cette cible et ces bénéficiaires.'})
    if demande:
        if demande.annule_le or demande.personne_id != getattr(objet,'pk',None) and isinstance(objet,m.Personne) or demande.menage_id != getattr(objet,'pk',None) and isinstance(objet,m.Menage):
            raise ValidationError({'demande':'La demande ne correspond pas à ce dossier.'})
        if not ids.issubset(set(demande.beneficiaires.values_list('pk',flat=True))):
            raise ValidationError({'demande':'Les bénéficiaires ne correspondent pas à la demande.'})


@service_metier
def creer(acteur, code, objet, beneficiaires, debut, source, attendu, motif='', accompagnement=None, demande=None, **valeurs):
    exiger(acteur,code,'add')
    if isinstance(objet,m.Menage):suivi.exiger(acteur,'view_menage')
    if accompagnement:suivi.exiger(acteur,'view_accompagnement','view_menage')
    if demande:exiger(acteur,'demandes')
    if code in ('demandes','suivi') and accompagnement or code!='orientations' and demande:
        raise ValidationError('Ce lien de contexte n’est pas proposé pour cette rubrique.')
    with transaction.atomic():
        bd6.reserver(objet,attendu)
        beneficiaires=list(beneficiaires)
        contexte_valide(objet,beneficiaires,accompagnement,demande)
        r=RUBRIQUES[code]
        if code=='suivi' and elements(code,objet).filter(annule_le__isnull=True).exists():
            raise ValidationError('Un suivi existe déjà ; renseignez un changement ou une correction.')
        e=r.racine(**cible_q(objet),cree_par=acteur)
        if code in ('objectifs','orientations'):e.accompagnement=accompagnement
        if code=='orientations':e.demande=demande
        e.full_clean();e.save();e.beneficiaires.set(beneficiaires)
        _version(acteur,code,e,debut,source,motif,None,valeurs)
        return e


@service_metier
def enregistrer(acteur,code,element,debut,source,attendu,motif='',correction=None,**valeurs):
    exiger(acteur,code,'change')
    if element.menage_id:suivi.exiger(acteur,'view_menage')
    with transaction.atomic():
        bd6.reserver(element,attendu)
        return _version(acteur,code,element,debut,source,motif,correction,valeurs)


@service_metier
def _version(acteur,code,e,debut,source,motif,correction,valeurs):
    r=RUBRIQUES[code]
    if e.annule_le:raise ValidationError('Cette saisie est annulée ; elle reste dans l’histoire.')
    if set(valeurs)!=set(r.champs):raise ValidationError('Toutes les rubriques doivent être précisées, même vides.')
    if debut>timezone.localdate():raise ValidationError({'debut':'Une date d’effet ne peut pas être future ; utilisez la date annoncée.'})
    if len(source)>160:raise ValidationError({'source':'Indiquez une source de 160 caractères au plus.'})
    if len(motif)>240:raise ValidationError({'motif':'240 caractères au plus.'})
    avant=photographie(code,e);serie=list(e.versions.order_by('debut','pk'))
    action='ajout' if not serie else 'changement'
    x=r.version(element=e,auteur=acteur)
    if correction is not None:
        x=next((v for v in serie if v.pk==correction),None)
        if x is None:raise ValidationError('Cette version appartient à un autre élément.')
        action='correction'
    elif any(v.debut>debut for v in serie):action='insertion'
    if any(v.pk!=x.pk and v.debut==debut for v in serie):raise ValidationError({'debut':'Une version existe à cette date ; corrigez une erreur explicitement.'})
    donnees=dict(valeurs)
    if code=='objectifs':donnees.update(tr.colonnes('texte',valeurs['texte'],max_length=4000))
    if correction and x.debut==debut and x.source==source.strip() and all(getattr(x,c)==v for c,v in donnees.items()):
        raise ValidationError('Aucune modification.')
    x.debut=debut;x.source=source.strip()
    for c,v in donnees.items():setattr(x,c,v)
    if not correction:serie.append(x)
    serie.sort(key=lambda v:v.debut)
    if correction and [v.pk for v in serie]!=[v['id'] for v in avant]:
        raise ValidationError({'debut':'Une correction de date ne traverse pas une autre version ; insérez le fait oublié.'})
    if code=='demandes' and e.accompagnement_id:
        adm=e.accompagnement.debut
        applicable=next((v for v in reversed(serie) if v.debut<=adm),None)
        if not applicable or applicable.etat!='acceptee' or serie[-1].etat!='acceptee':
            raise ValidationError('Une demande liée doit rester acceptée à l’admission et actuellement ; corrigez d’abord une liaison erronée.')
    for i,v in enumerate(serie):v.fin=serie[i+1].debut if i+1<len(serie) else None
    for v in sorted(serie,key=lambda v:v.fin is None):v.full_clean();v.save()
    r.journal.objects.create(element=e,action=action,avant=avant,apres=photographie(code,e),motif=motif.strip(),auteur=acteur)
    return e


@service_metier
def annuler(acteur,code,element,motif,attendu):
    exiger(acteur,code,'annuler')
    if element.menage_id:suivi.exiger(acteur,'view_menage')
    with transaction.atomic():
        bd6.reserver(element,attendu)
        if element.annule_le or not motif.strip() or len(motif)>240:raise ValidationError('Saisie déjà annulée ou motif manquant/invalide.')
        if code=='demandes' and element.accompagnement_id:raise ValidationError('Corrigez d’abord la liaison à la prise en charge.')
        avant=photographie(code,element)
        element.annule_le=timezone.now();element.annule_par=acteur;element.motif_annulation=motif.strip()
        element.full_clean();element.save(update_fields=['annule_le','annule_par','motif_annulation'])
        RUBRIQUES[code].journal.objects.create(element=element,action='annulation',avant=avant,apres=photographie(code,element),motif=motif.strip(),auteur=acteur)


@service_metier
def lier(acteur,demande,prise,attendu,motif,retirer=False):
    """Ordre de verrouillage : ménage, puis demande ; jamais personne puis ménage."""
    exiger(acteur,'demandes','change')
    suivi.exiger(acteur,'view_accompagnement','view_menage')
    with transaction.atomic():
        # UPDATE avant toute lecture métier ; le CAS de la demande protège le formulaire.
        from django.db.models import F
        m.Menage.objects.filter(pk=prise.menage_id).update(revision=F('revision')+1)
        prise.refresh_from_db()
        bd6.reserver(demande,attendu)
        if not motif.strip() or len(motif)>240:raise ValidationError({'motif':'Expliquez l’association ou sa correction.'})
        avant=[{'accompagnement':valeur_journal(demande.accompagnement)}]
        if retirer:
            if demande.accompagnement_id!=prise.pk:raise ValidationError('La liaison a changé.')
            demande.accompagnement=None
        else:
            if demande.annule_le or demande.accompagnement_id:raise ValidationError('Demande annulée ou déjà associée.')
            version=a_date('demandes',prise.debut).filter(element=demande).first()
            actuelle=demande.versions.first()
            if not version or version.etat!='acceptee' or actuelle.etat!='acceptee':raise ValidationError('La demande doit être acceptée à la date d’admission et actuellement.')
            ids=set(demande.beneficiaires.values_list('pk',flat=True))
            if ids!=set(prise.beneficiaires.values_list('pk',flat=True)) or demande.menage_id and demande.menage_id!=prise.menage_id:
                raise ValidationError('La prise en charge doit porter exactement les bénéficiaires et le ménage annoncés.')
            if m.DemandeAccueil.objects.filter(accompagnement=prise).exclude(pk=demande.pk).exists():raise ValidationError('Cette prise en charge est déjà liée à une demande.')
            demande.accompagnement=prise
        demande.full_clean();demande.save(update_fields=['accompagnement'])
        m.RevisionDemande.objects.create(element=demande,action='deliaison' if retirer else 'liaison',avant=avant,apres=[{'accompagnement':valeur_journal(demande.accompagnement)}],motif=motif.strip(),auteur=acteur)
        return demande
