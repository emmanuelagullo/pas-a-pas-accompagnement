"""Un accès de parcours depuis la BD, sélection locale et actions au niveau de l'élément."""
import csv
import json
from urllib.parse import urlencode
from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, OuterRef, Subquery, Model, Count
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe
from . import models as m, parcours as s, bd6, textes_riches as tr
from .forms_parcours import FORMULAIRES, LiaisonForm
from .champs_saisie import FormulaireMetier
from .forms_hebergement import date_champ
from .vues_bd6 import objet_dossier, traiter
from .presentation_dossier_complet import lignes, valeur
from .exports import cellule_csv


def code_valide(code):
    if code not in s.RUBRIQUES:raise Http404
    return s.RUBRIQUES[code]


def navigation(request,objet,code):
    p={k:request.GET[k][:160] for k in ('q','mode','page','origine_menage','sejour','repas','date','contexte_prise','retour_nature','retour_pk') if k in request.GET}
    if request.GET.get('retour_exploration'):p['retour_exploration']=request.GET['retour_exploration'][:20000]
    p.setdefault('retour_nature',objet._meta.model_name);p.setdefault('retour_pk',str(objet.pk))
    origine=objet
    if p['retour_nature'] in ('personne','menage'):
        try:identifiant=forms.UUIDField().clean(p['retour_pk'])
        except forms.ValidationError:raise Http404
        origine=objet_dossier(request,p['retour_nature'],identifiant)
    else:raise Http404
    nature=origine._meta.model_name
    p['rubrique']=code
    retour=reverse('dossiers:detail',args=[nature,origine.pk])+'?'+urlencode(p)
    context=None
    if p.get('contexte_prise'):
        try:context=origine.accompagnements.filter(pk=forms.UUIDField().clean(p['contexte_prise'])).first()
        except forms.ValidationError:pass
        if context:retour=reverse('dossiers:prise',args=[nature,origine.pk,context.pk])+'?'+urlencode(p)
        else:p.pop('contexte_prise',None)
    return p, retour, reverse('dossiers:parcours',args=[nature,origine.pk])+'?'+urlencode(p), context


def version_lignes(code,x):return lignes(s.RUBRIQUES[code].version,x,[c for c in s.RUBRIQUES[code].champs if c!='texte'])


def presenter(code,e,jour):
    vs=list(e.versions.select_related('auteur').all())
    v=next((v for v in vs if v.debut<=jour and (v.fin is None or v.fin>jour)),None)
    return {'element':e,'version':v,'lignes':version_lignes(code,v) if v else [],
        'titre':getattr(v,'titre',None) or getattr(v,'destination',None) or getattr(v,'motif_demande',None) or 'Suivi du dossier',
        'versions':[{'fait':x,'lignes':version_lignes(code,x)} for x in vs],
        'url':reverse('dossiers:parcours_element',args=[code,e.pk])}


def presentation_formulaire(code,form):
    principaux={
        'demandes':('beneficiaires','debut','etat','groupe_demande','motif_demande','demandeur','motif_decision','source'),
        'orientations':('beneficiaires','debut','etat','destination','motif_orientation','resultat','source'),
        'objectifs':('beneficiaires','debut','etat','theme','titre','horizon','echeance','texte','source'),
        'suivi':('beneficiaires','debut','etat','raison','source'),
    }[code]
    visibles=[b for b in form if not b.is_hidden]
    courants=[b for b in visibles if b.name in principaux or b.name=='motif']
    precisions=[b for b in visibles if b not in courants]
    return {'gabarit':'dossiers/form_parcours.html','champs_principaux':courants,'champs_precisions':precisions,
        'precisions_ouvertes':any(b.errors or b.value() for b in precisions)}


class ConsultationForm(FormulaireMetier):
    date=date_champ('Situation au')


