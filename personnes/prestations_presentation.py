"""Projection vers les composants NAV. Aucun modèle de stockage fictif."""
from datetime import timedelta
from urllib.parse import urlencode
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format, number_format
from . import models as m, collectifs as c

LECTURE=('personnes.view_prestationcollective','personnes.view_versionprestationcollective','personnes.view_couvertcollectif','personnes.view_compositioncollective')


def sources(acteur,prises,personne=None):
    if not acteur.has_perms(LECTURE):return []
    valeurs=[]
    for p in m.PrestationCollective.objects.filter(accompagnement__in=prises).prefetch_related('versions__composition__identifies','versions__couverts','mouvements'):
        v=max(p.versions.all(),key=lambda v:v.numero,default=None)
        if not v:continue
        if personne and not any(x.pk==personne.pk for x in v.composition.identifies.all()):continue
        p.version_nav=v;valeurs.append(p)
    return valeurs


def resume_sources(valeurs):
    actifs=[p for p in valeurs if p.version_nav.action!='annulation']
    morceaux=[]
    for nature,label in [('hebergement','Héberg.'),('restauration','Repas')]:
        nombre=sum(p.nature==nature for p in actifs)
        if nombre:morceaux.append(label+' : '+str(nombre)+' période'+('s' if nombre>1 else '')+' accordée'+('s' if nombre>1 else ''))
    return ' · '.join(morceaux)


def initialiser(context):
    if 'prestations_nav' in context:return
    request=context['request'];prise=context.get('prise')
    valeurs=([p for p in context['sources_prestations_nav'] if p.accompagnement_id==prise.pk] if 'sources_prestations_nav' in context else sources(request.user,[prise],context['objet'] if context['nature']=='personne' else None)) if prise else []
    context['prestations_nav']={str(p.pk):p for p in valeurs}
    cfg=c.profil(prise) if prise else None
    context['profil_prestations_nav']=cfg
    for famille,param,selection in [('hebergement','sejour','selection_sejour'),('restauration','repas','selection_repas')]:
        lignes=[p for p in valeurs if p.nature==famille]
        context['lignes_nav_'+famille]=lignes
        identifiant=request.GET.get(param) or context.get('parametres_prestations',{}).get(param)
        choisi=next((p for p in lignes if str(p.pk)==identifiant),None)
        if famille=='hebergement':
            prevus=context.get('hebergements_prevus',[])
            ident_prevu=request.GET.get('prevision') or identifiant
            prevision=next((p for p in prevus if str(p.pk)==ident_prevu),None)
            if not prevision and not context.get(selection) and not lignes and not identifiant:prevision=next(iter(prevus),None)
            if request.GET.get('sejour') and not prevision:
                context['parametres_prestations']['prevision']=''
                context['selection_prevision']=''
            context['selection_nav_prevision']=prevision
            if prevision:
                context['selection_prevision']=str(prevision.pk)
                context['parametres_prestations']['prevision']=str(prevision.pk)
                context[selection]=None
                context['selection_hebergement_collective']=False
        if not choisi and not context.get(selection) and not context.get('selection_nav_prevision') and not identifiant:choisi=next(iter(lignes),None)
        context['selection_nav_'+famille]=choisi
        if choisi:
            context['parametres_prestations'][param]=str(choisi.pk)
            context['navigation_query']=urlencode(context['parametres_prestations'])
            context[selection]=None
            if famille=='hebergement':context['selection_nav_prevision']=None;context['selection_prevision']=''
            if famille=='hebergement':context['selection_hebergement_collective']=False
        historique=bool(context.get('sejours_dossier') or context.get('hebergements_prevus') or context.get('accords_annules_sans_sejour')) if famille=='hebergement' else bool(context.get('accords_repas'))
        lecture=context.get('lecture_hebergement' if famille=='hebergement' else 'lecture_repas')
        propose=not cfg or famille in cfg['prestations']
        detail=not cfg or cfg[famille]=='individuel'
        context['visible_nav_'+famille]=bool(lignes or historique or propose and (lecture if detail else request.user.has_perms(LECTURE)))
        if famille=='restauration':context['suivi_repas_detaille']=detail and propose
    # One ordered list feeds each native family component, irrespective of source.
    context['lignes_repas_nav']=sorted([*context.get('accords_repas',[]),*context['lignes_nav_restauration']],key=lambda x: ((x.version_nav.action=='annulation',-x.version_nav.debut.toordinal(),str(x.pk)) if isinstance(x,m.PrestationCollective) else (bool(x.annule_le),-x.debut.toordinal(),str(x.pk))))
    if context['lignes_nav_hebergement'] or context.get('hebergements_prevus'):
        groupes=[*context.get('groupes_hebergement',[]),*[{'collectif':False,'sejours':[p],'debut':p.version_nav.debut} for p in context['lignes_nav_hebergement']],*[{'collectif':False,'sejours':[p],'debut':p.debut} for p in context.get('hebergements_prevus',[])]]
        def ordre(g):
            sejours=g['sejours']
            dates=[s.version_nav.debut if isinstance(s,m.PrestationCollective) else s.debut for s in sejours]
            fins=[s.version_nav.fin if isinstance(s,m.PrestationCollective) else s.fin for s in sejours]
            return (all(fins),-min(dates).toordinal(),str(sejours[0].pk))
        context['groupes_hebergement']=sorted(groupes,key=ordre)


