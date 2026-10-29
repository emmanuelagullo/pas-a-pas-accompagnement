"""Composition, exécution et preuves des analyses à mesures indépendantes."""
import csv
from copy import copy
from io import StringIO
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
from django import forms
from django.core import signing
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.response import TemplateResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from acteurs.statistiques import selection, reponse_bornee
from . import analyses as a, exploration as e, models as m, modeles_personnels as gestion
from .forms_analyses import AnalyseForm, aplatir
from .exports import cellule_csv
from . import justificatifs_exploration as preuves


class ConservationForm(forms.Form):
    nom=forms.CharField(label='Nom à conserver',max_length=100)
    description=forms.CharField(label='Explication du modèle (facultative)',max_length=6000,required=False,widget=forms.Textarea(attrs={'rows':3}))
    nature=forms.ChoiceField(label='Conserver comme',choices=[('modele','Modèle'),('personnalisation','Personnalisation de ce modèle'),('ensemble','Un modèle et sa personnalisation')])
    nom_modele=forms.CharField(label='Nom du nouveau modèle (si vous conservez les deux)',max_length=100,required=False)
    attendu=forms.CharField(required=False,widget=forms.HiddenInput)


def description_modele(modele,acteur):
    if modele is None:return ''
    if modele.description:return modele.description
    parent=modele.modele_source
    return parent.description if parent and parent.auteur_id==acteur.pk else ''


def url_analyse(d,**kw):
    return reverse('dossiers:analyse')+'?'+urlencode({'definition':a.encoder(d),**kw})


def jeton_preuve(acteur,d,n,cellule,page,contexte=None):
    return signing.dumps(dict(acteur=str(acteur.pk),definition=d,mesure=n,cellule=cellule['_cellule'],empreinte=preuves.empreinte(cellule['_objets']),page=page,retour=contexte or {}),salt='analyse-preuve-v2',compress=True)


def document(resultat,titre='Analyse composée',description='',resume=''):
    d=resultat['definition'];entete=['Mesure','Classement','Unité','Valeur'];lignes=[]
    if d['affichage']=='detail':
        entete=['Objet',*[e.DIMENSIONS[c] for c in d.get('colonnes',[])],*[r['titre'] for r in resultat['mesures']]]
        for x in resultat['details']:
            lignes.append([x['projection']['libelle'],*x['projection']['valeurs'],*[' ; '.join(str(v)+' '+u if v is not None else 'Non renseigné — '+u for u,v in ms.items()) for ms in x['mesures']]])
    else:
        for r in resultat['mesures']:
            for x in r['lignes']:
                lignes.append([r['titre'],('Sous-total : ' if x.get('sous_total') else '')+' / '.join([x['axe'],x['croisement'],*x['niveaux']]),x['unite'],x['valeur']])
            for u,v in r['totaux'].items():lignes.append([r['titre'],'Total recalculé',u,v])
    tampon=StringIO();w=csv.writer(tampon,delimiter=';');w.writerow(entete)
    for x in lignes:w.writerow([cellule_csv(v) for v in x])
    csv_r=HttpResponse(tampon.getvalue(),content_type='text/csv; charset=utf-8');csv_r['Content-Disposition']='attachment; filename="analyse.csv"'
    criteres=[('Période',str(d['debut'])+' → '+str(d['fin'])+' (fin exclue)'),('Référence personnelle',str(d['reference'])),('Source sociale','SituationPersonnelle saisie à la référence ; déclarations détaillées distinctes')]
    for c in d.get('criteres',[]):criteres.append(('Condition',('Avec' if c.get('mode','avec')=='avec' else 'Sans')+' · '+dict(e.POPULATIONS)[c['source']]+' · même '+c.get('relation','personne')+' · '+str(c.get('filtres',[]))))
    for r in resultat['mesures']:
        p=r['configuration'];criteres.append((r['titre'],dict(e.POPULATIONS)[p['population']]+' · '+p.get('mouvement','chevauche')+' · '+p.get('portion','selection')+' · '+str(next((x.get('filtres',[]) for i,x in enumerate(d['mesures']) if i==r['index']),[]))))
    return dict(titre=titre,description=description,resume=resume,criteres=criteres,entete=entete,
                blocs=[dict(groupes=[],valeurs=x,cellules=list(zip(entete,x))) for x in lignes],complements=[],large=len(entete)>7,csv=csv_r,
                notes='Les unités restent séparées. Les totaux distincts sont recalculés ; les groupes peuvent se recouvrir. Aucune réalisation n’est déduite d’une autorisation.')


