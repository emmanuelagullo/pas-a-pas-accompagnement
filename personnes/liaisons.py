"""Un cahier, des portées explicites ; projection des sources métier autorisées."""
from datetime import timedelta
from urllib.parse import urlencode
from django import forms
from django.core import signing
from django.core.exceptions import PermissionDenied,ValidationError,ObjectDoesNotExist
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from acteurs import politique as p
from acteurs.contexte import courant,perimetre
from acteurs.models import Service,DossierService,PorteeObjet,Responsabilite,JournalAcces
from . import models as m,transmissions,releve

MODELES={'personne':m.Personne,'menage':m.Menage,'prise':m.Accompagnement,
    'hebergement':m.AccordHebergement,'repas':m.AccordRepas,'aide':m.AccordAide,'sejour':m.Sejour}
NATURES={v:k for k,v in MODELES.items()}
NOTES={'prise':'accompagnement','hebergement':'accord_hebergement','repas':'accord_repas','aide':'accord_aide',
    'personne':'personne','menage':'menage','sejour':'sejour'}
TYPES=[('messages','Messages'),('equipe','Équipe'),('prestations','Prestations'),('actions','Actions à faire')]
CLES=('lia_debut','lia_fin','lia_types','lia_sous','lia_q','lia_annules')


class Filtres(forms.Form):
    lia_debut=forms.DateField(label='Du (inclus)',required=False,widget=forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'}))
    lia_fin=forms.DateField(label='Au (exclu)',required=False,widget=forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'}))
    lia_types=forms.MultipleChoiceField(label='Afficher',choices=TYPES,required=False,widget=forms.CheckboxSelectMultiple)
    lia_sous=forms.BooleanField(label='Inclure les niveaux inférieurs',required=False)
    lia_q=forms.CharField(label='Rechercher dans les éléments affichés',max_length=160,required=False,widget=forms.TextInput(attrs={'type':'search'}))
    lia_annules=forms.BooleanField(label='Inclure les messages annulés',required=False)
    def clean(self):
        d=super().clean()
        if d.get('lia_debut') and d.get('lia_fin') and d['lia_fin']<=d['lia_debut']:self.add_error('lia_fin','La fin exclue doit suivre le début.')
        return d


def filtres(donnees,point=None):
    data=donnees.copy();jour=timezone.localdate()
    if point is None or point.nature in ('service','ensemble'):
        data.setdefault('lia_debut',(jour-timedelta(days=30)).isoformat());data.setdefault('lia_fin',(jour+timedelta(days=1)).isoformat())
    if 'lia_filtres' not in data and 'lia_types' not in data:data.setlist('lia_types',['messages','equipe'])
    data.setdefault('lia_sous','true')
    for nom in ('lia_sous','lia_annules'):
        if data.get(nom) in ('0','false','False',''):data[nom]='false'
    return Filtres(data)


def identite(objet):return objet._meta.label_lower,str(objet.pk)


def ancetres(objet):
    """Parents structurels uniquement ; aucune donnée personnelle n'est déduite."""
    yield objet
    if isinstance(objet,m.Sejour):yield from ancetres(objet.accord)
    elif isinstance(objet,(m.AccordHebergement,m.AccordRepas,m.AccordAide)):yield from ancetres(objet.accompagnement)
    elif isinstance(objet,m.Accompagnement):yield objet.menage


def origine(objet):return PorteeObjet.objects.filter(modele=objet._meta.label_lower,identifiant=str(objet.pk)).first()


def services(compte):return p.habilitations(compte).filter(tache__in=['social','accueil','gestion']).values('service_id')


class Point:
    def __init__(self,compte,nature='service',pk=None):
        with perimetre(compte,statistiques='accessibles',reperage=False):
            self._initialiser(compte,nature,pk)
    def _initialiser(self,compte,nature,pk):
        self.compte=compte;self.nature=nature;self.objet=None;self.service=None
        self.service_id=None;self.ds=None;self.origine=None
        if nature in ('service','ensemble'):
            if not any(compte.has_perm('personnes.view_'+n) for n in ('transmission','notepartagee','actionrelais')):raise PermissionDenied
            if p.active():
                if not services(compte).exists():raise PermissionDenied
                if nature=='service':
                    sid=pk or (courant().service_id if courant() else None)
                    if sid is None:sid=services(compte).order_by('service_id').values_list('service_id',flat=True).first()
                    self.service=Service.objects.select_related('etablissement__fiche').get(pk=sid,pk__in=services(compte));self.service_id=self.service.pk
            self.label='Service '+str(self.service)+' — '+str(self.service.etablissement) if self.service else 'Tous les éléments accessibles'
            return
        if nature not in MODELES:raise ValidationError('Portée inconnue.')
        model=MODELES[nature]
        if not compte.has_perm('personnes.view_'+model._meta.model_name):raise PermissionDenied
        self.objet=model.objects.get(pk=pk);self.label=self.nom(self.objet);self.origine=origine(self.objet)
        if nature in ('personne','menage') and p.active():
            ds=DossierService.objects.filter(service_id__in=services(compte),**{nature:self.objet}).select_related('service')
            selection=ds.filter(service_id=courant().service_id).first() if courant() else None
            self.ds=selection or ds.order_by('service_id').first()
            if self.ds:self.service=self.ds.service;self.service_id=self.ds.service_id
        elif self.origine:
            self.ds=self.origine.dossier;self.service_id=self.origine.service_id;self.service=self.origine.service
    @staticmethod
    def nom(objet):
        if isinstance(objet,m.Accompagnement):return 'Prise en charge du '+objet.debut.strftime('%d/%m/%Y')
        if isinstance(objet,m.AccordHebergement):return 'Hébergement du '+objet.debut.strftime('%d/%m/%Y')
        if isinstance(objet,m.AccordRepas):return 'Repas du '+objet.debut.strftime('%d/%m/%Y')
        if isinstance(objet,m.AccordAide):return objet.get_nature_display()+' — '+objet.libelle
        if isinstance(objet,m.Sejour):return 'Séjour du '+objet.debut.strftime('%d/%m/%Y')
        return 'Dossier — '+str(objet)
    def params(self):
        return {'lia_cible':self.nature,**({'lia_id':str(self.objet.pk if self.objet else self.service_id)} if self.objet or self.service_id else {})}
    def url(self,params=None):return reverse('suivi:cahier')+'?'+urlencode({**self.params(),**(params or {})},doseq=True)
    def correspond(self,cible,source,sous=True):
        if self.nature in ('service','ensemble'):return self.service_id is None or source is not None and source.service_id==self.service_id
        if cible is None:return False
        if identite(cible)==identite(self.objet):return True
        if not sous:return False
        chemin=list(ancetres(cible))
        if any(identite(x)==identite(self.objet) for x in chemin):return True
        if self.nature=='personne':
            # Une prestation collective n'est retenue que pour un bénéficiaire explicite.
            x=next((x for x in chemin if hasattr(x,'beneficiaires')),None)
            return x is not None and x.beneficiaires.filter(pk=self.objet.pk).exists()
        return False
    def ecriture(self):
        modele=m.Transmission if self.nature=='service' else m.NotePartagee
        if self.nature=='ensemble' or not self.compte.has_perm('personnes.add_'+modele._meta.model_name):return False
        if not p.active():return True
        if self.nature=='service':return self.service_id is not None
        src=self.origine
        if self.nature in ('personne','menage') and self.ds:src=PorteeObjet(service_id=self.service_id,dossier=self.ds)
        return src is not None and p.peut_renseigner(self.compte,src,modele)
    def publier(self,contenu,date_fait,cle_envoi=None):
        with perimetre(self.compte,service=self.service_id,statistiques='accessibles',reperage=False):
            if not self.ecriture():raise PermissionDenied
            if self.nature=='service':return transmissions.transmettre(self.compte,contenu,date_fait,cle_envoi=cle_envoi)
            return transmissions.noter(self.compte,contenu,date_fait=date_fait,cle_envoi=cle_envoi,**{NOTES[self.nature]:self.objet})
    def dossier_parent(self,params):
        a=next((x for x in ancetres(self.objet) if isinstance(x,m.Accompagnement)),None) if self.objet else None
        if not a:return None
        choix=params.get('lia_racine','').split(':',1)
        if len(choix)==2 and choix[0]=='personne':
            try:
                point=Point(self.compte,'personne',choix[1])
                if a.beneficiaires.filter(pk=point.objet.pk).exists():return point
            except (ObjectDoesNotExist,ValidationError,PermissionDenied,ValueError):pass
        return Point(self.compte,'menage',a.menage_id)
    def page(self,params=None):
        params={**(params or {}),'lia_ouvrir':'1'}
        if self.nature in ('personne','menage'):url=reverse('dossiers:detail',args=[self.nature,self.objet.pk])
        elif self.nature=='prise':
            parent=self.dossier_parent(params)
            url=reverse('dossiers:prise',args=[parent.nature,parent.objet.pk,self.objet.pk])
        elif self.nature in ('hebergement','repas','aide'):url=reverse({'hebergement':'suivi:accord_hebergement','repas':'suivi:accord_repas','aide':'dossiers:aide'}[self.nature],args=[self.objet.pk])
        else:return self.url(params)+'#liaisons'
        return url+'?'+urlencode(params,doseq=True)+'#liaisons'
    def parents(self,params):
        xs=[];params=params.copy();params.pop('lia_sous',None)
        if self.objet:
            chemin=list(ancetres(self.objet))[1:]
            # La navigation remonte aux prises puis au dossier ; pas de note supérieure implicite.
            for obj in chemin:
                if type(obj) not in NATURES:continue
                try:point=self.dossier_parent(params) if isinstance(obj,m.Menage) else Point(self.compte,NATURES[type(obj)],obj.pk)
                except (PermissionDenied,ValidationError,ObjectDoesNotExist,Service.DoesNotExist,*[x.DoesNotExist for x in MODELES.values()]):continue
                xs.append({'label':'Cahier de '+point.label,'url':point.page(params)})
        if self.service and self.objet:xs.append({'label':'Cahier du service '+str(self.service),'url':Point(self.compte,'service',self.service.pk).page(params)})
        return xs


def lire_responsabilite(compte,r):
    if not p.active() or not p.habilitations(compte).filter(service_id=r.dossier.service_id,tache__in=['social','accueil','gestion']).exists():return False
    cible=r.cible
    if isinstance(cible,DossierService):
        racine=cible.personne or cible.menage
        suivi=p.missions(compte).filter(dossier=cible,prise__isnull=True,hebergement__isnull=True,repas__isnull=True,aide__isnull=True).exists()
        if not suivi and not p.pleines(compte).filter(service_id=cible.service_id).exists():return False
        cible=racine
    if not compte.has_perm('personnes.view_'+cible._meta.model_name):return False
    try:p.exiger_objet(compte,cible)
    except PermissionDenied:return False
    return True


def retour_signe(compte,url):return signing.dumps({'compte':str(compte.pk),'url':url},salt='retour-liaisons-v1',compress=True)


def lire_retour(compte,token):
    try:
        d=signing.loads(token,salt='retour-liaisons-v1',max_age=86400);url=d['url']
        if d.get('compte')==str(compte.pk) and url.startswith('/') and not url.startswith('//') and url_has_allowed_host_and_scheme(url,allowed_hosts=set()):return url
    except (signing.BadSignature,KeyError,TypeError,AttributeError):pass
    return ''


def selection(point,data):
    with perimetre(point.compte,service=point.service_id,statistiques='accessibles',reperage=False):
        Point(point.compte,point.nature,point.objet.pk if point.objet else point.service_id)
        return _selection(point,data)


def _selection(point,data):
    """Chaque ligne est autorisée avant recherche, tri et pagination."""
    debut,fin=data['lia_debut'],data['lia_fin'];sous=data['lia_sous'];xs=[]
    def borner(qs,champ):
        if debut:qs=qs.filter(**{champ+'__gte':debut})
        if fin:qs=qs.filter(**{champ+'__lt':fin})
        return qs
    def ajouter(cle,nature,titre,cible,source,date,saisi,auteur,message='',contribution=None,action_url=''):
        if (debut and date<debut) or (fin and date>=fin) or not point.correspond(cible,source,sous):return
        label=Point.nom(cible) if cible is not None else ('Service '+str(point.service) if point.service else 'Transmission générale')
        texte=contribution.contenu if contribution else message
        if any(mot.casefold() not in (' '.join((titre,label,str(auteur),texte))).casefold() for mot in data['lia_q'].split()):return
        xs.append({'cle':cle,'nature':nature,'categorie':dict(TYPES)[nature],'titre':titre,'cible':label,'date':date,'saisi_le':saisi,'auteur':auteur,'message':message,'contribution':contribution,'action_url':action_url})
    if 'messages' in data['lia_types']:
        for model in (m.Transmission,m.NotePartagee):
            if not point.compte.has_perm('personnes.view_'+model._meta.model_name):continue
            qs=model.objects.select_related('auteur','annulation').prefetch_related('revisions__auteur')
            dates=Q(date_fait__isnull=False);saisies=Q(date_fait__isnull=True)
            if debut:dates &= Q(date_fait__gte=debut);saisies &= Q(cree_le__date__gte=debut)
            if fin:dates &= Q(date_fait__lt=fin);saisies &= Q(cree_le__date__lt=fin)
            qs=qs.filter(dates|saisies)
            if not data['lia_annules']:qs=qs.filter(annulation__isnull=True)
            for x in qs:
                try:releve.lecture(point.compte,x)
                except PermissionDenied:continue
                cible=transmissions.cible_note(x) if isinstance(x,m.NotePartagee) else None
                if cible is not None:
                    try:p.exiger_objet(point.compte,cible)
                    except PermissionDenied:continue
                ajouter('message-'+model._meta.model_name+'-'+str(x.pk),'messages','Message',cible,origine(x),releve.date_de(x),x.cree_le,x.auteur,contribution=x)
    if 'equipe' in data['lia_types'] and p.active():
        relais={}
        for j in borner(JournalAcces.objects.filter(service_id__in=services(point.compte),action='relais'),'cree_le__date'):
            for pk in j.apres.get('responsabilites',[]):relais[pk]=True
        rs=borner(Responsabilite.objects.filter(dossier__service_id__in=services(point.compte)),'cree_le__date').select_related('dossier__personne','dossier__menage','professionnel','cree_par','prise','hebergement','repas','aide')
        for r in rs:
            if not lire_responsabilite(point.compte,r):continue
            cible=r.cible
            if isinstance(cible,DossierService):cible=cible.personne or cible.menage
            source=PorteeObjet(service_id=r.dossier.service_id,dossier=r.dossier)
            texte=r.message
            detail='Intervention à partir du '+timezone.localtime(r.debut).strftime('%d/%m/%Y')
            if r.fin:detail+=' ; fin prévue le '+timezone.localtime(r.fin).strftime('%d/%m/%Y')+' (exclue)'
            ajouter('attribution-'+str(r.pk),'equipe',('Relais vers ' if r.pk in relais else 'Attribution à ')+str(r.professionnel),cible,source,timezone.localdate(r.cree_le),r.cree_le,r.auteur_affiche,texte)
            if xs and xs[-1]['cle']=='attribution-'+str(r.pk):xs[-1]['detail']=detail
        for j in borner(JournalAcces.objects.filter(service_id__in=services(point.compte),action='fin_responsabilite'),'cree_le__date').select_related('auteur'):
            r=Responsabilite.objects.filter(pk=j.avant.get('id'),dossier_id=j.dossier_id).select_related('dossier').first()
            if not r or not lire_responsabilite(point.compte,r):continue
            cible=r.cible
            if isinstance(cible,DossierService):cible=cible.personne or cible.menage
            ajouter('fin-'+str(j.pk),'equipe','Fin d’intervention enregistrée pour '+str(r.professionnel),cible,PorteeObjet(service_id=j.service_id),timezone.localdate(j.cree_le),j.cree_le,j.auteur,'Fin fixée au '+str(j.apres.get('fin','')))
    if 'prestations' in data['lia_types']:
        for model in (m.OperationHebergement,m.OperationRepas,m.RevisionAide):
            if not point.compte.has_perm('personnes.view_'+model._meta.model_name):continue
            qs=model.objects.select_related('auteur','accord')
            qs=borner(qs,'enregistre_le__date') if model==m.RevisionAide else borner(qs,'date_effet')
            for x in qs:
                cible=getattr(x,'sejour',None) or x.accord
                try:p.exiger_objet(point.compte,cible)
                except PermissionDenied:continue
                titre=x.get_action_display() if model!=m.OperationHebergement else {'accorde':'Hébergement accordé','admis':'Arrivée enregistrée','sorti':'Sortie enregistrée','affecte':'Lieu affecté','absence':'Absence enregistrée'}.get(x.action,{'Hébergement accordé':'Hébergement accordé','Admission effective':'Arrivée enregistrée','Sortie effective':'Sortie enregistrée','Absence enregistrée':'Absence enregistrée','Affectation enregistrée':'Affectation enregistrée','Absence close':'Fin d’absence enregistrée','Affectation close':'Fin d’affectation enregistrée','Absence close à la sortie':'Fin d’absence à la sortie','Affectation close à la sortie':'Fin d’affectation à la sortie'}.get(x.action,'Événement d’hébergement'))
                ajouter('prestation-'+model._meta.model_name+'-'+str(x.pk),'prestations',titre,cible,origine(x),getattr(x,'date_effet',timezone.localdate(x.enregistre_le)),x.enregistre_le,x.auteur)
    if 'actions' in data['lia_types'] and point.compte.has_perm('personnes.view_actionrelais'):
        for x in m.ActionRelais.objects.filter(annule_le__isnull=True,terminee_le__isnull=True).select_related('auteur','note','transmission','appel'):
            try:
                if x.note_id:releve.lecture(point.compte,x.note)
                if x.transmission_id:releve.lecture(point.compte,x.transmission)
                if x.appel_id:
                    from .appels115 import lire
                    lire(point.compte,x.appel)
            except PermissionDenied:continue
            source=origine(x)
            cible=transmissions.cible_note(x.note) if x.note_id else None
            if cible is None and source and source.dossier_id:cible=source.prise or source.dossier.personne or source.dossier.menage
            date=x.echeance or timezone.localdate(x.cree_le)
            ajouter('action-'+str(x.pk),'actions','À faire : '+x.libelle,cible,origine(x),date,x.cree_le,x.auteur,action_url=reverse('suivi:actions_relais'))
    return sorted(xs,key=lambda x:(x['date'],x['saisi_le'],x['cle']),reverse=True)


def parametres(donnees):
    d={k:donnees.get(k,'')[:200] for k in CLES if k in donnees}
    if 'lia_types' in donnees:d['lia_types']=donnees.getlist('lia_types')
    if 'lia_filtres' in donnees:d['lia_filtres']='1'
    if donnees.get('lia_enplace')=='1':d['lia_enplace']='1'
    if donnees.get('lia_focus'):d['lia_focus']=donnees['lia_focus'][:100]
    if donnees.get('lia_racine'):d['lia_racine']=donnees['lia_racine'][:100]
    if donnees.get('retour')=='jour':
        from .retour_service import date_service
        d.update(retour='jour',date_service=date_service(donnees.get('date_service')))
    if donnees.get('lia_origine'):d['lia_origine']=donnees['lia_origine'][:35000]
    return d


def ouvrir_url(url):
    from urllib.parse import urlsplit,urlunsplit,parse_qsl
    u=urlsplit(url);q=dict(parse_qsl(u.query));q['lia_ouvrir']='1'
    return urlunsplit(('', '',u.path,urlencode(q),'liaisons'))


def widget(request,objet,racine=None):
    try:
        with perimetre(request.user,statistiques='accessibles',reperage=False):point=Point(request.user,NATURES[type(objet)],objet.pk)
    except (KeyError,PermissionDenied,ValidationError,ObjectDoesNotExist,m.Personne.DoesNotExist,m.Menage.DoesNotExist):return None
    params=parametres(request.GET);params['lia_enplace']='1'
    if isinstance(racine,(m.Personne,m.Menage)):params['lia_racine']=racine._meta.model_name+':'+str(racine.pk)
    if not lire_retour(request.user,params.get('lia_origine','')):params['lia_origine']=retour_signe(request.user,ouvrir_url(request.get_full_path()))
    return {'url':point.url(params),'ouvrir':request.GET.get('lia_ouvrir')=='1','label':point.label}


def url_attribution(compte,r):
    cible=r.cible
    if isinstance(cible,DossierService):cible=cible.personne or cible.menage
    point=Point(compte,NATURES[type(cible)],cible.pk)
    jour=timezone.localdate(r.cree_le)
    return point.page({'lia_debut':jour.isoformat(),'lia_fin':(jour+timedelta(days=1)).isoformat(),
        'lia_types':['equipe'],'lia_focus':'attribution-'+str(r.pk),
        'lia_racine':('personne:'+str(r.dossier.personne_id)) if r.dossier.personne_id else 'menage:'+str(r.dossier.menage_id)})


def jeton_envoi(point):
    from uuid import uuid4
    return signing.dumps({'compte':str(point.compte.pk),'point':point.params(),'cle':str(uuid4())},salt='envoi-liaison-v1')


def verifier_envoi(point,jeton):
    from uuid import UUID
    try:
        d=signing.loads(jeton,salt='envoi-liaison-v1',max_age=86400)
        if d['compte']!=str(point.compte.pk) or d['point']!=point.params():raise ValueError
        return UUID(d['cle'])
    except (signing.BadSignature,KeyError,TypeError,ValueError):raise ValidationError('Envoi expiré ou d’un autre cahier ; rechargez avant de publier.')
