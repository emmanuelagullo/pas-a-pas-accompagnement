"""COL2–4 : opérations communes avec preuves d'état et versions immuables."""
from copy import deepcopy
from datetime import timedelta, date
from decimal import Decimal, ROUND_HALF_UP
import re
from django.core import signing
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from acteurs.contexte import service_metier
from acteurs.models import Service, JournalAcces
from acteurs import portees
from acteurs.profils_collectifs import verifier, verifier_categories
from . import models as m, suivi
from .verrous_metier import serialiser

SALT='collectif-etat-v1'
SOCIAUX=('logement','revenu','dette','telephone','courriel','projet')
VERSION=('debut','fin','fin_prevue','arrivee','lieu','prestataire','dejeuner','diner','premier','dernier','petits_dejeuners','devise')

def profil(objet):
    try:service=service_objet(objet)
    except ValidationError:return None
    valeur=service.profil_collectif
    if not valeur:return None
    verifier(valeur)
    return valeur

def service_objet(objet):
    from acteurs.contexte import courant
    from acteurs.models import DossierService
    ctx=courant()
    if isinstance(objet,m.Menage) and ctx and ctx.service_id:
        ds=DossierService.objects.filter(service_id=ctx.service_id,menage=objet).select_related('service').first()
        if ds:return ds.service
    origine=portees.existante(objet)
    if not origine:raise ValidationError('Rattachez ce dossier à un service avant de configurer la collecte.')
    return origine.service

def etat(objet):
    if isinstance(objet,m.PrestationCollective):
        return [str(objet.pk),objet.revision]
    menage=objet.menage if isinstance(objet,m.Accompagnement) else objet
    scope={'accompagnement':objet} if isinstance(objet,m.Accompagnement) else {'accompagnement__isnull':True,'service':service_objet(objet)}
    lignes=list(m.CompositionCollective.objects.filter(menage=menage,**scope).values_list('pk',flat=True))
    return [str(objet.pk),menage.revision,sorted(lignes),service_objet(objet).revision]

def jeton(objet):return signing.dumps(etat(objet),salt=SALT)

def verifier_jeton(objet,attendu):
    try:ancien=signing.loads(attendu,salt=SALT,max_age=86400)
    except (signing.BadSignature,ValueError,TypeError):raise ValidationError('Formulaire périmé ; rechargez avant de confirmer.')
    if ancien!=etat(objet):raise ValidationError('Les données ou la configuration ont changé ; rechargez avant de confirmer.')

def composition(objet,jour):
    menage=objet.menage if isinstance(objet,m.Accompagnement) else objet
    q=m.CompositionCollective.objects.filter(menage=menage,service=service_objet(objet),debut__lte=jour,annule_le__isnull=True,pour_prestation=False)
    if isinstance(objet,m.Accompagnement):
        propre=q.filter(accompagnement=objet).order_by('-debut','-pk').first()
        if propre:return propre
    return q.filter(accompagnement__isnull=True).order_by('-debut','-pk').first()

def categorie_age(age,categories):
    return next((c['code'] for c in categories if c['min']<=age<=c['max']),None)

def age_exact(naissance,jour):
    if naissance>jour:return None
    return jour.year-naissance.year-((jour.month,jour.day)<(naissance.month,naissance.day))

def effectifs(comp,jour=None):
    jour=jour or comp.debut
    resultat={c['code']:0 for c in comp.categories};resultat['inconnu']=0
    for p in comp.identites:
        age=age_exact(date.fromisoformat(p['naissance']),jour) if p['naissance'] and p['precision']=='exacte' else None
        code=categorie_age(age,comp.categories) if age is not None else 'inconnu'
        resultat[code or 'inconnu']+=1
    for ligne in comp.complements:
        if ligne['naissance']:
            age=age_exact(date.fromisoformat(ligne['naissance']),jour)
            code=categorie_age(age,comp.categories) if age is not None else 'inconnu'
        elif ligne['age'] is not None:
            # Un âge déclaré ne définit aucun anniversaire.
            code=categorie_age(ligne['age'],comp.categories) if jour==comp.debut else 'inconnu'
        else:code=ligne['categorie']
        resultat[code or 'inconnu']+=ligne['nombre']
    return resultat

