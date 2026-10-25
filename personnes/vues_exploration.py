import csv
from datetime import timedelta
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect,get_object_or_404
from django.utils import timezone
from django.http import HttpResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from . import models as m,exploration as e
from .forms_exploration import ExplorationForm
from .personnalisation_rapports import retour_origine
from .exports import cellule_csv


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def explorer(request):
    e.disponibles(request.user)
    from . import modeles_personnels as gestion
    statut=200;calcul_effectue=False
    modele=get_object_or_404(m.ModeleRapport,pk=request.GET['modele'],auteur=request.user) if request.GET.get('modele') else None
    data=(modele.parametres.copy() if modele else (request.POST.copy() if request.method=='POST' else request.GET.copy()))
    cible=modele
    if not cible and (request.POST.get('modele_cible') or request.GET.get('modele_cible')):
        cible=get_object_or_404(m.ModeleRapport,pk=request.POST.get('modele_cible') or request.GET.get('modele_cible'),auteur=request.user)
    attendu_modele=request.POST.get('attendu_modele') or request.GET.get('attendu_modele') or (gestion.jeton(request.user,cible) if cible and request.user.has_perms(['personnes.view_modelerapport','personnes.add_modelerapport']) else '')
    contexte_retour={k:(request.POST if request.method=='POST' else request.GET).get(k,'') for k in ('origine_rapport','panneau','page')}
    if cible:contexte_retour.update(modele_cible=str(cible.pk),attendu_modele=attendu_modele)
    if modele and not data.get('exploration'):return redirect('statistiques')
    if modele and data.get('schema')!=1:return HttpResponse('Version du modèle non prise en charge ; aucun résultat calculé.',status=409)
    jour=timezone.localdate()
    for c,v in dict(population='personnes',debut=jour.replace(day=1).isoformat(),fin=(jour+timedelta(days=1)).isoformat(),reference=jour.isoformat(),mesure='objets',axe='total',croisement='',classes='',filtre1='',operation1='egal',valeur1='',filtre2='',operation2='egal',valeur2='').items():data.setdefault(c,v)
    if data.get('periode'):
        from .vues_statistiques import bornes_periode
        try:
            debut,fin=bornes_periode(data['periode'],jour);data.update(debut=debut.isoformat(),fin=fin.isoformat(),reference=(fin-timedelta(days=1)).isoformat())
        except ValueError:pass
    if request.GET.get('ajouter_filtre'):
        try:n=int(data.get('filtres') or 2)
        except ValueError:n=2
        n=min(n+1,20);data['filtres']=str(n)
        data.setdefault('filtre'+str(n),'');data.setdefault('operation'+str(n),'egal');data.setdefault('valeur'+str(n),'')
    for action,champ,mini,maxi in [('ajouter_niveau','niveaux',2,7),('ajouter_mesure','nombre_mesures',1,9),('ajouter_colonne','nombre_colonnes',0,11)]:
        if request.GET.get(action):
            try:n=int(data.get(champ) or mini)
            except (ValueError,TypeError):n=mini
            n=min(n+1,maxi);data[champ]=str(n)
    liens_totaux=[]
    from . import composition_exploration as composition
    if request.GET.get('deplacer_niveau'):data=composition.deplacer(data,request.GET['deplacer_niveau'])
    if request.GET.get('retirer_niveau'):data=composition.retirer(data,request.GET['retirer_niveau'])
    form=ExplorationForm(data,acteur=request.user);lignes=[];totaux={};nombre=0;selection=[];qualite_mesures=[]
    if form.is_valid():
        try:
            mesures=list(dict.fromkeys([form.cleaned_data['mesure'],*[form.cleaned_data.get('mesure'+str(i)) for i in range(2,10) if form.cleaned_data.get('mesure'+str(i))]]))
            labels=dict(form.fields['mesure'].choices)
            for mesure in mesures:
                lignes_mesure,totaux_mesure,selection=e.calculer(request.user,{**form.cleaned_data,'mesure':mesure},contributions=True)
                for ligne in lignes_mesure:
                    ligne['_code_mesure']=mesure;ligne['mesure']=labels[mesure];ligne['niveaux_affiches']=[v for i,v in enumerate(ligne['niveaux'],3) if form.cleaned_data.get('axe'+str(i))]
                lignes.extend(lignes_mesure)
                if len(lignes)>2000:raise ValidationError('Plus de 2 000 cellules pour les mesures réunies : réduisez les axes ou mesures. Aucun résultat tronqué.')
                inconnus=e.mesures.inconnus(selection,mesure)
                if inconnus is not None:qualite_mesures.append((labels[mesure],inconnus))
                from . import justificatifs_exploration as preuves
                for total in preuves.totaux_cellules(totaux_mesure,selection,mesure):
                    liens_totaux.append(dict(libelle=labels[mesure]+' — '+total['unite'],valeur=total['valeur'],url=preuves.lien(request.user,{**form.cleaned_data,**contexte_retour},mesure,total,contexte_retour.get('page') or 1)))
                totaux.update({(labels[mesure]+' — '+u if len(mesures)>1 else u):v for u,v in totaux_mesure.items()})
            nombre=len(selection)
            from .exploration_releve import relever
            colonnes,details=relever({**form.cleaned_data,**contexte_retour},selection,request.user)

        except ValidationError as erreur:
            form.add_error(None,erreur);lignes=[];totaux={};selection=[];qualite_mesures=[]
        else:
            calcul_effectue=True
            if request.method=='POST':
                from .suivi import exiger
                exiger(request.user,'add_modelerapport','view_modelerapport')
                nom=request.POST.get('nom','').strip()
                if not nom or len(nom)>100:form.add_error(None,'Nommez ce modèle (100 caractères au plus).')
                else:
                    params={k:str(v) if v is not None else '' for k,v in form.cleaned_data.items()};params.update(schema=1,exploration=True)
                    try:
                        if request.POST.get('action_modele')=='remplacer':
                            if cible is None:raise ValidationError('Choisissez le modèle personnel à remplacer.')
                            x=gestion.changer(request.user,cible,attendu_modele,nom,params)
                        else:
                            if m.ModeleRapport.objects.filter(auteur=request.user).count()>=30:raise ValidationError('Limite de 30 modèles personnels atteinte.')
                            x=m.ModeleRapport.objects.create(auteur=request.user,nom=nom,parametres=params)
                    except ValidationError as erreur:
                        form.add_error(None,erreur.messages);statut=409 if isinstance(erreur,gestion.ConflitModele) else 400
                    else:
                        from django.urls import reverse
                        from urllib.parse import urlencode
                        retour={k:v for k,v in contexte_retour.items() if k in ('origine_rapport','panneau','page') and v}
                        return redirect(reverse('dossiers:explorer')+'?'+urlencode({'modele':x.pk,**retour}))
            if request.GET.get('format')=='csv_detail':
                r=HttpResponse(content_type='text/csv; charset=utf-8');r['Content-Disposition']='attachment; filename="exploration-detail-fictive.csv"';w=csv.writer(r,delimiter=';');w.writerow(['Objet','Date du fait / début',*colonnes])
                for x in details:w.writerow([cellule_csv(v) for v in [x['id'],x['date'],*x['valeurs']]])
                return r
            if request.GET.get('format')=='pdf_detail':
                from .pdf_restitution import produire
                return produire(request,'Relevé détaillé — données fictives',['Population : '+dict(e.POPULATIONS)[form.cleaned_data['population']], 'Paramètres : '+str({k:str(v) for k,v in form.cleaned_data.items()}), 'Colonnes : '+' · '.join(colonnes),*[x['id']+' · '+str(x['date'])+' · '+' · '.join(x['valeurs']) for x in details]],'exploration-detail-fictive.pdf')
            if request.GET.get('format')=='csv':
                r=HttpResponse(content_type='text/csv; charset=utf-8');r['Content-Disposition']='attachment; filename="exploration-fictive.csv"';w=csv.writer(r,delimiter=';');w.writerow(['Population','Référence','Mesure','Axe','Croisement',*['Niveau '+str(i) for i in range(3,8)],'Unité','Valeur','Déclarants sans valeur connue pour cette mesure',*(['Type de ligne','Profondeur du sous-total'] if form.cleaned_data.get('sous_totaux') else [])])
                for x in lignes:w.writerow([cellule_csv(v) for v in [dict(e.POPULATIONS)[form.cleaned_data['population']],form.cleaned_data['reference'],x['mesure'],x['axe'],x['croisement'],*x['niveaux'],x['unite'],x['valeur'],x['inconnus'],*(['Sous-total' if x.get('sous_total') else 'Détail',x.get('niveau_sous_total','')] if form.cleaned_data.get('sous_totaux') else [])]])
                return r
            if request.GET.get('format')=='pdf':
                from .pdf_restitution import produire
                return produire(request,'Exploration — données fictives',[dict(e.POPULATIONS)[form.cleaned_data['population']],'Situation personnelle à la référence : '+str(form.cleaned_data['reference']),
                    'Période : '+str(form.cleaned_data['debut'])+' → '+str(form.cleaned_data['fin'])+' (fin exclue)',
                    'Paramètres : '+str({k:str(v) for k,v in form.cleaned_data.items()}),'Totaux distincts recalculés : '+str(totaux),
                    *[('Sous-total — ' if x.get('sous_total') else '')+f'{x["mesure"]} — '+ ' · '.join([x['axe'],x['croisement'],*x['niveaux']])+f' : {x["valeur"]} {x["unite"]}' for x in lignes],
                    'Les ventilations multi-valeurs ne sont pas additives. Une première entrée connue n’est pas une première entrée absolue.'],'exploration-fictive.pdf')
    if not calcul_effectue:colonnes=[];details=[]
    query={c:str(form.data.get(c,'')) for c in form.fields}
    for cle in ('origine_rapport','panneau'):
        if contexte_retour.get(cle):query[cle]=contexte_retour[cle]
    if cible:query.update(modele_cible=str(cible.pk),attendu_modele=attendu_modele)
    page=Paginator(details if form.cleaned_data.get('affichage')=='detail' else lignes,50).get_page(contexte_retour.get('page'))
    if calcul_effectue and form.cleaned_data.get('affichage')!='detail':
        for ligne in page:
            ligne['url_preuves']=preuves.lien(request.user,{**form.cleaned_data,**contexte_retour},ligne['_code_mesure'],ligne,page.number)
    parties,niveaux_composition=composition.presenter(form,request)
    from urllib.parse import urlencode
    return render(request,'exploration/rapport.html',{'calcul_effectue':calcul_effectue,'modele_cible':cible,'attendu_modele':attendu_modele,'nom_modele_saisi':request.POST.get('nom',cible.nom if cible else ''),'parties_analyse':parties,'niveaux_composition':niveaux_composition,'origine_rapport':contexte_retour.get('origine_rapport',''),'retour_rapport_source':retour_origine(request.user,contexte_retour.get('origine_rapport')), 'liens_totaux':liens_totaux,'form':form,'colonnes_detail':colonnes,'qualite_mesures':qualite_mesures,'champs_courants':[f for f in form if f.name in ('population','debut','fin','reference','periode','mesure','axe','croisement')],'champs_complementaires':[f for f in form if f.name not in ('population','debut','fin','reference','periode','mesure','axe','croisement')],'niveaux_actifs':[i for i in range(3,8) if form.data.get('axe'+str(i))],'page_obj':page,'query_rapport':urlencode(query),'totaux':totaux,'quantites_inconnues':sum(x['quantite'] is None for x in selection) if calcul_effectue else 0,'nombre':nombre,'modele':modele,
        'modeles':[x for x in m.ModeleRapport.objects.filter(auteur=request.user) if x.parametres.get('exploration')]},status=statut)