@never_cache
@require_safe
@login_required
@permission_required('personnes.view_personne',raise_exception=True)
def hub(request,nature,pk):
    objet=objet_dossier(request,nature,pk)
    autorises=[c for c in s.RUBRIQUES if request.user.has_perms(s.droits(c))]
    if not autorises:raise PermissionDenied
    code=request.GET.get('rubrique',autorises[0]);code_valide(code)
    s.exiger(request.user,code)
    params,retour,base,context=navigation(request,objet,code)
    f=ConsultationForm(request.GET if 'date' in request.GET else None,initial={'date':timezone.localdate()})
    jour=f.cleaned_data['date'] if f.is_bound and f.is_valid() else timezone.localdate()
    liens=[]
    for c in autorises:
        p={**params,'rubrique':c};liens.append((c,s.RUBRIQUES[c].titre,'?'+urlencode(p)))
    qs=s.elements(code,objet)
    # Une démarche personnelle survit aux changements de ménage. Sa cible reste affichée.
    if nature=='personne':
        qs=s.RUBRIQUES[code].racine.objects.filter(Q(personne=objet)|Q(beneficiaires=objet)).distinct().select_related('personne','menage').prefetch_related('beneficiaires')
    if not request.user.has_perm('personnes.view_menage'):qs=qs.filter(menage__isnull=True)
    objets=[] if f.errors else [presenter(code,e,jour) for e in qs.filter(annule_le__isnull=True).prefetch_related('versions')]
    return render(request,'dossiers/parcours.html',{'objet':objet,'nature':nature,'code':code,'rubrique':s.RUBRIQUES[code],
        'liens':liens,'consultation':f,'parametres':{k:v for k,v in params.items() if k not in ('date','page')},'query':urlencode(params),
        'retour':retour,'elements':objets,'peut_ajouter':request.user.has_perm('personnes.add_'+s.RUBRIQUES[code].racine._meta.model_name),
        'annules':qs.filter(annule_le__isnull=False),'date_situation':jour})


def form_initial(code,x):
    d={c:getattr(x,c) for c in s.RUBRIQUES[code].champs} if x else {}
    if code=='objectifs' and x:d['texte']=tr.lire_objet(x,'texte')
    return d


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def nouveau(request,nature,pk,code):
    r=code_valide(code);s.exiger(request.user,code,'add')
    objet=objet_dossier(request,nature,pk);params,retour,base,context=navigation(request,objet,code)
    personnes=m.Personne.objects.filter(pk=objet.pk) if nature=='personne' else m.Personne.objects.filter(appartenances__menage=objet).distinct()
    selection=list(personnes.values_list('pk',flat=True)) if nature=='personne' else list(objet.appartenances.filter(debut__lte=timezone.localdate()).filter(Q(fin__isnull=True)|Q(fin__gt=timezone.localdate())).values_list('personne_id',flat=True))
    try:jour=forms.DateField().clean(request.GET.get('date') or timezone.localdate())
    except forms.ValidationError:raise Http404
    if nature=='menage':selection=list(objet.appartenances.filter(debut__lte=jour).filter(Q(fin__isnull=True)|Q(fin__gt=jour)).values_list('personne_id',flat=True))
    f=FORMULAIRES[code](request.POST if request.method=='POST' else None,initial={'debut':jour,'attendu':bd6.jeton(objet),'beneficiaires':selection,'accompagnement':context.pk if context else None})
    f.fields['beneficiaires']=forms.ModelMultipleChoiceField(personnes,label='Personnes explicitement concernées',widget=forms.CheckboxSelectMultiple)
    if code in ('objectifs','orientations'):
        if request.user.has_perms(['personnes.view_accompagnement','personnes.view_menage']):
            f.fields['accompagnement']=forms.ModelChoiceField(objet.accompagnements.all(),label='Prise en charge de contexte (facultative)',required=False,
                help_text='Repère d’origine : l’objectif ou l’orientation reste dans le dossier après sa clôture.')
            f.fields['accompagnement'].label_from_instance=lambda a:str(a.menage)+' · '+str(a.debut)+' · '+str(a.pk)
    if code=='orientations' and request.user.has_perms(s.droits('demandes')):
        f.fields['demande']=forms.ModelChoiceField(s.elements('demandes',objet).filter(annule_le__isnull=True),label='Demande d’origine (facultative)',required=False)
        f.fields['demande'].label_from_instance=lambda e:str(e.cible)+' · '+str(e.cree_le.date())+' · '+str(e.pk)
    f.order_fields(['beneficiaires',*f.fields])
    return traiter(request,f,'Ajouter — '+r.titre,lambda **d:s.creer(request.user,code,objet,**d),base,objet,
        explication='Confirmez les personnes concernées. Une demande, un objectif ou une orientation ne crée aucune prestation. Le contexte et les personnes resteront identifiés ; une erreur de cible s’annule.',**presentation_formulaire(code,f))