def verifier_complements(lignes,categories,jour):
    if not isinstance(lignes,list) or len(lignes)>100:raise ValidationError('Composition limitée à 100 lignes.')
    codes={c['code'] for c in categories}|{'inconnu'}
    for x in lignes:
        if not isinstance(x,dict) or set(x)!={'categorie','nombre','age','naissance'}:raise ValidationError('Ligne de composition inconnue.')
        if x['categorie'] not in codes or type(x['nombre']) is not int or not 1<=x['nombre']<=1000:raise ValidationError('Catégorie ou effectif invalide.')
        if x['age'] is not None and (type(x['age']) is not int or not 0<=x['age']<=120):raise ValidationError('Âge déclaré invalide.')
        if x['naissance']:
            try:n=date.fromisoformat(x['naissance'])
            except (ValueError,TypeError):raise ValidationError('Date de naissance invalide.')
            if n>jour or x['nombre']!=1 or x['age'] is not None:raise ValidationError('Une naissance concerne une seule personne non individualisée, sans âge concurrent.')
        if x['age'] is not None and x['nombre']!=1:raise ValidationError('Un âge concerne une seule personne non individualisée.')

def photo_comp(c):
    return {'id':c.pk,'debut':str(c.debut),'reference':str(c.reference_id),
            'identifies':[str(x) for x in c.identifies.values_list('pk',flat=True)],'complements':c.complements,
            **{k:str(getattr(c,k)) if getattr(c,k) is not None else None for k in SOCIAUX},'devise':c.devise}

@service_metier
@transaction.atomic
def renseigner(acteur,objet,attendu,debut,reference,identifies,complements,source='',actualiser=False,**valeurs):
    suivi.exiger(acteur,'view_menage','view_compositioncollective','add_compositioncollective')
    verifier_jeton(objet,attendu)
    menage=objet.menage if isinstance(objet,m.Accompagnement) else objet
    # CAS du ménage avant toute écriture de fait : interdit les doubles confirmations.
    if m.Menage.objects.filter(pk=menage.pk,revision=menage.revision).update(revision=F('revision')+1)!=1:
        raise ValidationError('Le ménage a changé ; rechargez.')
    cfg=profil(objet)
    if not cfg:raise ValidationError('Ce service utilise le parcours historique.')
    if debut>timezone.localdate():raise ValidationError('Une composition déclarée ne peut pas être future.')
    if set(valeurs)-set((*SOCIAUX,'devise')):raise ValidationError('Rubrique collective inconnue.')
    for k in SOCIAUX:
        if k not in cfg['rubriques'] and valeurs.get(k) not in ('',None):raise ValidationError('Cette rubrique n’est pas collectée dans ce service.')
    personnes=list(identifies);ids={p.pk for p in personnes}
    if reference.pk not in ids:raise ValidationError('La personne de référence doit figurer parmi les personnes identifiées.')
    possibles=set(objet.beneficiaires.values_list('pk',flat=True)) if isinstance(objet,m.Accompagnement) else set(m.Appartenance.objects.filter(menage=menage,debut__lte=debut).filter(m.models.Q(fin__isnull=True)|m.models.Q(fin__gt=debut)).values_list('personne_id',flat=True))
    if not ids.issubset(possibles):raise ValidationError('Choisissez les personnes de ce ménage ou de cette prise.')
    if cfg['identification']=='reference' and ids!={reference.pk}:raise ValidationError('Ce profil identifie uniquement la personne de référence.')
    if cfg['identification']=='adultes' and any(not p.date_naissance or p.precision_naissance!='exacte' or age_exact(p.date_naissance,debut) is None or age_exact(p.date_naissance,debut)<18 for p in personnes):raise ValidationError('Ce profil demande des adultes identifiés ; vérifiez leurs dates de naissance.')
    if cfg['identification']=='tous' and complements:raise ValidationError('Ce profil demande d’identifier tous les bénéficiaires.')
    if cfg['identification']=='tous' and ids!=possibles:raise ValidationError('Sélectionnez tous les bénéficiaires identifiés de ce contexte.')
    verifier_complements(complements,cfg['categories'],debut)
    if cfg['identification']=='adultes':
        categories={x['code']:x for x in cfg['categories']}
        for x in complements:
            age=age_exact(date.fromisoformat(x['naissance']),debut) if x['naissance'] else x['age']
            cat=categories.get(x['categorie'])
            if age is not None and age>=18 or cat and cat['max']>=18:
                raise ValidationError('Ce profil demande d’identifier les adultes, pas de les compter anonymement.')
    precedent=composition(objet,debut)
    c=m.CompositionCollective(menage=menage,accompagnement=objet if isinstance(objet,m.Accompagnement) else None,
        service=service_objet(objet),debut=debut,reference=reference,complements=complements,
        categories=deepcopy(cfg['categories']),identites=[{'id':str(p.pk),'naissance':str(p.date_naissance) if p.date_naissance else '', 'precision':p.precision_naissance} for p in personnes],source=source,auteur=acteur,remplace=precedent,**valeurs)
    c.full_clean();c.save();c.identifies.set(ids)
    m.JournalCollectif.objects.create(composition=c,action='Composition déclarée',avant=photo_comp(precedent) if precedent else {},apres=photo_comp(c),auteur=acteur)
    if actualiser:
        if not isinstance(objet,m.Accompagnement):raise ValidationError('La composition est déjà celle du ménage.')
        derniere=m.CompositionCollective.objects.filter(menage=menage,service=c.service,accompagnement__isnull=True,annule_le__isnull=True).order_by('-debut','-pk').first()
        if derniere and derniere.debut>debut:raise ValidationError('Une déclaration plus récente du ménage existe ; elle est conservée.')
        copie=m.CompositionCollective.objects.create(menage=menage,service=c.service,debut=debut,reference=reference,
            complements=deepcopy(complements),categories=deepcopy(c.categories),identites=deepcopy(c.identites),source=source,auteur=acteur,remplace=derniere,**valeurs)
        copie.identifies.set(ids)
        m.JournalCollectif.objects.create(composition=copie,action='Reprise explicite depuis la prise',avant=photo_comp(derniere) if derniere else {},apres=photo_comp(copie),auteur=acteur)
    return c