@never_cache
@require_http_methods(['POST'])
@login_required
def supprimer_modele(request,pk):
    from .suivi import exiger
    exiger(request.user,'view_modelerapport','add_modelerapport')
    x=get_object_or_404(m.ModeleRapport,pk=pk,auteur=request.user)
    if not x.parametres.get('exploration'):
        from django.http import Http404
        raise Http404
    x.delete()
    return redirect('dossiers:explorer')


@never_cache
@require_http_methods(['GET','POST'])
@login_required
def echanger_modele(request,pk=None):
    from . import modeles_echange as echange
    from .suivi import exiger
    from django.urls import reverse
    from .champs_saisie import FormulaireMetier
    exiger(request.user,'view_modelerapport','add_modelerapport')
    if pk is not None:
        modele=get_object_or_404(m.ModeleRapport,pk=pk,auteur=request.user)
        try:contenu=echange.exporter(request.user,modele)
        except ValidationError as erreur:return HttpResponse(' '.join(erreur.messages),status=422,content_type='text/plain; charset=utf-8')
        r=HttpResponse(contenu,content_type='application/json');r['Content-Disposition']='attachment; filename="modele-exploration.json"';return r
    class ImportForm(FormulaireMetier):
        fichier=forms.FileField(label='Fichier JSON de modèle personnel',help_text='Paramètres uniquement, 64 Kio maximum. Les droits et critères sont revalidés ; aucun résultat ni dossier n’est importé.')
    form=ImportForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        try:
            x=echange.importer(request.user,form.cleaned_data['fichier'].read(echange.MAX_MODELE+1))
        except ValidationError as erreur:form.add_error('fichier',erreur)
        else:return redirect(reverse('dossiers:explorer')+'?modele='+str(x.pk))
    return render(request,'exploration/importer.html',{'form':form})


