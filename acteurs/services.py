"""Opérations explicites, atomiques et journalisées sur l'organisation et les relais."""
from datetime import datetime, time
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from .models import *
from . import politique as p


class Conflit(ValidationError): pass


def exiger_gestion(compte):
    if not compte.is_active or not compte.has_perm('acteurs.gerer_organisation'):
        raise PermissionDenied('La configuration des accès nécessite une autorisation explicite.')


def journal(compte, service, action, avant, apres, dossier=None, date=None):
    return JournalAcces.objects.create(auteur=compte, service=service, action=action,
        avant=avant, apres=apres, dossier=dossier, date_effet=date or timezone.localdate())


def jeton(objet): return signing.dumps([str(objet.pk), objet.revision], salt='acteurs-etat-v1')


def reserver(objet, attendu):
    try: pk, revision = signing.loads(attendu, salt='acteurs-etat-v1', max_age=86400)
    except (signing.BadSignature, ValueError, TypeError): raise Conflit('Formulaire expiré ; rechargez avant de confirmer.')
    if pk != str(objet.pk) or type(objet).objects.filter(pk=objet.pk, revision=revision).update(revision=F('revision')+1) != 1:
        raise Conflit('La situation a changé ; rechargez avant de confirmer.')
    objet.refresh_from_db()


@transaction.atomic
def changer_politique(compte, service, politique, attendu):
    exiger_gestion(compte)
    reserver(service, attendu)
    if politique not in dict(Service.POLITIQUES): raise ValidationError('Politique inconnue.')
    avant = service.politique
    service.politique = politique; service.full_clean(); service.save(update_fields=['politique'])
    journal(compte, service, 'politique', {'politique':avant}, {'politique':politique})


@transaction.atomic
def habiliter(compte, cible, service, tache, debut, fin=None, **options):
    exiger_gestion(compte)
    if set(options) - {'statistiques_service','statistiques_etablissement','exporter','corriger_autrui'}:
        raise ValidationError('Option d’habilitation inconnue.')
    if not cible.is_active or tache not in dict(Habilitation.TACHES): raise ValidationError('Compte inactif ou tâche inconnue.')
    prof = p.professionnel(cible)
    if not prof or not AppartenanceProfessionnelle.objects.filter(p.periode(debut), professionnel_id=prof, service=service).exists():
        raise ValidationError('Reliez explicitement ce compte à un professionnel membre du service.')
    q = Habilitation.objects.filter(compte=cible, service=service, tache=tache, revoque_le__isnull=True).filter(Q(fin__isnull=True)|Q(fin__gt=debut))
    if fin: q=q.filter(debut__lt=fin)
    if q.exists(): raise ValidationError('Une habilitation pour cette tâche recouvre déjà cette période.')
    x=Habilitation(compte=cible,service=service,tache=tache,debut=debut,fin=fin,accorde_par=compte,**options)
    x.full_clean();x.save()
    journal(compte,service,'habilitation',{}, {'id':x.pk,'compte':cible.pk,'tache':tache,'debut':str(debut),'fin':str(fin),**options})
    return x


@transaction.atomic
def revoquer(compte, habilitation, attendu):
    exiger_gestion(compte);reserver(habilitation,attendu)
    if habilitation.revoque_le: raise Conflit('Cette habilitation est déjà révoquée.')
    habilitation.revoque_le=timezone.now();habilitation.save(update_fields=['revoque_le'])
    journal(compte,habilitation.service,'revocation',{'habilitation':habilitation.pk},{'revoque_le':habilitation.revoque_le.isoformat()})


def selection_cible(dossier, objet):
    from personnes.models import Accompagnement, AccordHebergement, AccordRepas, AccordAide
    champs={'prise':None,'hebergement':None,'repas':None,'aide':None}
    if isinstance(objet,DossierService):
        if objet.pk!=dossier.pk:raise ValidationError('Dossier étranger.')
        return champs
    champ={Accompagnement:'prise',AccordHebergement:'hebergement',AccordRepas:'repas',AccordAide:'aide'}.get(type(objet))
    if not champ:raise ValidationError('Ce niveau ne porte pas de responsabilité.')
    origine=p.PorteeObjet.objects.filter(modele=objet._meta.label_lower,identifiant=str(objet.pk),dossier=dossier).first()
    if not origine:raise ValidationError('Cette cible n’appartient pas à ce dossier et à ce service.')
    champs[champ]=objet
    return champs


