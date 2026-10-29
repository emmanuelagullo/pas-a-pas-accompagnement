import csv
from io import StringIO
from urllib.parse import urlencode
from django import forms
from django.core.exceptions import ValidationError, PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404,render,redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from . import assemblages as a, analyses, models as m, modeles_personnels as gestion
from .forms_hebergement import date_champ
from .champs_saisie import FormulaireMetier
from .vues_analyses import ConservationForm,description_modele


class PeriodeForm(FormulaireMetier):
    from .periodes_rapports import PERIODES
    periode=forms.ChoiceField(label='Période commune (facultative)',choices=[('','Dates fixes'),*PERIODES.items()],required=False)
    debut=date_champ('Début inclus de la période commune',False)
    fin=date_champ('Fin exclue de la période commune',False)
    decalage_debut=forms.IntegerField(label='Début relatif en jours',required=False,min_value=-36600,max_value=36600)
    decalage_fin=forms.IntegerField(label='Fin relative en jours',required=False,min_value=-36600,max_value=36600)
    from .presentation_exports import CHOIX
    export_prioritaire=forms.ChoiceField(label='Export à mettre en avant',choices=CHOIX,required=False)
    filtre=forms.ChoiceField(label='Dossiers',required=False,choices=[('','Conserver les dossiers propres à chaque partie'),('tous','Tous les dossiers accessibles'),('mes','Mes dossiers'),('service','Mon service'),('attente','En attente')])


