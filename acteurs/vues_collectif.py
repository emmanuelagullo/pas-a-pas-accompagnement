from copy import deepcopy
from django import forms
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db.models import Q
from django.urls import reverse
from . import services as s
from .models import Service, OffrePrestataire
from .profils_collectifs import defaut, verifier, MODES, IDENTIFICATIONS
from .views import formulaire
from personnes.champs_saisie import FormulaireMetier

class ProfilForm(FormulaireMetier):
    actif=forms.BooleanField(label='Utiliser les réglages de ce service pour la composition et les prestations',required=False)
    prestations=forms.MultipleChoiceField(label='Prestations proposées',choices=[('hebergement','Hébergement'),('restauration','Repas')],required=False,widget=forms.CheckboxSelectMultiple)
    catalogue=forms.BooleanField(label='Limiter le choix aux offres sélectionnées',required=False,help_text='Cochez cette case pour choisir les offres proposées lors de la saisie.')
    offres=forms.ModelMultipleChoiceField(OffrePrestataire.objects.none(),label='Offres proposées à la saisie',required=False,widget=forms.CheckboxSelectMultiple)
    identification=forms.ChoiceField(label='Personnes à identifier',choices=IDENTIFICATIONS)
    hebergement=forms.ChoiceField(label='Suivi de l’hébergement',choices=MODES)
    restauration=forms.ChoiceField(label='Suivi de la restauration',choices=MODES)
    petits_dejeuners=forms.BooleanField(label='Proposer les petits déjeuners avec l’hébergement',required=False)
    aides=forms.MultipleChoiceField(label='Autres familles de prestations proposées',choices=[('transport','Transport'),('bon_alimentaire','Bons alimentaires'),('produits','Produits alimentaires'),('accueil_jour','Accueil de jour')],required=False,widget=forms.CheckboxSelectMultiple)
    rubriques=forms.MultipleChoiceField(label='Informations demandées au ménage',choices=[('logement','Logement'),('revenu','Revenu mensuel du ménage'),('dette','Total de dettes du ménage'),('telephone','Téléphone commun'),('courriel','Courriel commun'),('projet','Projet collectif')],widget=forms.CheckboxSelectMultiple,required=False)
    categories=forms.JSONField(label='Catégories d’âge',help_text='Liste : code, libelle, min et max inclusifs. Catégories sans chevauchement, couvrant 0 à 120 ans. Les personnes d’âge inconnu restent distinctes.')
    attendu=forms.CharField(widget=forms.HiddenInput)
    def __init__(self,*args,volet=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.volet = volet
        self.fields['offres'].queryset = OffrePrestataire.objects.filter(actif=True)
        if volet == 'composition':
            self.fields['offres'].queryset = OffrePrestataire.objects.filter(
                Q(actif=True) | Q(pk__in=self.initial['offres']))
            for nom in ('actif', 'prestations', 'aides', 'hebergement', 'restauration',
                        'petits_dejeuners', 'catalogue', 'offres'):
                self.fields[nom].disabled = True
        elif volet == 'prestations':
            self.fields['identification'].disabled = True
        # Les anciens choix restent conservés tant que les rubriques sociales
        # ne sont pas configurées dans leur écran dédié.
        self.fields['rubriques'].disabled = True
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
                self.fields[nom].disabled = volet == 'prestations'
            self.lignes.append(noms)
    @property
    def champs_principaux(self):return [x for x in self if not x.name.startswith('categorie_')]
    @property
    def groupes_champs(self):
        groupes=[('Réglages du service',['actif']),
                 ('Composition du ménage',['identification']),
                 ('Prestations proposées',['prestations','aides']),
                 ('Suivi des prestations',['hebergement','restauration','petits_dejeuners']),
                 ('Prestataires',['catalogue','offres'])]
        if self.volet == 'composition':
            groupes = groupes[1:2]
        elif self.volet == 'prestations':
            groupes = groupes[:1] + groupes[2:]
        return [(titre,[self[nom] for nom in noms]) for titre,noms in groupes]
    @property
    def afficher_categories(self):
        return self.volet != 'prestations'

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
        if self.volet != 'composition' and d.get('actif') and d.get('catalogue'):
            familles=set(d.get('prestations',[]))|set(d.get('aides',[]))
            disponibles={o.nature for o in d.get('offres',[])}
            if familles-disponibles:self.add_error('offres','Choisissez une offre pour chaque prestation proposée, ou décochez les prestations non proposées.')
        if all(k in d for k in defaut()):verifier({k:d[k] for k in defaut()})
        return d

@never_cache
@login_required
@require_http_methods(['GET','POST'])
def configurer(request,service_pk,volet=None):
    s.exiger_gestion(request.user)
    service=get_object_or_404(Service,pk=service_pk)
    if volet == 'composition' and not service.profil_collectif:
        raise Http404
    initial = {
        **defaut(), **service.profil_collectif,
        'actif': bool(service.profil_collectif),
        'attendu': s.jeton(service),
        'catalogue': service.catalogue_prestations,
        'offres': list(service.offres.values_list('pk', flat=True)),
    }
    f = ProfilForm(request.POST if request.method == 'POST' else None,
                   volet=volet, initial=initial)

    def sauver(attendu,actif,catalogue,offres,**valeurs):
        s.reserver(service,attendu);avant=deepcopy(service.profil_collectif)
        from .collecte import verifier as verifier_collecte
        from .profils_collectifs import categories_defaut
        verifier_collecte(service.collecte_rubriques,valeurs['categories'] if actif else categories_defaut())
        service.profil_collectif=valeurs if actif else {}
        if actif:verifier(valeurs)
        service.catalogue_prestations=catalogue
        service.save(update_fields=['profil_collectif','catalogue_prestations'])
        if volet != 'composition':
            service.offres.set(offres)
        s.journal(request.user,service,'profil_collectif',avant,{**service.profil_collectif,'catalogue':catalogue,'offres':list(service.offres.values_list('pk',flat=True))})
    titre = {'composition': 'Composition du ménage', 'prestations': 'Prestations du service'}.get(volet, 'Composition et prestations')
    retour = reverse('acteurs:service', args=[service.pk])
    if volet:
        retour += f'#service-{service.pk}-{volet}'
    return formulaire(request, f, titre, sauver, retour, service=service)