def instant(date):
    if isinstance(date,datetime):return date
    if date==timezone.localdate():return timezone.now()
    return timezone.make_aware(datetime.combine(date,time.min))


def responsables(dossier, objet, quand=None):
    return Responsabilite.objects.filter(p.periode(quand or timezone.now()), annule_le__isnull=True, dossier=dossier, **selection_cible(dossier,objet))


def verifier_professionnel(prof,service,date):
    if not AppartenanceProfessionnelle.objects.filter(p.periode(date),professionnel=prof,service=service).exists():
        raise ValidationError('Choisissez un professionnel membre de ce service à cette date.')


@transaction.atomic
def commencer(compte,dossier,attendu):
    # La première requête réserve l'agrégat, y compris sur SQLite.
    reserver(dossier,attendu)
    if not p.habilitations(compte).filter(service=dossier.service,tache='social').exists():raise PermissionDenied
    if not dossier.en_attente:raise Conflit('Un suivi a déjà commencé ; rechargez pour rejoindre ce suivi selon vos droits.')
    prof=p.professionnel(compte)
    x=Responsabilite.objects.create(dossier=dossier,professionnel_id=prof,cree_par=compte)
    dossier.en_attente=False;dossier.save(update_fields=['en_attente'])
    journal(compte,dossier.service,'commencer',{}, {'responsabilite':x.pk,'professionnel':str(prof)},dossier)
    return x


def proposition_relais(compte,dossier,objet,descendants=True,sortant=None,date=None):
    if not p.habilitations(compte).filter(service=dossier.service).exists():raise PermissionDenied
    p.exiger_objet(compte,dossier.personne or dossier.menage)
    date=instant(date or timezone.now());sortant=sortant or p.professionnel(compte)
    bases=responsables(dossier,objet,date).filter(professionnel_id=sortant)
    ids=set(bases.values_list('pk',flat=True))
    if descendants:
        from personnes.models import Accompagnement
        rs=Responsabilite.objects.filter(p.periode(date),annule_le__isnull=True,dossier=dossier,professionnel_id=sortant)
        if isinstance(objet,DossierService):
            rs=rs.filter(Q(prise__fin__isnull=True)|Q(prise__isnull=True))
        elif isinstance(objet,Accompagnement):
            rs=rs.filter(Q(prise=objet)|Q(hebergement__accompagnement=objet)|Q(repas__accompagnement=objet)|Q(aide__accompagnement=objet))
        else:rs=bases
        for r in rs.select_related('prise','hebergement','repas','aide'):
            cible=r.cible
            # Une prestation échue, annulée ou une prise terminée garde son histoire.
            if not en_cours(cible,date):continue
            ids.add(r.pk)
    contenu={'dossier':str(dossier.pk),'revision':dossier.revision,'ids':sorted(ids),'sortant':str(sortant),'date':date.isoformat()}
    return list(Responsabilite.objects.filter(pk__in=ids).select_related('professionnel','prise','hebergement','repas','aide')), signing.dumps(contenu,salt='acteurs-relais-v1')