def verifier_version(p,v):
    from .hebergement import verifier_periode
    a=p.accompagnement
    if v.debut<a.debut or (a.fin and (v.fin_prevue is None or v.fin_prevue>a.fin)):
        raise ValidationError('La période doit rester dans la prise en charge.')
    if v.fin_prevue and v.fin_prevue<v.debut or v.fin and v.fin<v.debut:raise ValidationError('La fin précède le début.')
    if v.fin and v.fin>timezone.localdate():raise ValidationError('Une fin effective ne peut pas être future.')
    if p.nature=='hebergement':
        for fin in (v.fin,v.fin_prevue):
            if fin and fin<=v.debut:raise ValidationError('Un hébergement comporte au moins une nuit.')
        if v.arrivee and (v.arrivee<v.debut or v.arrivee>timezone.localdate()):raise ValidationError('Arrivée effective invalide.')
        if v.fin and (not v.arrivee or v.fin<=v.arrivee or v.fin>timezone.localdate()):raise ValidationError('Départ effectif invalide.')
        if v.lieu and not v.arrivee:raise ValidationError('Le lieu effectif exige une arrivée enregistrée.')
    else:
        actifs=[x for x in ('dejeuner','diner') if getattr(v,x)]
        if not actifs or v.premier not in actifs or v.dernier not in actifs:raise ValidationError('Choisissez les repas activés et les bornes correspondantes.')
        if v.fin and v.fin==v.debut and v.premier=='diner' and v.dernier=='dejeuner':raise ValidationError('Le dernier repas précède le premier.')
    if not re.fullmatch('[A-Z]{3}',v.devise):raise ValidationError('Devise sur trois lettres majuscules attendue.')

def valeurs_version(v):return {k:getattr(v,k) for k in VERSION}

def exiger_actuelle(p):
    v=p.courante
    if not v or v.action=='annulation' or p.nature!='hebergement' or not v.arrivee or v.fin:
        raise ValidationError('Choisissez un hébergement arrivé, non terminé et non annulé.')
    return v