@never_cache
@require_safe
@login_required
def element(request,code,pk):
    r=code_valide(code);s.exiger(request.user,code)
    e=get_object_or_404(r.racine,pk=pk);objet=e.cible
    if e.menage_id and not request.user.has_perm('personnes.view_menage'):raise PermissionDenied
    params,retour,base,context=navigation(request,objet,code)
    jour=timezone.localdate()
    if 'date' in request.GET:
        try:jour=forms.DateField().clean(request.GET['date'])
        except forms.ValidationError:raise Http404
    x=presenter(code,e,jour)
    journaux=[]
    for j in e.revisions.select_related('auteur'):
        def photos(xs):
            out=[]
            for v in xs:
                if 'accompagnement' in v:
                    out.append({'debut':'','fin':None,'source':'','lignes':[('Prise en charge',valeur(None,v['accompagnement']))]});continue
                out.append({'debut':v['debut'],'fin':v['fin'],'source':v['source'],
                    'annulation':v.get('annulation',''),'lignes':[('Cible',valeur(None,v.get('cible'))),('Bénéficiaires', ' ; '.join(valeur(None,p) for p in v.get('beneficiaires',[])))]+[(r.version._meta.get_field(c).verbose_name,valeur(r.version._meta.get_field(c),v.get(c))) for c in r.champs]})
            return out
        journaux.append({'revision':j,'avant':photos(j.avant),'apres':photos(j.apres)})
    contacts=[]
    if x['version'] and code in ('demandes','orientations'):
        from . import partenaires,intervenants
        v=x['version']
        for champ,label in ([('organisme','Organisme destinataire'),('interlocuteur','Interlocuteur')] if code=='orientations' else [('demandeur_professionnel','Professionnel demandeur'),('demandeur_organisme','Organisme demandeur'),('prescripteur','Prescripteur'),('organisme_orienteur','Organisme orienteur')]):
            ref=getattr(v,champ)
            if ref:
                fiche=(intervenants.a_date([ref.pk],jour) if isinstance(ref,m.Intervenant) else partenaires.a_date([ref.pk],jour)).first()
                if fiche:contacts.append((label,fiche))
    from .exploration_releve import retour_verifie
    retour_rapport=retour_verifie(request.user,params.get('retour_exploration'))
    return render(request,'dossiers/parcours_document.html' if request.GET.get('edition')=='impression' else 'dossiers/parcours_element.html',{'retour_rapport':retour_rapport,'objet':objet,'code':code,'rubrique':r,'x':x,'query':urlencode(params),'retour':base,
        'lecture_prises':request.user.has_perms(['personnes.view_accompagnement','personnes.view_menage']),
        'lecture_demande':request.user.has_perms(s.droits('demandes')),'journaux':journaux,'peut_modifier':request.user.has_perm('personnes.change_'+r.racine._meta.model_name),
        'peut_annuler':request.user.has_perm('personnes.annuler_'+r.racine._meta.model_name),
        'peut_admettre':code=='demandes' and request.user.has_perms(['personnes.add_accompagnement','personnes.view_accompagnement','personnes.view_menage','personnes.change_demandeaccueil']),
        'contacts':contacts,'url_fiche':reverse('dossiers:parcours_element',args=[code,e.pk])+'?'+urlencode(params),'date_situation':jour,'nouvelle_prise_url':reverse('dossiers:nouvelle_prise',args=[objet._meta.model_name,objet.pk])+'?'+urlencode({**params,'demande':str(e.pk)})})


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def modifier(request,code,pk,action,version_pk=None):
    r=code_valide(code);s.exiger(request.user,code,'annuler' if action=='annuler' else 'change')
    e=get_object_or_404(r.racine,pk=pk);objet=e.cible
    if e.menage_id and not request.user.has_perm('personnes.view_menage'):raise PermissionDenied
    params,retour,base,context=navigation(request,objet,code)
    url=reverse('dossiers:parcours_element',args=[code,e.pk])+'?'+urlencode(params)
    if action=='annuler':
        f=FormulaireMetier(request.POST if request.method=='POST' else None)
        f.fields['attendu']=forms.CharField(widget=forms.HiddenInput,initial=bd6.jeton(e))
        f.fields['motif']=forms.CharField(label='Pourquoi cette saisie était-elle une erreur ?',max_length=240)
        return traiter(request,f,'Annuler une saisie erronée',lambda **d:s.annuler(request.user,code,e,**d),url,objet,
            explication='Cette démarche restera dans l’historique. Pour une évolution réelle, renseignez son nouvel état.')
    if action not in ('changer','corriger'):raise Http404
    try:jour=forms.DateField().clean(request.GET.get('date') or timezone.localdate())
    except forms.ValidationError:raise Http404
    v=get_object_or_404(e.versions,pk=version_pk) if action=='corriger' else e.versions.filter(debut__lte=jour).filter(Q(fin__isnull=True)|Q(fin__gt=jour)).first()
    if v is None:raise Http404
    initial=form_initial(code,v)
    initial.update(debut=v.debut if action=='corriger' else jour,source=v.source if action=='corriger' else '',attendu=bd6.jeton(e))
    f=FORMULAIRES[code](request.POST if request.method=='POST' else None,initial=initial)
    f.fields['motif'].required=False
    return traiter(request,f,('Corriger une erreur' if action=='corriger' else 'Renseigner un changement')+' — '+r.titre,
        lambda **d:s.enregistrer(request.user,code,e,correction=v.pk if action=='corriger' else None,**d),url,objet,
        explication='Le changement conserve les états précédents à leurs dates ; la correction rectifie une information erronée. Une échéance annoncée ne change pas automatiquement l’état.',**presentation_formulaire(code,f))


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def liaison(request,pk):
    s.exiger(request.user,'demandes','change')
    from .suivi import exiger
    exiger(request.user,'view_menage','view_accompagnement')
    e=get_object_or_404(m.DemandeAccueil,pk=pk);objet=e.cible
    params,retour,base,context=navigation(request,objet,'demandes')
    f=LiaisonForm(request.POST if request.method=='POST' else None,initial={'attendu':bd6.jeton(e),'accompagnement':e.accompagnement_id})
    f.fields['accompagnement'].queryset=objet.accompagnements.all()
    f.fields['accompagnement'].label_from_instance=lambda a:str(a.menage)+' · '+str(a.debut)+' · '+str(a.pk)
    if e.accompagnement_id:
        f.fields['accompagnement'].disabled=True
        f.fields['retirer']=forms.BooleanField(label='Je confirme que cette liaison était une erreur ; la prise en charge est conservée')
    def action(**d):
        return s.lier(request.user,e,prise=d.pop('accompagnement'),**d)
    return traiter(request,f,'Corriger la liaison' if e.accompagnement_id else 'Associer une prise en charge existante',action,
        reverse('dossiers:parcours_element',args=['demandes',e.pk])+'?'+urlencode(params),objet,
        explication='La demande doit être acceptée à l’admission. Les bénéficiaires doivent correspondre exactement ; aucune prestation ni modification de la prise en charge.')