def date(jour):return date_format(jour,'d/m/Y') if jour else ''

def creation(context,famille):
    initialiser(context)
    from . import prestation_navigation as nav
    cfg=context['profil_prestations_nav'];u=context['request'].user
    nature='repas' if famille=='restauration' else 'hebergement'
    if cfg and famille not in cfg['prestations']:return None
    if cfg and cfg[famille]!='individuel':
        if not u.has_perms((*LECTURE,'personnes.add_prestationcollective')):return None
        cle='nouveau:commun_'+famille
    else:
        if not u.has_perm('personnes.add_accordrepas' if nature=='repas' else 'personnes.add_accordhebergement'):return None
        cle='nouveau:'+nature
    if context.get('prise'):url=nav.adresse(context,cle)
    else:url=reverse('dossiers:nouveau',args=[context['nature'],context['objet'].pk,nature])+'?'+context.get('navigation_query','')
    return {'url':url,'cle':cle,'label':'Nouvelle période de repas' if nature=='repas' else 'Nouveau séjour'}

def ligne(context,objet,genre):
    initialiser(context)
    from . import prestation_navigation as nav
    if isinstance(objet,m.PrestationCollective):genre='commun'
    elif isinstance(objet,m.AccordHebergement):genre='hebergement'
    selection='selection_repas' if genre=='repas' else 'selection_sejour'
    param='repas' if genre=='repas' or genre=='commun' and objet.nature=='restauration' else 'sejour'
    famille='restauration' if param=='repas' else 'hebergement'
    cle=genre+':'+str(objet.pk)
    if genre=='commun':
        v=objet.version_nav
        titre=date(v.debut)+' → '+(date(v.fin or v.fin_prevue) or 'sans fin prévue')
        nombres=c.effectifs(v.composition,v.composition.debut)
        resume=['Annulée' if v.action=='annulation' else 'Terminée' if v.fin else 'En cours' if famille=='restauration' or v.arrivee else 'Prévu — arrivée à confirmer']
        lieu=v.libelle_offre or (str(v.lieu) if v.lieu and context['request'].user.has_perm('personnes.view_lieuhebergement') else str(v.prestataire) if v.prestataire and context['request'].user.has_perm('personnes.view_partenaire') else '')
        if lieu:resume[0]+=' · '+lieu
        if famille=='restauration':titre=('Déjeuner / Dîner' if v.dejeuner and v.diner else 'Déjeuner' if v.dejeuner else 'Dîner')+' · '+titre
        resume.append(str(sum(nombres.values()))+' personnes déclarées')
        if famille=='hebergement' and v.arrivee:
            titre=date(v.arrivee)+' → '+(date(v.fin) or 'en cours')
            if v.fin_prevue:resume.append('Fin prévue : '+date(v.fin_prevue))
        if famille=='restauration' and v.action!='annulation' and (v.fin or v.fin_prevue):
            from django.core.exceptions import ValidationError
            try:
                calcul=c.bilan(v,v.debut,(v.fin or v.fin_prevue)+timedelta(days=1))
                if not calcul['prix_inconnus']:resume.append('Total calculé : '+number_format(calcul['cout'],2)+' '+v.devise)
            except ValidationError:pass
        choisi=context.get('selection_nav_'+famille)==objet
        selection_url=reverse('dossiers:prise',args=[context['nature'],context['objet'].pk,context['prise'].pk])+'?'+urlencode({**context['parametres_prestations'],param:str(objet.pk)})+'#'+('repas' if param=='repas' else 'hebergement')
    else:
        choisi=context.get(selection)==objet
        selection_url=getattr(objet,'selection_url','')
        if genre=='hebergement':
            choisi=context.get('selection_nav_prevision')==objet
            titre=date(objet.debut)+' → '+(date(objet.fin) or 'sans fin prévue')
            resume=['Période échue — arrivée non enregistrée' if objet.fin and objet.fin<=timezone.localdate() else 'Prévu — arrivée à confirmer',' ; '.join(str(p) for p in objet.personnes_attendues)]
        elif genre=='repas':
            titre=objet.get_service_display()+' · '+date(objet.debut)+' → '+(date(objet.fin) or 'sans fin prévue')
            resume=['Annulé' if objet.annule_le else 'À venir' if objet.debut>timezone.localdate() else 'Terminé' if objet.fin and objet.fin<=timezone.localdate() else 'Accord en cours']
        else:
            titre=date(objet.debut)+' → '+(date(objet.fin) or 'en cours')
            etat='Terminé' if objet.fin else 'À venir' if objet.debut>timezone.localdate() else 'Ouvert'
            if context.get('lecture_lieux'):
                lieu=objet.lieu_ouvert.lieu if objet.lieu_ouvert else objet.lieux_dossier[0].lieu if objet.lieux_dossier else 'Lieu non renseigné'
                etat+=' · '+str(lieu)
            resume=[etat]
        if genre!='hebergement':resume.append(' ; '.join(str(p) for p in objet.beneficiaires.all()))
    if context.get('prise') and famille=='hebergement':
        params={**context['parametres_prestations'],'sejour':str(objet.pk),'prevision':''}
        selection_url=reverse('dossiers:prise',args=[context['nature'],context['objet'].pk,context['prise'].pk])+'?'+urlencode(params)+'#hebergement'
    return {'objet':objet,'cle':cle,'genre':genre,'pk':str(objet.pk),'titre':titre,'resume':resume,'param':param,'form':'selection-repas' if param=='repas' else 'selection-hebergement','selected':choisi,'selection_url':selection_url,'ouvrir_url':nav.adresse(context,cle)}

