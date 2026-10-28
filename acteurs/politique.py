"""Sélection fermée : droits actuels, tâche et portée historique restent distincts."""
from django.apps import apps
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.utils import timezone
from .models import (ConfigurationAcces, Habilitation, AppartenanceProfessionnelle,
    LienCompteProfessionnel, Responsabilite, PorteeObjet, DossierService)
from .contexte import courant

# Répertoires et catalogues sont transversaux dans cette base applicative.
# Ils ne donnent jamais accès aux dossiers. Les permissions Django restent nécessaires.
REPERTOIRES = {'partenaire', 'fichepartenaire', 'revisionfichepartenaire',
    'intervenant', 'ficheintervenant', 'revisionficheintervenant', 'propositionsaisie',
    'revisionpropositionsaisie', 'typeaide', 'revisiontypeaide', 'lieuhebergement', 'revisionlieu'}
CONTEXTUELS={'notepartagee','revisioncontribution','annulationcontribution','actionrelais','revisionactionrelais'}
PERSONNELS = {'personne', 'menage', 'appartenance'}
FINANCE = {'tarifprestation', 'versiontarif', 'financementprestation', 'versionfinancement',
    'lignecout', 'imputationfinancement', 'documentfinancement', 'annulationdocument'}
OPERATIONS = {'accompagnement', 'accordhebergement', 'sejour', 'affectation', 'absence',
    'annulationarrivee', 'operationhebergement', 'accordrepas', 'repasdistribue',
    'operationrepas', 'accordaide', 'remiseaide', 'usageaide', 'revisionaide', 'revisionrepas',
    'continuite_sejour', 'continuitesejour', 'revisioncontinuite', 'revisionservicerepas',
    'evolutionaccord', 'correctionperiode', 'evenementsuivi', 'transmission',
    'revisioncontribution', 'annulationcontribution', 'actionrelais', 'revisionactionrelais',
    'notepartagee', 'appel115', 'versionappel115', 'revisionappel115', 'lienappelparcours'}


def active():
    # Activation stable pour la requête ; sélections de lecture mémorisées
    # dans cette requête uniquement, écritures revalidées sans ce cache.
    ctx=courant()
    if ctx is not None and ctx.controle_actif is not None:return ctx.controle_actif
    try: return ConfigurationAcces.objects.filter(pk=1, active=True).exists()
    except Exception as e:
        from django.db import OperationalError, ProgrammingError
        if isinstance(e, (OperationalError, ProgrammingError)):
            raise PermissionDenied('Le contrôle des accès est indisponible.') from e
        raise


def periode(jour=None, prefixe=''):
    jour = jour or timezone.localdate()
    return Q(**{prefixe+'debut__lte': jour}) & (Q(**{prefixe+'fin__isnull': True}) | Q(**{prefixe+'fin__gt': jour}))


def habilitations(compte):
    if not getattr(compte, 'is_authenticated', False) or not compte.is_active:
        return Habilitation.objects.none()
    prof=professionnel(compte)
    if not prof:return Habilitation.objects.none()
    services = AppartenanceProfessionnelle.objects.filter(periode(), professionnel_id=prof).values('service_id')
    return Habilitation.objects.filter(periode(), compte=compte, revoque_le__isnull=True,
        service__actif=True, service_id__in=services)


def taches(modele):
    nom = modele._meta.model_name
    if nom == 'modelerapport': return {'social', 'gestion', 'coordination'}
    if nom in FINANCE: return {'gestion'}
    if nom in PERSONNELS | OPERATIONS: return {'social', 'accueil', 'gestion'}
    if nom in REPERTOIRES: return {'social', 'accueil', 'gestion'}
    if nom == 'importparametrage': return {'gestion'}
    return {'social'}


def professionnel(compte):
    ctx=courant();cle=('professionnel',compte.pk)
    if ctx and cle in ctx.memo:return ctx.memo[cle]
    prof=LienCompteProfessionnel.objects.filter(compte=compte).values_list('professionnel_id', flat=True).first()
    if ctx:ctx.memo[cle]=prof
    return prof


def missions(compte):
    return Responsabilite.objects.filter(periode(timezone.now()), annule_le__isnull=True, professionnel_id=professionnel(compte),
        dossier__service_id__in=habilitations(compte).values('service_id'))


def pleines(compte, ecriture=False):
    hs = habilitations(compte).filter(tache='social')
    ps = ['collectif'] if ecriture else ['collectif', 'lecture']
    return hs.filter(service__politique__in=ps).values('service_id')