@never_cache
@require_http_methods(['GET'])
@login_required
def justificatifs(request,fait=False):
    from . import justificatifs_exploration as p
    from django.urls import reverse
    from urllib.parse import urlencode
    from django.http import Http404
    token=request.GET.get('preuve','')
    try:
        payload,form,cellule=p.lire(request.user,token)
        contexte=dict(retour=p.retour_analyse(payload),cellule=cellule,form=form,
            population=dict(e.POPULATIONS)[form.cleaned_data['population']],
            mesure=dict(form.fields['mesure'].choices)[payload['mesure']],
            unite_affichee=cellule['unite'] if payload['mesure'] in ('quantite','minimum','maximum','moyenne') else 'personnes-nuitées' if payload['mesure'] in e.mesures.NUITEES else 'personnes distinctes' if payload['mesure'] in ('personnes',*e.mesures.PERSONNES) else 'ménages distincts' if payload['mesure']=='menages' else 'objets' if payload['mesure']=='objets' else 'unités déclarées',
            preuve=token)
        if fait:
            x,champs,native=p.fiche_objet(request.user,form.cleaned_data,cellule,request.GET.get('objet',''),token,request.GET.get('page','1'))
            contexte.update(objet=x,champs=champs,native=native,
                retour_faits=reverse('dossiers:explorer_justificatifs')+'?'+urlencode({'preuve':token,'page':request.GET.get('page','1')}))
            return render(request,'exploration/fait.html',contexte)
        lignes,regle=p.contributions(request.user,form.cleaned_data,payload['mesure'],cellule,token,request.GET.get('page','1'))
        if request.GET.get('format')=='csv':
            r=HttpResponse(content_type='text/csv; charset=utf-8');r['Content-Disposition']='attachment; filename="justificatifs-exploration.csv"'
            w=csv.writer(r,delimiter=';');w.writerow(['Mesure','Unité','Total de la partie','Contribution','Période','Valeur','Objet'])
            for l in lignes:w.writerow([cellule_csv(v) for v in [contexte['mesure'],cellule['unite'],cellule['valeur'],l['libelle'],l['periode'],l['valeur'],l['objet']]])
            return r
        page=Paginator(lignes,50).get_page(request.GET.get('page'))
        # Les liens des objets conservent la page réellement affichée.
        for ligne in page:
            ligne['url']=reverse('dossiers:explorer_fait')+'?'+urlencode({'preuve':token,'objet':ligne['objet'],'page':page.number})
        connus=[l['valeur'] for l in lignes if l['valeur'] is not None]
        calcul=''
        if payload['mesure']=='moyenne':calcul=f'Somme des quantités connues : {sum(connus)} ; nombre d’objets avec une quantité connue : {len(connus)}. Moyenne arrondie au centième.'
        elif payload['mesure'] in ('minimum','maximum'):calcul=f'Quantités connues comparées : {len(connus)} ; objets sans valeur connue : {len(lignes)-len(connus)}.'
        contexte.update(page_obj=page,query_rapport=urlencode({'preuve':token}),regle=regle,calcul=calcul)
        return render(request,'exploration/justificatifs.html',contexte)
    except ValidationError as erreur:
        return render(request,'exploration/preuve_perimee.html',{'erreur':erreur,'retour':getattr(erreur,'retour',p.retour_analyse(payload) if 'payload' in locals() else reverse('dossiers:explorer'))},status=409)


@never_cache
@require_http_methods(['GET'])
@login_required
def personnaliser(request,source):
    from . import personnalisation_rapports as s
    from django.urls import reverse
    from urllib.parse import urlencode
    if source not in s.SOURCES:
        from django.http import Http404
        raise Http404
    try:params=s.adapter(request.user,source,request.GET)
    except (ValidationError,ValueError) as erreur:
        return render(request,'exploration/personnalisation_refusee.html',{'erreur':erreur,
            'retour':reverse(s.SOURCES[source])+'?'+urlencode({k:v for k,v in request.GET.items() if k not in ('format','page')})},status=422)
    params['origine_rapport']=s.signer_origine(request.user,source,request.GET)
    return redirect(reverse('dossiers:explorer')+'?'+urlencode(params))