def actions(context,famille):
    """Les nouvelles capacités alimentent la même barre NAV de la sélection."""
    initialiser(context)
    from . import prestation_navigation as nav
    p=context.get('selection_nav_'+famille)
    if not p:return actions_natives(context,famille)
    u=context['request'].user;v=p.version_nav;cle='commun:'+str(p.pk)
    def lien(action,label):
        operation=reverse('dossiers:collectif_action',args=['prise',p.accompagnement_id,action])+'?'+urlencode({'pk':p.pk})
        return {'label':label,'url':nav.adresse(context,cle,operation),'bouton':label in ('Prolonger','Modifier')}
    principaux=[{'label':'Ouvrir','url':nav.adresse(context,cle),'bouton':True}, {'label':'Imprimer / PDF','url':nav.adresse(context,cle,impression=True),'imprimer':True,'bouton':True}]
    autres=[]
    if v.action!='annulation' and u.has_perm('personnes.change_prestationcollective'):
        if v.fin_prevue and not v.fin:principaux.append(lien('prolongation','Prolonger'))
        principaux.insert(1,lien('correction','Modifier'))
        autres=[lien('annulation','Annuler la prestation')]
        if famille=='hebergement' and v.arrivee and not v.fin:
            if u.has_perm('personnes.add_mouvementcollectif'):autres.extend([lien('lieu','Changer de lieu'),lien('absence','Enregistrer une absence')])
            if u.has_perm('personnes.change_mouvementcollectif'):autres.extend([lien('retour','Enregistrer le retour d’absence'),lien('annuler_mouvement','Annuler un mouvement')])
    return {'cle':cle,'resume':str(sum(c.effectifs(v.composition).values()))+' personnes déclarées','principaux':principaux,'autres':autres}


