"""Restitution commune depuis les sélections et les CSV natifs, sans nouveau calcul."""
import csv
from io import StringIO
from copy import copy
from django import forms
from django.conf import settings
from django.core import signing
from django.core.exceptions import ValidationError
from django.http import HttpResponse,QueryDict
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .exports import cellule_csv
from . import catalogue_rapports as c,models as m

class ExportForm(forms.Form):
    definition=forms.CharField(widget=forms.HiddenInput)
    resume=forms.CharField(required=False,max_length=6000)
    inclure_description=forms.BooleanField(required=False)
    format=forms.ChoiceField(choices=[('pdf','PDF'),('csv','CSV')])

def requete_source(request,source,params):
    from .vues_rapports import reponse_source
    if source!='exploration':return reponse_source(request,source,params)
    from .vues_exploration import explorer
    r=copy(request);r.method='GET';r.GET=QueryDict('',mutable=True);r.POST=QueryDict('')
    for k,v in params.items():r.GET[k]=str(v)
    return explorer(r)

def document(request,d,resume='',inclure_description=False):
    from .periodes_rapports import resoudre
    params=d['parametres'].copy();regle=params.get('periode','');params['periode']='';params.pop('format',None);params.pop('page',None)
    source=d['source']
    cible=m.ModeleRapport.objects.filter(pk=d.get('cible'),auteur=request.user).select_related('modele_source').first() if d.get('cible') else None
    r=requete_source(request,source,params);ctx=getattr(r,'context_data',None)
    if ctx is None or r.status_code!=200:raise ValidationError('Le rapport ne peut pas être exporté avec ces critères.')
    f=ctx.get('form') or ctx.get('formulaire')
    if f is None or not f.is_valid():raise ValidationError('Corrigez les critères avant d’exporter.')
    description=(cible.description or (cible.modele_source.description if cible.modele_source and cible.modele_source.auteur_id==request.user.pk else '')) if cible else ''
    titre=cible.nom if cible else ctx.get('titre_rapport') or (c.SOURCES[source][0] if source!='exploration' else 'Analyse des populations')
    from .periodes_rapports import PERIODES
    criteres=[('Règle de la sélection affichée',PERIODES.get(regle,regle))] if regle else []
    for nom,champ in f.fields.items():
        if nom not in f.cleaned_data or (f.cleaned_data[nom] is None or f.cleaned_data[nom] is False or f.cleaned_data[nom]=='') or champ.widget.is_hidden:continue
        v=f.cleaned_data[nom]
        if source=='exploration' and (nom.startswith('operation') or nom.startswith('valeur')):continue
        if source=='exploration' and nom.startswith('filtre') and nom[6:].isdigit():
            i=nom[6:];op=f.cleaned_data.get('operation'+i,'');val=f.cleaned_data.get('valeur'+i,'')
            criteres.append(('Critère '+i,str(dict(champ.choices).get(v,v))+' · '+str(dict(f.fields['operation'+i].choices).get(op,op))+' · '+str(val)))
            continue
        try:v=dict(champ.choices).get(str(v),str(v))
        except AttributeError:v=str(v)
        criteres.append((champ.label or nom,str(v)))
    csv_r=requete_source(request,source,{**params,'format':'csv_detail' if source=='exploration' and f.cleaned_data.get('affichage')=='detail' else 'csv'})
    if csv_r.status_code!=200 or not csv_r.get('Content-Type','').startswith('text/csv'):raise ValidationError('Le rapport n’a pas produit de données exportables.')
    table=list(csv.reader(StringIO(csv_r.content.decode('utf-8-sig')),delimiter=',' if source=='statistiques' else ';'))
    if not table:raise ValidationError('En-tête manquant.')
    entete,*lignes=table;blocs=[];precedent=()
    axes=[i for i,h in enumerate(entete) if h in ('Axe','Croisement') or h.startswith('Niveau ')] if source=='exploration' and f.cleaned_data.get('affichage')!='detail' else []
    for row in lignes:
        chemin=tuple(row[i] for i in axes if i<len(row) and row[i])
        groupes=[(i+2,v) for i,v in enumerate(chemin) if i>=len(precedent) or chemin[:i+1]!=precedent[:i+1]]
        indices=[i for i,h in enumerate(entete) if h not in ('Population','Référence','Axe','Croisement') and not h.startswith('Niveau ')] if axes else list(range(len(entete)))
        valeurs=[row[i] if i<len(row) else '' for i in indices]
        blocs.append(dict(groupes=groupes,cellules=[(entete[i],row[i] if i<len(row) else '') for i in indices],valeurs=valeurs));precedent=chemin
    if axes:entete=[h for h in entete if h not in ('Population','Référence','Axe','Croisement') and not h.startswith('Niveau ')]
    complements=[]
    if ctx.get('comparaison'):complements=[('Période précédente — '+str(k).replace('_',' '),str(v)) for k,v in ctx['comparaison'].items()]
    if ctx.get('mouvements_comparaison'):complements=[('Période précédente — '+str(nom),str(avant)) for nom,avant,apres in ctx['mouvements_comparaison']]
    if ctx.get('erreur_comparaison'):raise ValidationError(ctx['erreur_comparaison'])
    return dict(titre=titre,resume=resume,description=description if inclure_description else '',criteres=criteres,entete=entete,blocs=blocs,complements=complements,large=len(entete)>7,csv=csv_r,notes='Les ventilations et sous-totaux peuvent se recouvrir. Les totaux distincts sont recalculés ; les unités, devises et phases restent séparées.')