class RapportParcoursForm(FormulaireMetier):
    rubrique=forms.ChoiceField(label='Rubrique')
    date=date_champ('Situation au')
    q=forms.CharField(label='Personne ou ménage contenant',max_length=160,required=False)
    etat=forms.ChoiceField(label='État',required=False)
    texte=forms.CharField(label='Motif, thème, destination ou provenance contenant',max_length=160,required=False)
    depuis=date_champ('Première déclaration depuis le',False)
    jusqua=date_champ('Première déclaration jusqu’au',False)
    sortie_depuis=date_champ('Fin réelle de prise en charge depuis le',False)
    sortie_jusqua=date_champ('Fin réelle de prise en charge jusqu’au',False)
    activite=forms.ChoiceField(label='Activité',required=False,choices=[('','Toutes'),*m.VersionDemande._meta.get_field('activite').choices])
    demandeur=forms.ChoiceField(label='Demande exprimée par',required=False,choices=[('','Tous'),*m.VersionDemande._meta.get_field('demandeur').choices])
    admission=forms.ChoiceField(label='Admission',required=False,choices=[('','Toutes'),('oui','Prise en charge débutée'),('non','Sans prise en charge débutée')])
    horizon=forms.ChoiceField(label='Horizon',required=False,choices=[('','Tous'),*m.VersionObjectif._meta.get_field('horizon').choices])
    echeance_avant=date_champ('Échéance annoncée au plus tard le',False)
    organisme=forms.ModelChoiceField(m.Partenaire.objects.all(),label='Organisme',required=False)
    professionnel=forms.ModelChoiceField(m.Intervenant.objects.all(),label='Professionnel demandeur / prescripteur / interlocuteur',required=False)
    groupe_demande=forms.CharField(label='Groupe demandeur déclaré exact',max_length=160,required=False)
    dernier_hebergement_duree=forms.CharField(label='Durée déclarée du dernier hébergement exacte',max_length=160,required=False)
    motif_demande=forms.CharField(label='Motif de demande exact',max_length=160,required=False)
    motif_decision=forms.CharField(label='Motif de décision exact',max_length=160,required=False)
    provenance=forms.CharField(label='Provenance exacte',max_length=160,required=False)
    dernier_hebergement_type=forms.CharField(label='Type du dernier hébergement exact',max_length=160,required=False)
    type_destination=forms.CharField(label='Type de destination exact',max_length=160,required=False)
    theme=forms.CharField(label='Thème exact',max_length=160,required=False)
    motif_entree=forms.CharField(label='Motif d’entrée exact',max_length=160,required=False)
    motif_sortie=forms.CharField(label='Motif de sortie exact',max_length=160,required=False)
    orientation_sortie=forms.CharField(label='Orientation de sortie exacte',max_length=160,required=False)
    destination_sortie=forms.CharField(label='Destination de sortie exacte',max_length=160,required=False)
    def clean(self):
        d=super().clean()
        if d.get('depuis') and d.get('jusqua') and d['depuis']>d['jusqua']:raise forms.ValidationError('La période est inversée.')
        if d.get('sortie_depuis') and d.get('sortie_jusqua') and d['sortie_depuis']>d['sortie_jusqua']:raise forms.ValidationError('La période de sortie est inversée.')
        return d