def actions_natives(context,famille):
    from . import prestation_navigation as nav
    objet=context.get('selection_repas' if famille=='restauration' else 'selection_sejour')
    if not objet:
        prevu=context.get('selection_nav_prevision') if famille=='hebergement' else None
        if not prevu:return None
        cle='hebergement:'+str(prevu.pk)
        principaux=[]
        if context['request'].user.has_perm('personnes.add_sejour'):
            principaux.append({'label':'Enregistrer l’arrivée','url':nav.adresse(context,cle,reverse('suivi:arrivee_prevue',args=[prevu.pk])),'bouton':True})
        principaux.extend([{'label':'Ouvrir','url':nav.adresse(context,cle),'bouton':True},{'label':'Imprimer / PDF','url':nav.adresse(context,cle,impression=True),'imprimer':True,'bouton':True}])
        return {'cle':cle,'resume':' ; '.join(str(p) for p in prevu.personnes_attendues),'principaux':principaux,'autres':[]}
    u=context['request'].user;repas=famille=='restauration';cle=('repas:' if repas else 'sejour:')+str(objet.pk)
    accord=objet if repas else objet.accord
    def autorise(*droits):return u.has_perms(['personnes.'+d for d in droits])
    def lien(label,nom,*args):return {'label':label,'url':nav.adresse(context,cle,reverse(nom,args=args)),'bouton':label in ('Prolonger','Enregistrer la sortie','Enregistrer une distribution')}
    principaux=[{'label':'Ouvrir','url':nav.adresse(context,cle),'bouton':True},{'label':'Imprimer / PDF','url':nav.adresse(context,cle,impression=True),'imprimer':True,'bouton':True}]
    autres=[];informations=[]
    if not accord.annule_le and accord.fin and autorise('view_evolutionaccord','prolonger_accordrepas' if repas else 'prolonger_accordhebergement'):
        principaux.append(lien('Prolonger','suivi:prolonger_accord','repas' if repas else 'hebergement',accord.pk))
    if repas:
        if not accord.annule_le and autorise('add_repasdistribue'):principaux.append(lien('Enregistrer une distribution','suivi:distribuer_repas',accord.pk))
        if not accord.annule_le and autorise('change_accordrepas','view_correctionperiode'):autres.append(lien('Corriger les dates de l’accord','suivi:corriger_saisie','accordrepas',accord.pk))
        informations=['Période de suivi du '+date(accord.accompagnement.debut)+'. Un accord ne prouve pas une distribution.']
        if accord.annule_le:informations.append('Accord annulé : '+accord.motif_annulation)
    else:
        if objet.beneficiaires.count()>1 and not objet.fin and autorise('add_continuitesejour'):principaux.insert(0,lien('Poursuivre individuellement','dossiers:individualiser_sejour',objet.pk))
        if not objet.fin and autorise('change_sejour','change_affectation','change_absence'):principaux.append(lien('Enregistrer la sortie','suivi:sortir',objet.pk))
        if not objet.fin:
            if context.get('lecture_lieux'):
                if objet.lieu_ouvert and autorise('change_affectation','add_affectation'):principaux.append(lien('Changer de lieu','suivi:changer_lieu',objet.lieu_ouvert.pk))
                elif not objet.lieu_ouvert and autorise('add_affectation'):principaux.append(lien('Affecter un lieu','suivi:affecter',objet.pk))
            if autorise('view_absence'):
                if objet.absence_ouverte and autorise('change_absence'):principaux.append(lien('Enregistrer le retour d’absence','suivi:clore_absence',objet.absence_ouverte.pk))
                elif not objet.absence_ouverte and autorise('add_absence'):principaux.append(lien('Enregistrer une absence','suivi:absence',objet.pk))
        if autorise('annuler_sejour','view_annulationarrivee'):autres.append(lien('Corriger ou annuler l’arrivée','dossiers:annuler_arrivee',objet.pk))
        if autorise('change_sejour','view_correctionperiode'):autres.append(lien('Corriger les dates du séjour','suivi:corriger_saisie','sejour',objet.pk))
        if autorise('view_notepartagee'):autres.append(lien('Notes du séjour','suivi:notes','sejour',objet.pk))
        informations=['Période de suivi du '+date(accord.accompagnement.debut)+'. Accord jusqu’au '+(date(accord.fin) or 'sans fin prévue')+' (fin exclue).']
        if autorise('view_partenaire') and objet.lieu_ouvert and objet.lieu_ouvert.lieu.organisme_id:informations.insert(0,'Organisme rattaché au lieu : '+str(objet.lieu_ouvert.lieu.organisme))
    noms=' ; '.join(str(p) for p in objet.beneficiaires.all())
    return {'cle':cle,'resume':noms,'principaux':principaux,'autres':autres,'informations':informations,'repli':not repas and context.get('selection_hebergement_collective'),'titre_repli':'Actions individuelles — '+noms+' · '+date(objet.debut)}
