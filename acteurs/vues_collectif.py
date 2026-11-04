from copy import deepcopy
from django import forms
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.shortcuts import get_object_or_404
from django.urls import reverse
from . import services as s
from .models import Service
from .profils_collectifs import defaut, verifier, MODES, IDENTIFICATIONS
from .views import formulaire
from personnes.champs_saisie import FormulaireMetier

class ProfilForm(FormulaireMetier):
    actif=forms.BooleanField(label='Activer le parcours collectif de ce service',required=False)
    identification=forms.ChoiceField(label='Personnes à identifier',choices=IDENTIFICATIONS)
    hebergement=forms.ChoiceField(label='Suivi de l’hébergement',choices=MODES)
    restauration=forms.ChoiceField(label='Suivi de la restauration',choices=MODES)
    petits_dejeuners=forms.BooleanField(label='Proposer les petits déjeuners avec l’hébergement',required=False)
    aides=forms.MultipleChoiceField(label='Autres familles de prestations proposées',choices=[('transport','Transport'),('bon_alimentaire','Bons alimentaires'),('produits','Produits alimentaires'),('accueil_jour','Accueil de jour')],required=False,widget=forms.CheckboxSelectMultiple)
    rubriques=forms.MultipleChoiceField(label='Informations collectives demandées',choices=[('logement','Logement'),('revenu','Revenu mensuel du ménage'),('dette','Total de dettes du ménage'),('telephone','Téléphone commun'),('courriel','Courriel commun'),('projet','Projet collectif')],widget=forms.CheckboxSelectMultiple,required=False)
    categories=forms.JSONField(label='Catégories d’âge',help_text='Liste : code, libelle, min et max inclusifs. Catégories sans chevauchement, couvrant 0 à 120 ans. Les personnes d’âge inconnu restent distinctes.')
    attendu=forms.CharField(widget=forms.HiddenInput)
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        categories=self.initial.get('categories',defaut()['categories'])
        del self.fields['categories']
        self.categories_initiales=categories;self.lignes=[]
        for i in range(8):
            cat=categories[i] if i<len(categories) else {}
            noms=[]
            for cle,label in [('libelle','Catégorie'),('min','Âge minimal inclus'),('max','Âge maximal inclus')]:
                nom=f'categorie_{i}_{cle}';noms.append(nom)
                self.fields[nom]=forms.CharField(label=label,max_length=80,required=False) if cle=='libelle' else forms.IntegerField(label=label,min_value=0,max_value=120,required=False)
                self.initial[nom]=cat.get(cle)
            self.lignes.append(noms)
    @property
    def champs_principaux(self):return [x for x in self if not x.name.startswith('categorie_')]
    @property
    def categories_lignes(self):return [[self[n] for n in noms] for noms in self.lignes]
    def clean(self):
        d=super().clean()
        categories=[]
        for i,noms in enumerate(self.lignes):
            valeurs=[d.pop(n,None) for n in noms]
            if not valeurs[0] and valeurs[1:] == [None,None]:continue
            code=self.categories_initiales[i]['code'] if i<len(self.categories_initiales) else f'categorie_{i+1}'
            categories.append(dict(zip(('libelle','min','max'),valeurs),code=code))
        d['categories']=categories
        if all(k in d for k in defaut()):verifier({k:d[k] for k in defaut()})
        return d

@never_cache
@login_required
@require_http_methods(['GET','POST'])
def configurer(request,service_pk):
    s.exiger_gestion(request.user)
    service=get_object_or_404(Service,pk=service_pk)
    f=ProfilForm(request.POST if request.method=='POST' else None,initial={**(service.profil_collectif or defaut()),'actif':bool(service.profil_collectif),'attendu':s.jeton(service)})
    def sauver(attendu,actif,**valeurs):
        s.reserver(service,attendu);avant=deepcopy(service.profil_collectif)
        service.profil_collectif=valeurs if actif else {}
        if actif:verifier(valeurs)
        service.save(update_fields=['profil_collectif'])
        s.journal(request.user,service,'profil_collectif',avant,service.profil_collectif)
    return formulaire(request,f,'Collecte et prestations du service — '+service.libelle,sauver,reverse('acteurs:service',args=[service.pk]))