def exporter_document(doc,format):
    if format=='csv':
        r=doc['csv']
        if doc.get('resume') or doc.get('description'):
            s=StringIO();w=csv.writer(s,delimiter=';')
            for nom,cle in [('Description','description'),('Résumé','resume')]:
                if doc.get(cle):w.writerow(['# '+nom,cellule_csv(doc[cle])])
            r.content=s.getvalue().encode()+r.content
    elif format=='pdf':
        from .exports_rapports import produire_pdf
        r=HttpResponse(produire_pdf(doc),content_type='application/pdf');r['Content-Disposition']='attachment; filename="rapport.pdf"'
    else:raise ValidationError('Format d’export inconnu.')
    r['Cache-Control']='private, no-store';r['X-Content-Type-Options']='nosniff'
    return r


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def analyse(request):
    e.disponibles(request.user)
    modele=get_object_or_404(m.ModeleRapport,pk=request.GET['modele'],auteur=request.user) if request.GET.get('modele') else None
    source=request.POST if request.method=='POST' else request.GET
    cible=modele
    if source.get('cible'):cible=get_object_or_404(m.ModeleRapport,pk=source['cible'],auteur=request.user)
    try:
        if modele:d=a.lire(modele.parametres)
        elif source.get('definition'):d=a.lire(dict(schema=2,analyse=True,definition=source['definition']))
        elif source.get('ancien'):
            ancien=get_object_or_404(m.ModeleRapport,pk=source['ancien'],auteur=request.user)
            gestion.exiger(request.user,ancien)
            from .traduction_analyses import depuis_exploration
            d=depuis_exploration(request.user,ancien.parametres)
        else:d=a.defaut()
    except ValidationError as exc:return render(request,'analyses/erreur.html',{'erreurs':exc.messages},status=422)
    if 'filtre' in source:d['filtre']=source['filtre']
    # Le formulaire modifié prime sur sa définition de départ, jamais sur un autre compte.
    valeurs=source.copy() if 'nombre_mesure' in source else aplatir(d)
    if 'filtre' in source:valeurs['filtre']=source['filtre']
    def incrementer(cle,maximum,defaut=0):
        try:n=int(valeurs.get(cle,defaut))
        except (ValueError,TypeError):n=defaut
        valeurs[cle]=min(n+1,maximum)
    action=source.get('ajouter','')
    if action in ('critere','mesure','axes','colonnes'):
        incrementer('nombre_'+action,20 if action=='critere' else 12 if action=='mesure' else 7 if action=='axes' else 11)
        i=valeurs['nombre_'+action]
        if action in ('critere','mesure'):
            for k,v in dict(source='prises' if action=='critere' else 'repas',mesure='objets' if action=='critere' else 'quantite',mode='avec',relation='personne',mouvement='chevauche',portion='selection',cohorte='tous',nombre_filtres=0).items():valeurs.setdefault(f'{action}{i}_{k}',v)
        else:valeurs.setdefault(action+str(i),'total' if action=='axes' else 'personne')
    elif action.startswith(('critere','mesure')) and action.endswith('_filtre'):
        prefixe=action[:-6];incrementer(prefixe+'nombre_filtres',20)
        i=valeurs[prefixe+'nombre_filtres'];valeurs.setdefault(prefixe+f'f{i}_operation','egal')
    # Retrait et ordre modifient seulement la partie choisie, même si une autre
    # partie comporte une erreur de saisie.
    if action.startswith('retirer-'):
        identifiant=action[len('retirer-'):]
        import re
        match=re.fullmatch(r'(critere|mesure|axes|colonnes)([0-9]+)',identifiant)
        if match:
            cle,i=match[1],int(match[2]);compte='nombre_'+cle
            try:n=int(valeurs.get(compte,0))
            except (ValueError,TypeError):n=0
            mini=1 if cle in ('mesure','axes') else 0
            if 1<=i<=n and n>mini:
                if cle in ('critere','mesure'):
                    copie=dict(valeurs.items())
                    for k in list(valeurs):
                        if re.match(rf'{cle}[0-9]+_',k):del valeurs[k]
                    for j in range(1,n+1):
                        if j==i:continue
                        for k,v in copie.items():
                            prefixe=f'{cle}{j}_'
                            if k.startswith(prefixe):valeurs[f'{cle}{j if j<i else j-1}_'+k[len(prefixe):]]=v
                else:
                    for j in range(i,n):
                        valeurs[cle+str(j)]=valeurs.get(cle+str(j+1),'')
                        if cle=='axes':valeurs['classes'+str(j)]=valeurs.get('classes'+str(j+1),'')
                    valeurs.pop(cle+str(n),None)
                valeurs[compte]=n-1
    elif action.startswith('monter-axe'):
        try:i=int(action[len('monter-axe'):]);n=int(valeurs.get('nombre_axes',1))
        except (ValueError,TypeError):i=n=0
        if 1<i<=n:
            for cle in ('axes','classes'):
                valeurs[cle+str(i-1)],valeurs[cle+str(i)]=valeurs.get(cle+str(i),''),valeurs.get(cle+str(i-1),'')
    form=AnalyseForm(valeurs,acteur=request.user)
    resultat=None;erreurs=[];statut=200
    with selection(request.user,d,'analyse'):
        if form.is_valid():
            try:
                d=a.valider(request.user,form.definition())
                resultat=a.calculer(request.user,d)
            except ValidationError as exc:form.add_error(None,exc.messages)
        if resultat:
            fige=a.valider(request.user,d,figer=True)
            page=source.get('page','1')
            retour_context={'cible':cible.pk,'attendu':source.get('attendu','')} if cible else {}
            if source.get('retour_assemblage'):retour_context['retour_assemblage']=source['retour_assemblage']
            for r in resultat['mesures']:
                r['_totaux']=[]
                for x in [*r['lignes'],*preuves.totaux_cellules(r['totaux'],r['objets'],r['configuration']['mesure'])]:
                    x['url_preuves']=reverse('dossiers:analyse_preuves')+'?'+urlencode({'preuve':jeton_preuve(request.user,fige,r['index'],x,page,retour_context)})
                    if '_totaux' not in r:r['_totaux']=[]
                    if x['_cellule'].get('total') is not None:r['_totaux'].append(x)
                r['totaux_affiches']=r['_totaux']
            for x in resultat['details']:
                x['cellules_affichees']=[]
                for n,js in enumerate(x['justifications']):
                    for cellule in js:cellule['url_preuves']=reverse('dossiers:analyse_preuves')+'?'+urlencode({'preuve':jeton_preuve(request.user,fige,n,cellule,page,retour_context)})
                    x['cellules_affichees'].append(js)
            if resultat['details']:
                base=a.configuration(request.user,d,dict(source=d['lignes'],mesure='objets'),classement=False)
                from .exploration_releve import relever
                _,ls=relever({**base,'_analyse_definition':a.encoder(d),'_analyse_retour_assemblage':source.get('retour_assemblage',''),'page':page},[x['objet'] for x in resultat['details']],request.user)
                for x,projection in zip(resultat['details'],ls):
                    if not d.get('colonnes'):projection['valeurs']=[]
                    x['projection']=projection
            if source.get('format') in ('pdf','csv'):
                resume=source.get('resume','')
                if len(resume)>6000:return render(request,'analyses/erreur.html',{'erreurs':['Le résumé dépasse 6 000 caractères. Revenez au rapport pour le raccourcir.']},status=422)
                return exporter_document(document(resultat,cible.nom if cible else 'Analyse composée',description_modele(cible,request.user) if source.get('inclure_description')=='1' else '',resume),source['format'])
        if source.get('format') and not resultat:statut=422
        peut_conserver=request.user.has_perms(['personnes.view_modelerapport','personnes.add_modelerapport'])
        initial=dict(nom=cible.nom if cible else '',description=cible.description if cible else '',nature=cible.nature if cible else 'modele',attendu=source.get('attendu',gestion.jeton(request.user,cible)) if cible and peut_conserver else '')
        sauvegarde=ConservationForm(request.POST if request.method=='POST' and source.get('action') else None,initial=initial)
        if request.method=='POST' and source.get('action') and resultat and sauvegarde.is_valid():
            if not peut_conserver:raise PermissionDenied
            try:
                x=gestion.conserver_composition(request.user,cible,sauvegarde.cleaned_data,source['action'],a.parametres(d))
            except ValidationError as exc:sauvegarde.add_error(None,exc.messages);statut=409 if isinstance(exc,gestion.ConflitModele) else 400
            else:return redirect(reverse('dossiers:analyse')+'?'+urlencode({'modele':x.pk}))
        parties=[]
        for nom,titre in [('retenir','Retenir'),('afficher','Afficher'),('compter','Compter'),('classer','Classer')]:
            blocs=[]
            for bloc in form.parties['critere' if nom=='retenir' else 'mesure'] if nom in ('retenir','compter') else []:
                blocs.append({**bloc,'champs':[form[k] for k in bloc['champs']],'regles':[form[k] for k in bloc['regles']],'filtres':[[form[k] for k in fs] for fs in bloc['filtres']]})
            compteur=len(d.get('criteres',[])) if nom=='retenir' else len(d.get('colonnes',[])) if nom=='afficher' else len(d.get('mesures',[])) if nom=='compter' else sum(x!='total' for x in d.get('axes',[]))
            regles_generales={'retenir':{'reference_mode','reference','decalage_debut','decalage_fin'},'afficher':{'affichage','export_prioritaire'},'classer':{'sous_totaux'}}.get(nom,set())
            champs=[form[k] for k in form.groupes[nom] if k not in regles_generales]
            regles=[form[k] for k in form.groupes[nom] if k in regles_generales]
            resume=(' · '.join(('Sans' if c.get('mode')=='sans' else 'Avec')+' '+dict(e.POPULATIONS).get(c.get('source'),'faits') for c in d.get('criteres',[])) or 'Aucun critère supplémentaire') if nom=='retenir' else ' · '.join(e.DIMENSIONS.get(c,c) for c in d.get('colonnes',[])) if nom=='afficher' else ' · '.join(c.get('titre') or dict(e.POPULATIONS).get(c.get('source'),'faits') for c in d.get('mesures',[])) if nom=='compter' else ' → '.join(e.DIMENSIONS.get(c,c) for c in d.get('axes',[]) if c!='total') or 'Aucun regroupement'
            parties.append(dict(nom=nom,titre=titre,champs=champs,regles=regles,resume=resume,blocs=blocs,compteur=compteur,ouvert=source.get('panneau')==nom or (nom=='retenir' and not cible and not source.get('definition') and not source.get('nombre_mesure')) or bool(form.errors)))
        from .presentation_exports import prioritaire
        ctx=dict(description=description_modele(cible,request.user),nouveau=not cible and not source.get('definition') and not source.get('nombre_mesure') and not source.get('ancien'),form=form,parties=parties,resultat=resultat,sauvegarde=sauvegarde,peut_conserver=peut_conserver,cible=cible,definition=a.encoder(d),prioritaire=prioritaire('analyse',d),page_obj=Paginator(resultat['details'],50).get_page(source.get('page')) if resultat and d['affichage']=='detail' else None)
        reponse=TemplateResponse(request,'analyses/rapport.html',ctx,status=statut)
        return reponse_bornee(reponse,request.user,d,'analyse')