@service_metier
@transaction.atomic
def mouvement(acteur,p,action,attendu,debut,fin=None,lieu=None):
    suivi.exiger(acteur,'change_prestationcollective','view_prestationcollective','view_versionprestationcollective','add_mouvementcollectif','view_mouvementcollectif')
    m.Menage.objects.filter(pk=p.accompagnement.menage_id).update(revision=F('revision')+1)
    p=m.PrestationCollective.objects.get(pk=p.pk);verifier_jeton(p,attendu);v=exiger_actuelle(p)
    if debut<v.arrivee or debut>timezone.localdate() or fin and (fin<=debut or fin>timezone.localdate()):raise ValidationError('Période effective de mouvement invalide.')
    if action not in ('lieu','absence'):raise ValidationError('Mouvement inconnu.')
    if action=='lieu':
        suivi.exiger(acteur,'view_lieuhebergement')
        if not lieu:raise ValidationError('Choisissez le lieu commun.')
    elif lieu:raise ValidationError('Une absence n’attribue pas de lieu.')
    q=p.mouvements.filter(nature=action,annule_le__isnull=True)
    if action=='absence':
        q=q.filter(Q(fin__isnull=True)|Q(fin__gt=debut))
        if fin:q=q.filter(debut__lt=fin)
        if q.exists():raise ValidationError('Cette absence chevauche une absence du groupe.')
    elif q.filter(debut__gte=debut).exists():raise ValidationError('Un changement de lieu plus récent existe ; corrigez son histoire.')
    x=m.MouvementCollectif(prestation=p,nature=action,debut=debut,fin=fin,lieu=lieu,auteur=acteur)
    x.full_clean();x.save();p.revision+=1;p.save(update_fields=['revision'])
    m.JournalCollectif.objects.create(prestation=p,mouvement=x,action=action,apres={'debut':str(debut),'fin':str(fin),'lieu':str(lieu.pk) if lieu else None},auteur=acteur)
    return x

@service_metier
@transaction.atomic
def reviser_mouvement(acteur,p,mouvement,attendu,date=None,annuler=False,motif=''):
    suivi.exiger(acteur,'change_prestationcollective','change_mouvementcollectif','view_mouvementcollectif','view_versionprestationcollective')
    m.Menage.objects.filter(pk=p.accompagnement.menage_id).update(revision=F('revision')+1)
    p=m.PrestationCollective.objects.get(pk=p.pk);verifier_jeton(p,attendu)
    if p.courante.action=='annulation':raise ValidationError('La prestation est annulée.')
    x=m.MouvementCollectif.objects.get(pk=mouvement.pk,prestation=p)
    if x.annule_le:raise ValidationError('Mouvement déjà annulé.')
    avant={'debut':str(x.debut),'fin':str(x.fin),'annule':False}
    if annuler:
        if not motif.strip():raise ValidationError('Expliquez l’annulation.')
        x.annule_le=timezone.now();x.save(update_fields=['annule_le'])
    else:
        if x.nature!='absence' or x.fin or not date or date<=x.debut or date>timezone.localdate():raise ValidationError('Retour d’absence invalide.')
        x.fin=date;x.save(update_fields=['fin'])
    p.revision+=1;p.save(update_fields=['revision'])
    m.JournalCollectif.objects.create(prestation=p,mouvement=x,action='Annulation de mouvement' if annuler else 'Retour d’absence',avant=avant,apres={'fin':str(x.fin),'annule':annuler,'motif':motif},auteur=acteur)
    return x

def tarifs_proposes(acteur,prestataire,jour,categories,devise):
    if not acteur.has_perms(['personnes.view_tarifprestation','personnes.view_versiontarif']):return {}
    from .financements import applicable
    resultat={}
    for t in m.TarifPrestation.objects.all():
        v=applicable(t,jour)
        if v and v.actif and v.unite=='repas' and v.devise==devise and v.prestataire_id==prestataire:
            for cat in categories:
                if v.categorie==cat['libelle']:resultat.setdefault(cat['code'],[]).append(v)
    # Plusieurs tarifs compatibles : aucun choix silencieux.
    return {code:lignes[0] for code,lignes in resultat.items() if len(lignes)==1}