def produire_pdf(doc):
    from pas_communs.pdf import rendre_html,fiche_texte
    if getattr(settings,'MODE_PWA',False):
        lignes=['Prototype d’essai — données fictives uniquement',*(['Description : '+doc['description']] if doc['description'] else []),*(['Résumé : '+doc['resume']] if doc['resume'] else []),*[k+' : '+v for k,v in doc['criteres']]]
        for bloc in doc['blocs']:
            lignes.extend(val for niveau,val in bloc['groupes'])
            lignes.extend(k+' : '+str(v) for k,v in bloc['cellules'])
        lignes.extend(k+' : '+v for k,v in doc['complements']);lignes.append(doc['notes'])
        return fiche_texte(doc['titre'],lignes)
    def refuser(url):raise ValueError('Ressource externe interdite.')
    return rendre_html(render_to_string('rapports/pdf.html',doc),base_url=None,feuille_style=settings.BASE_DIR/'static/rapports-pdf.css',recuperer=refuser)

@login_required
@require_POST
def exporter(request):
    f=ExportForm(request.POST)
    if not f.is_valid():return HttpResponse('Options d’export invalides.',status=400)
    try:
        d=signing.loads(f.cleaned_data['definition'],salt='reglages-rapport-v1',max_age=86400)
        if not isinstance(d,dict) or d.get('acteur')!=str(request.user.pk):raise signing.BadSignature()
    except (signing.BadSignature,ValueError,TypeError):return HttpResponse('Définition d’export périmée ou non vérifiable.',status=409)
    if d.get('source') not in (*c.SOURCES,'exploration'):return HttpResponse('Source inconnue.',status=400)
    try:
        doc=document(request,d,f.cleaned_data['resume'],f.cleaned_data['inclure_description'])
        if f.cleaned_data['format']=='csv':
            r=doc['csv']
            if doc['resume'] or doc['description']:
                tampon=StringIO();w=csv.writer(tampon,delimiter=',' if d['source']=='statistiques' else ';')
                if doc['description']:w.writerow(['# Description',cellule_csv(doc['description'])])
                if doc['resume']:w.writerow(['# Résumé',cellule_csv(doc['resume'])])
                r.content=tampon.getvalue().encode()+r.content
        else:
            r=HttpResponse(produire_pdf(doc),content_type='application/pdf');r['Content-Disposition']='attachment; filename="rapport.pdf"'
    except (ValidationError,ValueError,OverflowError) as e:return HttpResponse('Export impossible : '+str(e),status=422,content_type='text/plain; charset=utf-8')
    r['Cache-Control']='private, no-store';r['X-Content-Type-Options']='nosniff';return r