@transaction.atomic
def relayer(compte,dossier,entrant,attendu,proposition):
    reserver(dossier,attendu)
    try:d=signing.loads(proposition,salt='acteurs-relais-v1',max_age=3600);date=datetime.fromisoformat(d['date'])
    except (signing.BadSignature,KeyError,ValueError,TypeError):raise Conflit('Proposition de relais expirée ; recommencez.')
    if d['dossier']!=str(dossier.pk) or d['revision']+1!=dossier.revision:raise Conflit('Le suivi a changé.')
    hs=p.habilitations(compte).filter(service=dossier.service,tache__in=['social','accueil','gestion'])
    if not hs.exists():raise PermissionDenied
    if d['sortant']!=str(p.professionnel(compte)) and not hs.filter(corriger_autrui=True).exists():raise PermissionDenied('La reprise du suivi d’un collègue nécessite le droit correspondant.')
    verifier_professionnel(entrant,dossier.service,date.date())
    if str(entrant.pk)==d['sortant']:raise ValidationError('Choisissez une autre personne pour le relais.')
    lignes=list(Responsabilite.objects.filter(pk__in=d['ids'],dossier=dossier,professionnel_id=d['sortant'],annule_le__isnull=True).filter(p.periode(date)))
    if len(lignes)!=len(d['ids']) or not lignes:raise Conflit('Une responsabilité a changé ou aucune responsabilité ne correspond.')
    if any(x.prise_id or not (x.hebergement_id or x.repas_id or x.aide_id) for x in lignes) and not hs.filter(tache='social').exists():raise PermissionDenied
    avant=[];apres=[]
    for x in lignes:
        if date<=x.debut:raise ValidationError('Le relais doit suivre le début de la responsabilité.')
        if not en_cours(x.cible,date):raise Conflit('Cet élément est terminé ; rechargez le suivi.')
        cible=selection_cible(dossier,x.cible)
        if Responsabilite.objects.filter(p.periode(date),annule_le__isnull=True,dossier=dossier,professionnel=entrant,**cible).exists():
            raise ValidationError('Le collègue intervient déjà à ce niveau ; terminez votre intervention séparément.')
        x.fin=date;x.full_clean();x.save(update_fields=['fin'])
        y=Responsabilite(dossier=dossier,professionnel=entrant,debut=date,role=x.role,cree_par=compte,**cible);y.full_clean();y.save()
        avant.append(x.pk);apres.append(y.pk)
    journal(compte,dossier.service,'relais',{'responsabilites':avant,'professionnel':d['sortant']},
        {'responsabilites':apres,'professionnel':str(entrant.pk)},dossier,date.date())
    oublier_initialisation(dossier,lignes)
    return apres


def proposer_responsabilites(compte,objet,dossier):
    """Copie à la création, jamais une filiation réécrivant les épisodes anciens."""
    from personnes.models import Accompagnement
    from .contexte import courant
    choisi=courant().responsable_id if courant() else None
    if isinstance(objet,Accompagnement) and not choisi and dossier.service_id not in set(p.pleines(compte,True)) and not p.missions(compte).filter(dossier=dossier,prise__isnull=True,hebergement__isnull=True,repas__isnull=True,aide__isnull=True).exists():choisi=p.professionnel(compte)
    if isinstance(objet,Accompagnement) and not choisi:
        source=responsables(dossier,dossier)
        for x in source:
            Responsabilite.objects.create(dossier=dossier,professionnel=x.professionnel,prise=objet,role=x.role,cree_par=compte)
    else:
        prof=choisi or p.professionnel(compte)
        if prof:Responsabilite.objects.create(dossier=dossier,professionnel_id=prof,cree_par=compte,**selection_cible(dossier,objet))


def qualifier_hebergement(etablissement,lieu,date):
    vus=set();xs=[]
    while lieu and lieu.pk not in vus:
        vus.add(lieu.pk)
        xs=list(ExploitationLieu.objects.filter(p.periode(date),lieu=lieu).select_related('etablissement'))
        if xs:break
        lieu=lieu.parent
    if len(xs)!=1:return 'Non déterminé'
    x=xs[0]
    if x.organisme_exterieur_id==etablissement.organisme.organisme_id:return 'Non déterminé'
    if x.etablissement_id==etablissement.pk:return 'Même établissement'
    if x.etablissement_id and x.etablissement.organisme_id==etablissement.organisme_id:return 'Autre établissement du même organisme'
    return 'Organisme extérieur'


@transaction.atomic
def inscrire(compte,service,professionnel,debut,fin=None,fonction='',cible_compte=None):
    exiger_gestion(compte)
    Service.objects.filter(pk=service.pk).update(revision=F('revision')+1)
    x=AppartenanceProfessionnelle(professionnel=professionnel,service=service,debut=debut,fin=fin,fonction=fonction)
    x.full_clean();x.save()
    if cible_compte:
        if not cible_compte.is_active:raise ValidationError('Compte inactif.')
        lien= LienCompteProfessionnel.objects.filter(Q(compte=cible_compte)|Q(professionnel=professionnel)).first()
        if lien and (lien.compte_id!=cible_compte.pk or lien.professionnel_id!=professionnel.pk):
            raise ValidationError('Ce compte ou ce professionnel est déjà relié autrement ; aucun rapprochement automatique.')
        if not lien:LienCompteProfessionnel.objects.create(compte=cible_compte,professionnel=professionnel)
    journal(compte,service,'appartenance',{}, {'id':x.pk,'professionnel':str(professionnel.pk),'compte':cible_compte.pk if cible_compte else None,'debut':str(debut),'fin':str(fin)})
    return x