@service_metier
@transaction.atomic
def creer(acteur,accompagnement,nature,comp,attendu,couverts,selection=None,reference_selection=None,**valeurs):
    suivi.exiger(acteur,'view_prestationcollective','add_prestationcollective','view_versionprestationcollective','view_couvertcollectif','view_compositioncollective')
    # Le jeton de création est lié à la prise, composition et configuration.
    verifier_jeton(accompagnement,attendu)
    if m.Menage.objects.filter(pk=accompagnement.menage_id,revision=accompagnement.menage.revision).update(revision=F('revision')+1)!=1:
        raise ValidationError('Le ménage a changé ; rechargez.')
    cfg=profil(accompagnement)
    if nature not in dict(m.PrestationCollective.NATURES) or not cfg or cfg[nature]=='individuel':raise ValidationError('Cette famille utilise le parcours individuel.')
    if comp.menage_id!=accompagnement.menage_id or comp.service_id!=service_objet(accompagnement).pk or comp.accompagnement_id not in (None,accompagnement.pk) or comp.annule_le:
        raise ValidationError('Composition étrangère ou annulée.')
    if selection is not None:
        if cfg[nature]!='option':raise PermissionDenied('Ce service ne propose pas de sélection individuelle pour cette famille.')
        suivi.exiger(acteur,'add_compositioncollective')
        ids={p.pk for p in selection}
        if not ids or not ids.issubset(set(comp.identifies.values_list('pk',flat=True))) or not reference_selection or reference_selection.pk not in ids:
            raise ValidationError('Choisissez les personnes identifiées concernées et leur personne de référence.')
        # Photographie propre à cette prestation, sans changer le ménage ni la prise.
        sous=m.CompositionCollective.objects.create(menage=comp.menage,accompagnement=accompagnement,service=comp.service,
            debut=valeurs.get('debut',comp.debut),reference=reference_selection,pour_prestation=True,
            categories=deepcopy(comp.categories),complements=[],identites=[x for x in comp.identites if x['id'] in {str(pk) for pk in ids}],auteur=acteur)
        sous.identifies.set(ids);comp=sous
    p=m.PrestationCollective.objects.create(accompagnement=accompagnement,nature=nature,auteur=acteur)
    _version(acteur,p,comp,'creation',couverts,valeurs)
    return p

def _version(acteur,p,comp,action,couverts,valeurs,motif=''):
    if set(valeurs)-set(VERSION):raise ValidationError('Champ de prestation inconnu.')
    v=m.VersionPrestationCollective(prestation=p,composition=comp,numero=p.revision+1,action=action,auteur=acteur,motif=motif,**valeurs)
    verifier_version(p,v);v.full_clean();v.save()
    if not isinstance(couverts,list) or len(couverts)>9:raise ValidationError('Couverts invalides.')
    categories={c['code']:c['libelle'] for c in comp.categories};categories['inconnu']='Âge non précisé';vus=set()
    for x in couverts:
        if set(x)-{'categorie','nombre','prix','tarif'} or x['categorie'] not in categories or x['categorie'] in vus:raise ValidationError('Catégories de couverts invalides.')
        vus.add(x['categorie']);nombre=x['nombre']
        if type(nombre) is not int or not 0<=nombre<=1000:raise ValidationError('Couverts : entier de 0 à 1000 attendu.')
        prix=x.get('prix');tarif=x.get('tarif')
        if tarif and (prix!=tarif.montant or tarif.devise!=v.devise or tarif.categorie!=categories[x['categorie']] or tarif.prestataire_id not in (None,v.prestataire_id)):
            raise ValidationError('Le prix particulier doit être détaché de la référence tarifaire.')
        if tarif:
            suivi.exiger(acteur,'view_tarifprestation','view_versiontarif')
            from .financements import applicable
            precedent=p.versions.filter(numero__lt=v.numero).order_by('-numero').first()
            conserve=action=='correction' and precedent and precedent.debut==v.debut and precedent.couverts.filter(categorie=x['categorie'],tarif=tarif,prix=prix).exists()
            applique=applicable(tarif.tarif,v.debut)
            if not conserve and (not tarif.actif or not applique or applique.pk!=tarif.pk):raise ValidationError('Ce tarif n’est pas applicable à la date choisie ; saisissez un prix particulier explicite.')
        c=m.CouvertCollectif(version=v,categorie=x['categorie'],libelle=categories[x['categorie']],nombre=nombre,prix=prix,tarif=tarif)
        c.full_clean();c.save()
    if p.nature=='restauration' and not any(x['nombre'] for x in couverts):raise ValidationError('Renseignez au moins un couvert.')
    p.revision+=1;p.save(update_fields=['revision'])
    m.JournalCollectif.objects.create(prestation=p,action=action,apres={'version':v.pk},auteur=acteur)
    return v