def portees(compte, modele, ecriture=False):
    hs = habilitations(compte).filter(tache__in=taches(modele))
    p = PorteeObjet.objects.filter(service_id__in=hs.values('service_id'))
    propres = missions(compte)
    dossier_seul = propres.filter(prise__isnull=True, hebergement__isnull=True, repas__isnull=True, aide__isnull=True)
    ctx = courant()
    mes_stats=bool(ctx and ctx.statistiques=='mes')
    q = Q(dossier_id__in=dossier_seul.values('dossier_id'))
    if not mes_stats:q |= Q(service_id__in=pleines(compte, ecriture))
    q |= Q(prise_id__in=propres.filter(prise__isnull=False).values('prise_id'))
    for nom in ('hebergement', 'repas', 'aide'):
        m = {'hebergement':'accordhebergement', 'repas':'accordrepas', 'aide':'accordaide'}[nom]
        q |= Q(prestation_modele=m, prestation_id__in=propres.filter(**{nom+'__isnull':False}).values_list(nom+'_id', flat=True))
    # Accueil : opérations seulement, pas l'histoire sociale ; la politique individuelle
    # n'empêche pas d'assurer la permanence dans le service autorisé.
    if not mes_stats and modele._meta.model_name in PERSONNELS | OPERATIONS | FINANCE:
        operation=Q(service_id__in=hs.filter(tache__in=['accueil', 'gestion']).values('service_id'))
        if modele._meta.model_name in CONTEXTUELS:operation &= Q(prestation_id__isnull=False)|Q(dossier__isnull=True)
        q |= operation
    if not mes_stats and modele._meta.model_name in ('transmission','revisioncontribution','annulationcontribution','actionrelais','revisionactionrelais'):
        q |= Q(dossier__isnull=True, service_id__in=hs.values('service_id'))
    ctx = courant()
    if ctx and ctx.statistiques in ('service','etablissement') and not ecriture:
        option='statistiques_etablissement' if ctx.statistiques=='etablissement' else 'statistiques_service'
        stats = habilitations(compte).filter(service_id=ctx.service_id,**{option:True})
        from .models import Service
        services = Service.objects.filter(pk__in=stats.values('service_id')) if ctx.statistiques == 'service' else Service.objects.filter(etablissement_id__in=stats.filter(statistiques_etablissement=True).values('service__etablissement_id'))
        # Les données personnelles ne sont consultées que durant le calcul, jamais
        # dans les justificatifs ou l'ouverture d'un dossier.
        p = PorteeObjet.objects.filter(service_id__in=services.values('pk'))
        return p
    if ctx and not ecriture:
        if ctx.statistiques=='service_accessible':p=p.filter(service_id=ctx.service_id)
        elif ctx.statistiques=='attente':p=p.filter(dossier__en_attente=True)
    return p.filter(q)


def filtre(modele, ecriture=False):
    ctx=courant()
    if ctx is None or not active():return Q()
    if ecriture:
        from .cache import invalider
        invalider()
        return calculer_filtre(modele,True)
    cle=('filtre',modele._meta.label_lower,ctx.service_id,ctx.statistiques,ctx.reperage,ctx.export_demande)
    if cle not in ctx.memo:ctx.memo[cle]=calculer_filtre(modele)
    return ctx.memo[cle]