@transaction.atomic
def terminer_responsabilite(compte,x,date,attendu):
    dossier=x.dossier;reserver(dossier,attendu)
    hs=p.habilitations(compte).filter(service=dossier.service,tache__in=['social','accueil','gestion'])
    p.exiger_objet(compte,dossier.personne or dossier.menage)
    if (x.prise_id or not(x.hebergement_id or x.repas_id or x.aide_id)) and not hs.filter(tache='social').exists():raise PermissionDenied
    if not hs.exists() or (x.professionnel_id!=p.professionnel(compte) and not hs.filter(corriger_autrui=True).exists()):raise PermissionDenied
    x.refresh_from_db();date=instant(date)
    if x.fin or x.annule_le or date<=x.debut:raise ValidationError('Cette responsabilité est déjà terminée ou sa fin est invalide.')
    x.fin=date;x.full_clean();x.save(update_fields=['fin'])
    journal(compte,dossier.service,'fin_responsabilite',{'id':x.pk},{'fin':date.isoformat()},dossier,date.date())
    oublier_initialisation(dossier,[x])


def peut_attribuer(compte,dossier,objet):
    from personnes.models import Accompagnement
    hs=p.habilitations(compte).filter(service=dossier.service)
    if isinstance(objet,(DossierService,Accompagnement)) and not hs.filter(tache='social').exists():return False
    if not hs.filter(tache__in=['social','accueil','gestion']).exists():return False
    if isinstance(objet,DossierService):
        origine=PorteeObjet(service=dossier.service,dossier=dossier)
        return p.peut_renseigner(compte,origine,type(dossier.personne or dossier.menage))
    try:p.exiger_objet(compte,objet,True)
    except PermissionDenied:return False
    return True


@transaction.atomic
def ajouter_responsabilite(compte,dossier,objet,professionnel,debut,role,attendu,fin=None):
    reserver(dossier,attendu)
    if not peut_attribuer(compte,dossier,objet):raise PermissionDenied
    champs=selection_cible(dossier,objet)
    date=instant(debut)
    verifier_professionnel(professionnel,dossier.service,date.date())
    if not en_cours(objet,date):
        raise ValidationError('Cet élément est terminé ; son historique reste conservé.')
    if Responsabilite.objects.filter(p.periode(date),annule_le__isnull=True,dossier=dossier,professionnel=professionnel,**champs).exists():
        raise ValidationError('Cette personne intervient déjà à ce niveau.')
    borne=timezone.make_aware(datetime.combine(fin,time.min)) if fin else None
    if borne and borne<=date:raise ValidationError('La fin exclue doit suivre le début de l’intervention.')
    x=Responsabilite(dossier=dossier,professionnel=professionnel,debut=date,fin=borne,role=role,cree_par=compte,**champs)
    x.full_clean();x.save()
    if isinstance(objet,DossierService):
        dossier.en_attente=False;dossier.save(update_fields=['en_attente'])
    journal(compte,dossier.service,'ajout_responsabilite',{}, {'id':x.pk,'professionnel':str(professionnel.pk),'role':role,'debut':date.isoformat(),'fin':borne.isoformat() if borne else None},dossier,date.date())
    return x


@transaction.atomic
def changer_exploitation(compte,service,lieu,debut,etablissement=None,organisme_exterieur=None,interlocuteur=None,attendu=None):
    exiger_gestion(compte)
    from personnes.models import LieuHebergement
    # Verrou commun au lieu : deux services ne peuvent définir deux exploitants
    # concurrents sur un même lieu physique.
    LieuHebergement._base_manager.filter(pk=lieu.pk).update(revision_sociale=F('revision_sociale')+1)
    reserver(service,attendu)
    if ExploitationLieu.objects.filter(lieu=lieu,debut__gte=debut).exists():
        raise ValidationError('Une exploitation existe déjà à cette date ou après ; ne réécrivez pas son histoire.')
    ouverts=list(ExploitationLieu.objects.filter(lieu=lieu,debut__lt=debut).filter(Q(fin__isnull=True)|Q(fin__gt=debut)))
    avant=[]
    for x in ouverts:
        avant.append({'id':x.pk,'fin':str(x.fin)});x.fin=debut;x.full_clean();x.save(update_fields=['fin'])
    x=ExploitationLieu(lieu=lieu,debut=debut,etablissement=etablissement,organisme_exterieur=organisme_exterieur,interlocuteur=interlocuteur)
    x.full_clean();x.save()
    journal(compte,service,'exploitation_lieu',{'periodes':avant},{'id':x.pk,'lieu':lieu.pk,'debut':str(debut),
        'etablissement':etablissement.pk if etablissement else None,'organisme':str(organisme_exterieur.pk) if organisme_exterieur else None})
    return x