@never_cache
@login_required
@require_http_methods(['GET'])
def justificatifs(request):
    token=request.GET.get('preuve','')
    if len(token)>100000:raise Http404
    try:p=signing.loads(token,salt='analyse-preuve-v2',max_age=86400)
    except (signing.BadSignature,TypeError,ValueError):raise Http404
    if not isinstance(p,dict) or p.get('acteur')!=str(request.user.pk):raise Http404
    d=p.get('definition');retour=url_analyse(d,page=p.get('page','1'),**p.get('retour',{}))
    try:
        with selection(request.user,d,'analyse'):
            r=a.calculer(request.user,d)
            n=p.get('mesure')
            if not isinstance(n,int) or n<0 or n>=len(r['mesures']):raise Http404
            mesure=r['mesures'][n];cfg=mesure['configuration'];code=cfg['mesure']
            cellules=[*mesure['lignes'],*preuves.totaux_cellules(mesure['totaux'],mesure['objets'],code)]
            if isinstance(p.get('cellule'),dict) and p['cellule'].get('detail'):
                detail=next((x for x in r['details'] if x['objet']['id']==p['cellule']['detail']),None)
                cellules=detail['justifications'][n] if detail else []
            cellule=next((x for x in cellules if preuves.canonique(x['_cellule'])==preuves.canonique(p.get('cellule'))),None)
            if cellule is None or preuves.empreinte(cellule['_objets'])!=p.get('empreinte'):raise ValidationError('Les données ont changé. Recalculez l’analyse avant de consulter ses justificatifs.')
            contexte=dict(retour=retour,population=dict(e.POPULATIONS)[cfg['population']],mesure=mesure['titre'],cellule=cellule,unite_affichee=cellule['unite'],preuve=token)
            f=ExplorationForm(cfg,acteur=request.user);f.is_valid();contexte['form']=f
            if request.GET.get('objet'):
                x,champs,native=preuves.fiche_objet(request.user,cfg,cellule,request.GET['objet'],token,request.GET.get('page','1'))
                if native:
                    from .exploration_releve import signer_retour
                    u=urlsplit(native);q=dict(parse_qsl(u.query));q['retour_exploration']=signer_retour(request.user,{'_analyse_preuve':token,'page':request.GET.get('page','1')})
                    native=urlunsplit((u.scheme,u.netloc,u.path,urlencode(q),u.fragment))
                contexte.update(objet=x,champs=champs,native=native,retour_faits=reverse('dossiers:analyse_preuves')+'?'+urlencode({'preuve':token,'page':request.GET.get('page','1')}))
                return render(request,'exploration/fait.html',contexte)
            ls,regle=preuves.contributions(request.user,cfg,code,cellule,token,request.GET.get('page','1'))
            if request.GET.get('format')=='csv':
                s=StringIO();w=csv.writer(s,delimiter=';');w.writerow(['Contribution','Période','Valeur','Objet'])
                for l in ls:w.writerow([cellule_csv(l[c]) for c in ('libelle','periode','valeur','objet')])
                response=HttpResponse(s.getvalue(),content_type='text/csv; charset=utf-8');response['Content-Disposition']='attachment; filename="contributions.csv"';return response
            page=Paginator(ls,50).get_page(request.GET.get('page'))
            for l in page:l['url']=reverse('dossiers:analyse_preuves')+'?'+urlencode({'preuve':token,'objet':l['objet'],'page':page.number})
            contexte.update(page_obj=page,regle=regle,query_rapport=urlencode({'preuve':token}))
            return render(request,'exploration/justificatifs.html',contexte)
    except ValidationError as exc:return render(request,'exploration/preuve_perimee.html',{'erreur':exc,'retour':retour},status=409)


from .forms_exploration import ExplorationForm