def calculer_filtre(modele, ecriture=False):
    ctx = courant()
    if ctx is None or not active(): return Q()
    compte = ctx.compte
    hs = habilitations(compte)
    nom = modele._meta.model_name
    if nom == 'modelerapport': return Q(auteur=compte) if hs.exists() else Q(pk__in=[])
    if nom in REPERTOIRES:
        return Q() if hs.filter(tache__in=taches(modele)).exists() else Q(pk__in=[])
    ps = portees(compte, modele, ecriture)
    q = Q(pk__in=list(ps.filter(modele=modele._meta.label_lower).values_list('identifiant', flat=True)))
    if nom in ('personne', 'menage') and not ecriture:
        # Les identités nécessaires à une reprise sont visibles ; aucun fait social
        # n'est ouvert par cette sélection d'accueil.
        ds = DossierService.objects.filter(service_id__in=hs.exclude(tache='coordination').values('service_id'))
        if ctx.statistiques=='service_accessible':ds=ds.filter(service_id=ctx.service_id)
        elif ctx.statistiques=='attente':ds=ds.filter(en_attente=True)
        collectifs = ds.filter(pk__in=missions(compte).values('dossier_id')) if ctx.statistiques=='mes' else ds.filter(Q(service_id__in=pleines(compte)) | Q(pk__in=missions(compte).values('dossier_id')) | Q(en_attente=True))
        q |= Q(pk__in=collectifs.values(nom+'_id'))
        if nom == 'personne':
            from personnes.models import Appartenance
            q |= Q(pk__in=Appartenance._base_manager.filter(menage_id__in=collectifs.values('menage_id')).values('personne_id'))
    if nom in ('personne','menage') and ecriture:
        ds=DossierService.objects.filter(service_id__in=hs.values('service_id'))
        propres=missions(compte).filter(prise__isnull=True,hebergement__isnull=True,repas__isnull=True,aide__isnull=True)
        ds=ds.filter(Q(service_id__in=pleines(compte,True))|Q(pk__in=propres.values('dossier_id')))
        q |= Q(pk__in=ds.values(nom+'_id'))
        if nom=='personne':
            from personnes.models import Appartenance
            q |= Q(pk__in=Appartenance._base_manager.filter(menage_id__in=ds.values('menage_id')).values('personne_id'))
    if nom == 'accompagnement' and not ecriture:
        ids = missions(compte).values_list('hebergement__accompagnement_id', 'repas__accompagnement_id', 'aide__accompagnement_id')
        supplement={v for ligne in ids for v in ligne if v}
        if ctx.statistiques in ('service_accessible','attente'):
            supplement &= set(modele._base_manager.filter(pk__in=list(ps.filter(modele=modele._meta.label_lower).values_list('identifiant',flat=True))).values_list('pk',flat=True))
        q |= Q(pk__in=supplement)
    if ecriture and nom in ('transmission','notepartagee'):
        q &= Q(auteur=compte) | Q(pk__in=list(ps.filter(modele=modele._meta.label_lower,
            service_id__in=hs.filter(corriger_autrui=True).values('service_id')).values_list('identifiant',flat=True)))
    if ctx.reperage and not ecriture and not ctx.export_demande and not ctx.statistiques:
        from . import reperage
        if nom in ('personne','menage'):q |= Q(pk__in=reperage.identites(compte,nom))
        elif nom=='accompagnement' and ctx.reperage=='prestation':q |= Q(pk__in=list(reperage.prises(compte)))
    q |= Q(pk__in=[identifiant for label,identifiant in ctx.nouveaux if label==modele._meta.label_lower])
    return q


def exiger_objet(compte, objet, ecriture=False):
    from .contexte import perimetre
    with perimetre(compte):
        if not type(objet)._base_manager.filter(pk=objet.pk).filter(filtre(type(objet), ecriture)).exists():
            raise PermissionDenied('Cet objet ne fait pas partie de votre accès actuel.')


def service_creation(modele):
    ctx = courant()
    if not ctx: raise PermissionDenied
    hs = habilitations(ctx.compte).filter(tache__in=taches(modele))
    if ctx.service_id: hs = hs.filter(service_id=ctx.service_id)
    ids = list(hs.values_list('service_id', flat=True).distinct()[:2])
    if len(ids) != 1:
        raise ValidationError('Choisissez le service dans lequel effectuer cette saisie.')
    return ids[0]


def peut_renseigner(compte, origine, modele):
    hs=habilitations(compte).filter(service_id=origine.service_id,tache__in=taches(modele))
    if not hs.exists():return False
    ctx=courant()
    if ctx and origine.dossier_id:
        ds=origine.dossier
        racine=('personnes.personne',str(ds.personne_id)) if ds.personne_id else ('personnes.menage',str(ds.menage_id))
        if racine in ctx.nouveaux:return True
    if ctx and origine.prise_id and ('personnes.accompagnement',str(origine.prise_id)) in ctx.nouveaux:return True
    if ctx and origine.prestation_id and ('personnes.'+origine.prestation_modele,str(origine.prestation_id)) in ctx.nouveaux:return True
    nom=modele._meta.model_name
    if nom in OPERATIONS|PERSONNELS|FINANCE and hs.filter(tache__in=['accueil','gestion']).exists():
        if nom not in CONTEXTUELS or origine.prestation_id or origine.dossier_id is None:return True
    if origine.service_id in set(pleines(compte,True).values_list('service_id',flat=True)):return True
    rs=missions(compte).filter(dossier_id=origine.dossier_id)
    if rs.filter(prise__isnull=True,hebergement__isnull=True,repas__isnull=True,aide__isnull=True).exists():return True
    if origine.prise_id and rs.filter(prise_id=origine.prise_id).exists():return True
    for champ,modele_p in [('hebergement','accordhebergement'),('repas','accordrepas'),('aide','accordaide')]:
        if origine.prestation_modele==modele_p and rs.filter(**{champ+'_id':origine.prestation_id}).exists():return True
    return origine.dossier_id is None and nom in OPERATIONS