def oublier_initialisation(dossier,lignes):
    """L'aide à l'initialisation ne conserve pas de droits après un relais."""
    from .contexte import courant
    ctx=courant()
    if not ctx:return
    condition=Q(pk__in=[])
    for x in lignes:
        if x.prise_id:condition|=Q(prise_id=x.prise_id)
        elif x.hebergement_id:condition|=Q(prestation_modele='accordhebergement',prestation_id=x.hebergement_id)
        elif x.repas_id:condition|=Q(prestation_modele='accordrepas',prestation_id=x.repas_id)
        elif x.aide_id:condition|=Q(prestation_modele='accordaide',prestation_id=x.aide_id)
        else:condition|=Q(dossier=dossier)
    ctx.nouveaux.difference_update(PorteeObjet.objects.filter(condition,dossier=dossier).values_list('modele','identifiant'))


def en_cours(objet, quand):
    """Une fin d'accord n'est pas la sortie effective d'un hébergement."""
    from personnes.models import AccordHebergement
    jour=timezone.localtime(quand).date() if isinstance(quand,datetime) and timezone.is_aware(quand) else quand.date() if isinstance(quand,datetime) else quand
    if getattr(objet,'annule_le',None):return False
    prise=getattr(objet,'accompagnement',None)
    if prise and prise.fin and prise.fin<=jour:return False
    if isinstance(objet,AccordHebergement) and objet.sejours.non_annules().filter(debut__lte=jour).filter(Q(fin__isnull=True)|Q(fin__gt=jour)).exists():return True
    fin=getattr(objet,'fin',None)
    return not fin or fin>jour


@transaction.atomic
def terminer_prise(compte, prise, fin):
    """Fin d'accès maintenant si la clôture métier est rétrospective.

    Appelé après le journal métier et dans sa transaction. Les responsabilités
    du dossier restent distinctes. Une mission future exclue est annulée, gardée.
    """
    if not p.active():return
    quand=max(timezone.now(),timezone.make_aware(datetime.combine(fin,time.min)))
    rs=Responsabilite.objects.filter(Q(prise=prise)|Q(hebergement__accompagnement=prise)|Q(repas__accompagnement=prise)|Q(aide__accompagnement=prise),annule_le__isnull=True).filter(Q(fin__isnull=True)|Q(fin__gt=quand))
    dossiers=list(DossierService.objects.filter(pk__in=rs.values('dossier_id')).order_by('pk'))
    for dossier in dossiers:
        # Même réservation que le relais : une confirmation antérieure est périmée.
        DossierService.objects.filter(pk=dossier.pk).update(revision=F('revision')+1)
        courantes=list(rs.filter(dossier=dossier,debut__lt=quand).values_list('pk',flat=True))
        futures=list(rs.filter(dossier=dossier,debut__gte=quand).values_list('pk',flat=True))
        Responsabilite.objects.filter(pk__in=courantes).update(fin=quand)
        Responsabilite.objects.filter(pk__in=futures).update(annule_le=timezone.now())
        journal(compte,dossier.service,'fin_prise',{'responsabilites':courantes,'prevues':futures},
            {'prise':str(prise.pk),'fin_metier':str(fin),'fin_acces':quand.isoformat()},dossier,fin)
    oublier_initialisation_prise(prise)


def oublier_initialisation_prise(prise):
    from .contexte import courant
    ctx=courant()
    if ctx:ctx.nouveaux.difference_update(PorteeObjet.objects.filter(prise=prise).values_list('modele','identifiant'))