@never_cache
@require_safe
@login_required
@permission_required('personnes.view_personne',raise_exception=True)
def rapport(request):
    choix=[(c,r.titre) for c,r in s.RUBRIQUES.items() if request.user.has_perms(s.droits(c))]
    lecture_admissions=request.user.has_perms(['personnes.view_menage','personnes.view_accompagnement'])
    lecture_prises=request.user.has_perms(['personnes.view_menage','personnes.view_accompagnement','personnes.view_informationsaccompagnement'])
    if lecture_prises:choix.append(('prises','Entrées et sorties des prises en charge'))
    if not choix:raise PermissionDenied
    params=request.GET.copy();params.setdefault('rubrique',choix[0][0]);params.setdefault('date',timezone.localdate().isoformat())
    code=params['rubrique']
    if code not in dict(choix):raise PermissionDenied
    f=RapportParcoursForm(params);f.fields['rubrique'].choices=choix
    inutiles=set()
    if code=='prises':
        f.fields['depuis'].label='Début de prise en charge depuis le';f.fields['jusqua'].label='Début de prise en charge jusqu’au'
        champs=['activite','provenance','motif_entree','orientation_sortie','motif_sortie','destination_sortie','referent','animaux']
        f.fields['etat'].choices=[('','Toutes'),('ouverte','Ouvertes'),('close','Closes')]
        inutiles|={'demandeur','admission','horizon','echeance_avant','organisme','professionnel'}
    else:
        r=s.RUBRIQUES[code];champs=list(r.champs)
        inutiles|={'sortie_depuis','sortie_jusqua'}
        f.fields['etat'].choices=[('','Tous'),*r.version._meta.get_field('etat').choices]
        if code!='demandes':inutiles|={'activite','demandeur','admission'}
        if code!='objectifs':inutiles.add('horizon')
        if code=='suivi':inutiles|={'echeance_avant','organisme','professionnel'}
        if code=='objectifs':inutiles|={'organisme','professionnel'}
    if not request.user.has_perm('personnes.view_menage') and code!='prises':
        # Les versions de ménages ne participent ni aux filtres, ni aux totaux, ni aux exports.
        individuel=True
    else:individuel=False
    if not lecture_admissions:inutiles.add('admission')
    for c in ('groupe_demande','dernier_hebergement_duree','motif_demande','motif_decision','provenance','dernier_hebergement_type','type_destination','theme','motif_entree','motif_sortie','orientation_sortie','destination_sortie'):
        if c not in champs:inutiles.add(c)
    for c in inutiles:f.fields.pop(c,None)
    objets=[];lignes_rapport=[];delais=[];repartition=[]
    if f.is_valid():
        d=f.cleaned_data;jour=d['date']
        if code=='prises':
            derniere=m.InformationsAccompagnement.objects.filter(accompagnement_id=OuterRef('accompagnement_id')).order_by('-version').values('pk')[:1]
            qs=m.InformationsAccompagnement.objects.filter(pk=Subquery(derniere),accompagnement__debut__lte=jour).select_related('accompagnement__menage')
            if d.get('etat')=='ouverte':qs=qs.filter(Q(accompagnement__fin__isnull=True)|Q(accompagnement__fin__gt=jour))
            elif d.get('etat')=='close':qs=qs.filter(accompagnement__fin__lte=jour)
            if d.get('depuis'):qs=qs.filter(accompagnement__debut__gte=d['depuis'])
            if d.get('jusqua'):qs=qs.filter(accompagnement__debut__lte=d['jusqua'])
            if d.get('sortie_depuis'):qs=qs.filter(accompagnement__fin__gte=d['sortie_depuis'])
            if d.get('sortie_jusqua'):qs=qs.filter(accompagnement__fin__lte=d['sortie_jusqua'])
        else:
            qs=s.a_date(code,jour).select_related('element__personne','element__menage').prefetch_related('element__beneficiaires')
            if individuel:qs=qs.filter(element__menage__isnull=True)
            if code=='demandes':qs=qs.select_related('element__accompagnement')
            if d.get('etat'):qs=qs.filter(etat=d['etat'])
            premiere=r.version.objects.filter(element_id=OuterRef('element_id')).order_by('debut').values('debut')[:1]
            qs=qs.annotate(premiere_date=Subquery(premiere))
            if d.get('depuis'):qs=qs.filter(premiere_date__gte=d['depuis'])
            if d.get('jusqua'):qs=qs.filter(premiere_date__lte=d['jusqua'])
        if d['q']:
            for mot in d['q'].split():
                filtre=Q(accompagnement__menage__libelle__icontains=mot)|Q(accompagnement__beneficiaires__designation__icontains=mot)|Q(accompagnement__beneficiaires__prenom__icontains=mot) if code=='prises' else Q(element__personne__designation__icontains=mot)|Q(element__personne__prenom__icontains=mot)|Q(element__menage__libelle__icontains=mot)|Q(element__beneficiaires__designation__icontains=mot)|Q(element__beneficiaires__prenom__icontains=mot)
                qs=qs.filter(filtre).distinct()
        if d['texte']:
            filtre=Q()
            modele=m.InformationsAccompagnement if code=='prises' else r.version
            for c in champs:
                if modele._meta.get_field(c).get_internal_type() in ('CharField','TextField'):filtre|=Q(**{c+'__icontains':d['texte']})
            qs=qs.filter(filtre)
        for c in ('groupe_demande','dernier_hebergement_duree','motif_demande','motif_decision','provenance','dernier_hebergement_type','type_destination','theme','motif_entree','motif_sortie','orientation_sortie','destination_sortie'):
            if d.get(c):qs=qs.filter(**{c+'__iexact':d[c]})
        for c in ('activite','demandeur','horizon'):
            if d.get(c):qs=qs.filter(**{c:d[c]})
        if d.get('echeance_avant'):
            champ={'demandes':'accueil_prevu','orientations':'date_prevue','objectifs':'echeance'}[code];qs=qs.filter(**{champ+'__lte':d['echeance_avant']})
        if d.get('organisme'):
            qs=qs.filter(Q(demandeur_organisme=d['organisme'])|Q(organisme_orienteur=d['organisme'])) if code=='demandes' else qs.filter(organisme=d['organisme'])
        if d.get('professionnel'):
            qs=qs.filter(Q(demandeur_professionnel=d['professionnel'])|Q(prescripteur=d['professionnel'])) if code=='demandes' else qs.filter(interlocuteur=d['professionnel'])
        if d.get('admission'):
            condition=Q(element__accompagnement__debut__lte=jour)
            qs=qs.filter(condition) if d['admission']=='oui' else qs.exclude(condition)
        if code!='prises':
            etiquettes=dict(r.version._meta.get_field('etat').choices)
            repartition=[(etiquettes[x['etat']],x['nombre']) for x in qs.order_by().values('etat').annotate(nombre=Count('element_id',distinct=True))]
        objets=list(qs.order_by('pk'))
        modele=m.InformationsAccompagnement if code=='prises' else r.version
        for v in objets:
            e=v.accompagnement if code=='prises' else v.element
            ps=list(e.beneficiaires.all())
            adm=e if code=='prises' else e.accompagnement if code=='demandes' and lecture_admissions else None
            depot=e.debut if code=='prises' else v.premiere_date
            delai=(adm.debut-depot).days if code=='demandes' and adm and adm.debut<=jour else None
            if delai is not None:delais.append(delai)
            lignes_rapport.append({'fait':v,'element':e,'cible':str(e.menage) if code=='prises' else str(e.cible),'beneficiaires':ps,
                'depot':depot,'admission':adm if adm and adm.debut<=jour else None,'delai':delai,'lignes':lignes(modele,v,champs),
                'url':reverse('suivi:resume',args=[e.pk]) if code=='prises' else reverse('dossiers:parcours_element',args=[code,e.pk])+'?date='+jour.isoformat()})
        if request.GET.get('format')=='csv':
            response=HttpResponse(content_type='text/csv; charset=utf-8');response['Content-Disposition']='attachment; filename="parcours.csv"'
            w=csv.writer(response,delimiter=';');w.writerow(['date_reference','rubrique','element_id','cible','beneficiaires_ids','depot_ou_debut_prise','date_effet','saisie_le','fin_exclue',*champs,'source','prise_id','admission_debut','delai_jours'])
            for x in lignes_rapport:
                v=x['fait'];a=x['admission']
                w.writerow([jour.isoformat(),code,x['element'].pk,cellule_csv(x['cible']),','.join(str(p.pk) for p in x['beneficiaires']),x['depot'].isoformat(),'' if code=='prises' else v.debut.isoformat(),v.enregistre_le.isoformat(),(x['element'].fin.isoformat() if x['element'].fin else '') if code=='prises' else v.fin.isoformat() if v.fin else '',
                    *[cellule_csv(json.dumps(s.valeur_journal(getattr(v,c)),ensure_ascii=False) if isinstance(getattr(v,c),Model) else getattr(v,c) if getattr(v,c) is not None else '') for c in champs],cellule_csv(v.motif if code=='prises' else v.source),a.pk if a else '',a.debut.isoformat() if a else '',x['delai'] if x['delai'] is not None else ''])
            return response
    params.pop('format',None);params.pop('page',None)
    return render(request,'dossiers/rapport_parcours.html',{'form':f,'code':code,'nombre':len(objets),'delais':delais,
        'repartition':repartition,'moyenne_delai':sum(delais)/len(delais) if delais else None,'page_obj':Paginator(lignes_rapport,40).get_page(request.GET.get('page')),'query_rapport':params.urlencode()})