@service_metier
@transaction.atomic
def modifier(acteur,p,attendu,action,couverts=None,motif='',**valeurs):
    suivi.exiger(acteur,'view_prestationcollective','change_prestationcollective','view_versionprestationcollective','view_couvertcollectif')
    # Même ordre de réservation que les autres prestations : ménage avant prestation.
    m.Menage.objects.filter(pk=p.accompagnement.menage_id).update(revision=F('revision')+1)
    p=m.PrestationCollective.objects.get(pk=p.pk);verifier_jeton(p,attendu)
    if m.PrestationCollective.objects.filter(pk=p.pk,revision=p.revision).update(revision=F('revision')+1)!=1:raise ValidationError('Prestation modifiée ; rechargez.')
    v=p.courante
    if v.action=='annulation':raise ValidationError('La prestation est annulée.')
    if action not in ('correction','prolongation','depart','annulation'):raise ValidationError('Action inconnue.')
    d=valeurs_version(v)
    if action=='annulation':
        if not motif.strip():raise ValidationError('Expliquez l’annulation.')
        valeurs={}
    if action=='prolongation':
        if v.fin or set(valeurs)!={'fin_prevue'} or not v.fin_prevue or valeurs['fin_prevue']<=v.fin_prevue:raise ValidationError('La nouvelle fin prévue doit prolonger une période non terminée.')
    if action=='depart' and (set(valeurs)!={'fin'} or v.fin):raise ValidationError('Renseignez un premier départ effectif.')
    d.update(valeurs)
    for x in p.mouvements.filter(annule_le__isnull=True):
        if d['arrivee'] and x.debut<d['arrivee'] or d['fin'] and (x.debut>=d['fin'] or x.fin and x.fin>d['fin']):
            raise ValidationError('La période exclurait un mouvement enregistré ; corrigez ce mouvement d’abord.')
        if action=='depart' and x.nature=='absence' and x.fin is None:
            avant={'fin':None};x.fin=d['fin'];x.save(update_fields=['fin'])
            m.JournalCollectif.objects.create(prestation=p,mouvement=x,action='Absence close au départ',avant=avant,apres={'fin':str(x.fin)},auteur=acteur)
    if couverts is None:couverts=[{'categorie':c.categorie,'nombre':c.nombre,'prix':c.prix,'tarif':c.tarif} for c in v.couverts.all()]
    return _version(acteur,p,v.composition,action,couverts,d,motif)

def bilan(v,debut,fin):
    """Volumes calculés dans [debut, fin[, jamais distributions pointées."""
    if fin<=debut:raise ValidationError('La fin du bilan doit suivre son début.')
    if (fin-debut).days>3660:raise ValidationError('Bilan limité à dix ans.')
    r={'nuits':0,'personnes_nuitees_declarees':0,'petits_dejeuners':0,'dejeuners':0,'diners':0,'repas':0,'cout':Decimal('0'),'prix_inconnus':False}
    if v.action=='annulation':return r
    jours=range((fin-debut).days)
    if v.prestation.nature=='hebergement':
        if not v.arrivee:return r
        borne=v.fin or fin
        r['nuits']=max(0,(min(fin,borne)-max(debut,v.arrivee)).days)
        r['personnes_nuitees_declarees']=r['nuits']*sum(effectifs(v.composition,v.composition.debut).values())
        if v.petits_dejeuners:
            r['petits_dejeuners']=sum(v.arrivee<debut+timedelta(days=i)<=borne for i in jours)
            for c in v.couverts.all():
                r['repas']+=r['petits_dejeuners']*c.nombre
                if c.prix is None and c.nombre:r['prix_inconnus']=True
                elif c.prix is not None:r['cout']+=(r['petits_dejeuners']*c.nombre*c.prix).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        return r
    borne=v.fin or v.fin_prevue
    for i in jours:
        jour=debut+timedelta(days=i)
        if jour<v.debut or borne and jour>borne:continue
        for repas in ('dejeuner','diner'):
            if not getattr(v,repas):continue
            if jour==v.debut and v.premier=='diner' and repas=='dejeuner':continue
            if borne and jour==borne and v.dernier=='dejeuner' and repas=='diner':continue
            r['dejeuners' if repas=='dejeuner' else 'diners']+=1
    services=r['dejeuners']+r['diners']
    for c in v.couverts.all():
        r['repas']+=services*c.nombre
        if c.prix is None and c.nombre:r['prix_inconnus']=True
        elif c.prix is not None:r['cout']+=(services*c.nombre*c.prix).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
    return r