@never_cache
@login_required
@require_http_methods(['GET','POST'])
def assemblage(request):
    if not request.user.has_perms(['personnes.view_modelerapport','personnes.add_modelerapport']):raise PermissionDenied
    source=request.POST if request.method=='POST' else request.GET
    modele=get_object_or_404(m.ModeleRapport,pk=source['modele'],auteur=request.user) if source.get('modele') else None
    cible=modele or (get_object_or_404(m.ModeleRapport,pk=source['cible'],auteur=request.user) if source.get('cible') else None)
    erreurs=[];statut=200
    try:d=a.lire(modele.parametres) if modele else a.lire(dict(schema=2,assemblage=True,definition=source['definition'])) if source.get('definition') else a.defaut()
    except ValidationError as exc:return render(request,'analyses/erreur.html',{'erreurs':exc.messages},status=422)
    f=PeriodeForm(request.POST if request.method=='POST' else None,initial=d)
    sauvegarde=ConservationForm(request.POST if request.method=='POST' and source.get('action') in ('creer','remplacer') else None,initial=dict(nom=cible.nom if cible else '',description=cible.description if cible else '',nature=cible.nature if cible else 'modele',attendu=gestion.jeton(request.user,cible) if cible else ''))
    if request.method=='POST':
        action=source.get('action')
        try:
            if action=='ajouter':
                if len(d['parties'])>=12:raise ValidationError('Douze parties au maximum.')
                if source.get('modele_ajoute'):
                    original=get_object_or_404(m.ModeleRapport,pk=source['modele_ajoute'],auteur=request.user)
                    partie=a.photographier(request.user,request,modele=original)
                else:partie=a.photographier(request.user,request,cle=source.get('catalogue'))
                d['parties'].append(partie)
            elif action in ('monter','descendre','retirer','actualiser'):
                try:i=int(source.get('partie'))
                except (ValueError,TypeError):raise ValidationError('Partie inconnue.')
                if not 0<=i<len(d['parties']):raise ValidationError('Partie inconnue.')
                if action=='retirer':d['parties'].pop(i)
                elif action=='actualiser':
                    p=d['parties'][i]
                    original=get_object_or_404(m.ModeleRapport,pk=p.get('modele'),auteur=request.user)
                    nouveau=a.photographier(request.user,request,modele=original);nouveau['periode_commune']=p.get('periode_commune',False);d['parties'][i]=nouveau
                else:
                    j=i-1 if action=='monter' else i+1
                    if not 0<=j<len(d['parties']):raise ValidationError('Déplacement impossible.')
                    d['parties'][i],d['parties'][j]=d['parties'][j],d['parties'][i]
            elif action=='parametrer' and f.is_valid():
                d.update({k:str(v) if v is not None else '' for k,v in f.cleaned_data.items()})
                for i,p in enumerate(d['parties']):
                    p['periode_commune']=source.get('commune'+str(i))=='1'
                    p['titre']=source.get('titre'+str(i),p['titre']).strip()
                    p['description']=source.get('description'+str(i),p.get('description',''))
            elif action in ('creer','remplacer') and sauvegarde.is_valid():
                d=a.valider(request.user,d)
                if not d['parties']:raise ValidationError('Ajoutez au moins une partie avant de conserver.')
                x=gestion.conserver_composition(request.user,cible,sauvegarde.cleaned_data,action,a.parametres(d))
                return redirect(reverse('dossiers:assemblage')+'?'+urlencode({'modele':x.pk}))
        except ValidationError as exc:erreurs.extend(exc.messages);statut=409 if isinstance(exc,gestion.ConflitModele) else 422
    docs=[]
    try:docs=a.documents(request.user,request,d)
    except ValidationError as exc:erreurs.extend(exc.messages);statut=422
    if request.method=='POST' and source.get('format') in ('csv','pdf') and not erreurs:
        from .exports import cellule_csv
        resume=source.get('resume','')
        if len(resume)>6000:return HttpResponse('Résumé trop long.',status=400)
        description=description_modele(cible,request.user) if source.get('inclure_description')=='1' else ''
        if source['format']=='csv':
            # Une table par partie, avec en-tête propre ; aucune fausse table commune.
            s=StringIO();w=csv.writer(s,delimiter=';')
            if description:w.writerow(['# Description',cellule_csv(description)])
            if resume:w.writerow(['# Résumé',cellule_csv(resume)])
            for n,doc in enumerate(docs,1):
                w.writerow(['# Partie',n,cellule_csv(doc['titre'])])
                for nom,valeur in doc['criteres']:w.writerow(['# '+str(nom),cellule_csv(valeur)])
                w.writerow(doc['entete'])
                for b in doc['blocs']:w.writerow([cellule_csv(v) for v in b['valeurs']])
                w.writerow([])
            response=HttpResponse(s.getvalue(),content_type='text/csv; charset=utf-8');response['Content-Disposition']='attachment; filename="assemblage.csv"'
        else:
            from .exports_rapports import produire_pdf
            from .vues_analyses import exporter_document
            # Le moteur PDF du socle est réutilisé, y compris son repli PWA.
            blocs=[]
            for n,doc in enumerate(docs,1):
                blocs.append(dict(groupes=[(2,str(n)+'. '+doc['titre'])],valeurs=[],cellules=([('Description',doc['description'])] if doc.get('description') else [])+doc['criteres']))
                blocs.extend(doc['blocs'])
                if doc.get('complements'):blocs.append(dict(groupes=[(3,'Comparaison de cette partie')],valeurs=[],cellules=doc['complements']))
                blocs.append(dict(groupes=[],valeurs=[],cellules=[('Définitions et limites',doc['notes'])]))
            doc=dict(titre=cible.nom if cible else 'Rapport composé',description=description,resume=resume,criteres=[],entete=[],blocs=blocs,complements=[],large=True,notes='Les parties sont calculées séparément. Aucun total entre parties n’est déduit.')
            response=exporter_document(doc,'pdf')
        response['Cache-Control']='private, no-store';return response
    from .catalogue_rapports import catalogue
    from .presentation_exports import prioritaire
    return render(request,'analyses/assemblage.html',dict(description=description_modele(cible,request.user),definition=analyses.encoder(d),d=d,docs=docs,erreurs=erreurs,form=f,sauvegarde=sauvegarde,cible=cible,personnels=m.ModeleRapport.objects.filter(auteur=request.user),catalogue=catalogue(request.user),prioritaire=prioritaire('assemblage',d)),status=statut)
