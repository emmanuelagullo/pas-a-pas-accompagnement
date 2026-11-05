from copy import deepcopy
from django import forms
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.shortcuts import get_object_or_404
from django.urls import reverse
from personnes.champs_saisie import FormulaireMetier
from .models import Service
from . import services as s, collecte as c
from .profils_collectifs import categories_defaut
from .views import formulaire

class CollecteForm(FormulaireMetier):
    attendu=forms.CharField(widget=forms.HiddenInput)
    profil=forms.ChoiceField(label='Partir d’un profil',choices=[('detail','Suivi personnel détaillé'),('menage','Informations communes au ménage'),('adultes','Informations personnelles des adultes')],required=False)
    def __init__(self,*args,service,regles=None,**kw):
        super().__init__(*args,**kw)
        self.service=service
        self.initial['attendu']=s.jeton(service)
        self.initial['profil']='detail'
        regles=regles or service.collecte_rubriques or c.profil('detail')
        populations=c.POPULATIONS+ [('categorie:'+x['code'],x['libelle']) for x in service.profil_collectif.get('categories',categories_defaut())]
        self.lignes=[]
        for code,(titre,champs) in c.RUBRIQUES.items():
            portees=c.PORTEES if champs else [v for v in c.PORTEES if v[0] in ('personne','non')]
            if code=='identite':portees=[('personne','Personne identifiée')]
            if code=='projet':portees=[v for v in c.PORTEES if v[0] in ('menage','non')]
            self.fields[code+'_portee']=forms.ChoiceField(label=titre+' — rattachement',choices=portees,initial=regles[code]['portee'])
            self.fields[code+'_population']=forms.ChoiceField(label=titre+' — personnes concernées',choices=c.POPULATIONS[:1] if code=='identite' else populations,initial=regles[code]['population'],required=False)
            self.lignes.append((titre,code+'_portee',code+'_population'))
    @property
    def lignes_collecte(self):return [(titre,self[a],self[b]) for titre,a,b in self.lignes]
    def clean(self):
        d=super().clean()
        if self.errors:return d
        regles={code:{'portee':d.pop(code+'_portee'),'population':d.pop(code+'_population') or 'tous'} for code in c.RUBRIQUES}
        c.verifier(regles,self.service.profil_collectif.get('categories',categories_defaut()))
        d.pop('profil',None);d['regles']=regles
        return d

@never_cache
@login_required
@require_http_methods(['GET','POST'])
def configurer(request,service_pk):
    s.exiger_gestion(request.user)
    service=get_object_or_404(Service,pk=service_pk)
    if request.method=='POST' and 'appliquer_profil' in request.POST:
        choix=request.POST.get('profil','detail')
        choix=choix if choix in ('menage','adultes','detail') else 'detail'
        f=CollecteForm(service=service,regles=c.profil(choix))
        f.initial['profil']=choix
    else:f=CollecteForm(request.POST if request.method=='POST' else None,service=service)
    def sauver(attendu,regles):
        s.reserver(service,attendu)
        c.verifier(regles,service.profil_collectif.get('categories',categories_defaut()))
        avant=deepcopy(service.collecte_rubriques)
        service.collecte_rubriques=regles;service.save(update_fields=['collecte_rubriques'])
        s.journal(request.user,service,'collecte_rubriques',avant,regles)
    return formulaire(request,f,'Rubriques sociales — '+service.libelle,sauver,reverse('acteurs:service',args=[service.pk]))
