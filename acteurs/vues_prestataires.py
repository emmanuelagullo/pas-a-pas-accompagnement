"""Catalogue organisationnel ; aucune donnée de dossier ni droit implicite."""
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404,render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from personnes import models as m, financements, bd6
from personnes.champs_saisie import FormulaireMetier
from . import services as s
from .models import OffrePrestataire,TarifOffre,JournalOffre
from .profils_collectifs import categories_defaut
from .views import formulaire

class OffreForm(FormulaireMetier):
    libelle=forms.CharField(label='Nom de l’offre',max_length=160)
    lieu=forms.ModelChoiceField(m.Partenaire.objects.none(),label='Lieu prestataire',required=False)
    nouveau_lieu=forms.CharField(label='Ou créer un lieu',max_length=160,required=False)
    nature=forms.ChoiceField(label='Prestation',choices=OffrePrestataire._meta.get_field('nature').choices)
    dejeuner=forms.BooleanField(label='Déjeuner proposé',initial=True,required=False)
    diner=forms.BooleanField(label='Dîner proposé',initial=True,required=False)
    actif=forms.BooleanField(label='Proposer cette offre',initial=True,required=False)
    attendu=forms.CharField(widget=forms.HiddenInput,required=False)
    def __init__(self,*args,**kw):
        super().__init__(*args,**kw)
        # Répertoire organisationnel après gerer_organisation, comme les membres.
        self.fields['lieu'].queryset=m.Partenaire._base_manager.all()
    def clean(self):
        d=super().clean()
        if bool(d.get('lieu'))==bool(d.get('nouveau_lieu')):self.add_error('lieu','Choisissez un lieu existant ou créez-en un.')
        if d.get('nature')=='restauration' and not (d.get('dejeuner') or d.get('diner')):self.add_error('dejeuner','Choisissez au moins un repas.')
        return d

class PrixForm(FormulaireMetier):
    categorie=forms.ChoiceField(label='Catégorie')
    debut=forms.DateField(label='Prix applicable à partir du',initial=timezone.localdate,widget=forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'))
    prix=forms.DecimalField(label='Prix commun par repas',min_value=0,max_digits=14,decimal_places=4)
    prix_diner=forms.DecimalField(label='Prix du dîner différent — facultatif',min_value=0,max_digits=14,decimal_places=4,required=False)
    devise=forms.RegexField('[A-Z]{3}',label='Devise',initial='EUR',max_length=3)
    attendu=forms.CharField(widget=forms.HiddenInput)
    def __init__(self,*args,offre,**kw):
        super().__init__(*args,**kw)
        categories={c['code']:c['libelle'] for c in categories_defaut()}
        for service in offre.services.all():
            for c in service.profil_collectif.get('categories',[]):categories[c['code']]=c['libelle']
        categories['inconnu']='Âge non précisé'
        self.fields['categorie'].choices=list(categories.items())
        self.initial['attendu']=s.jeton(offre)

@never_cache
@login_required
@require_http_methods(['GET','POST'])
def catalogue(request,pk=None,action=None):
    s.exiger_gestion(request.user)
    offre=get_object_or_404(OffrePrestataire,pk=pk) if pk else None
    retour=reverse('acteurs:prestataires')
    if action=='prix':
        if offre.nature!='restauration':raise ValidationError('Cette grille concerne les repas.')
        f=PrixForm(request.POST if request.method=='POST' else None,offre=offre)
        def sauver(attendu,categorie,debut,prix,prix_diner,devise):
            s.reserver(offre,attendu)
            label=dict(f.fields['categorie'].choices)[categorie]
            for repas,montant in [('commun',prix),('diner',prix_diner)]:
                lien=offre.tarifs.filter(categorie=categorie,repas=repas).first()
                if montant is None and lien is None:continue
                tarif=lien.tarif if lien else None
                action='correction' if tarif and tarif.versions.filter(debut=debut).exists() else 'changement' if tarif else 'definition'
                version=financements.definir_tarif(request.user,bd6.jeton(tarif) if tarif else financements.creation_tarif(),'Paramétrage du lieu d’alimentation',action=action,tarif=tarif,
                    debut=debut,fin=None,libelle=offre.libelle+' — '+label+' — '+repas,unite='repas',categorie=label,montant=montant or 0,devise=devise,prestataire=offre.lieu,actif=montant is not None,source='Catalogue des prestataires')
                if not lien:TarifOffre.objects.create(offre=offre,categorie=categorie,libelle=label,repas=repas,tarif=version)
            JournalOffre.objects.create(offre=offre,auteur=request.user,apres={'categorie':categorie,'debut':str(debut),'prix':str(prix),'prix_diner':str(prix_diner),'devise':devise})
        return formulaire(request,f,'Tarifs — '+offre.libelle,sauver,reverse('acteurs:prestataire',args=[offre.pk]))
    if action=='modifier' or action=='nouveau':
        f=OffreForm(request.POST if request.method=='POST' else None,initial={k:getattr(offre,k) for k in ('libelle','lieu','nature','dejeuner','diner','actif')}|{'attendu':s.jeton(offre)} if offre else {})
        def sauver(attendu,nouveau_lieu,**d):
            nonlocal offre
            avant={k:str(getattr(offre,k)) for k in d} if offre else {}
            if offre:s.reserver(offre,attendu)
            if nouveau_lieu:
                if not request.user.has_perm('personnes.add_partenaire'):
                    from django.core.exceptions import PermissionDenied
                    raise PermissionDenied
                d['lieu']=m.Partenaire.objects.create(libelle=nouveau_lieu,cree_par=request.user)
            if offre:
                for k,v in d.items():setattr(offre,k,v)
            else:offre=OffrePrestataire(**d)
            offre.full_clean();offre.save()
            JournalOffre.objects.create(offre=offre,auteur=request.user,avant=avant,apres={k:str(v) for k,v in d.items()})
        return formulaire(request,f,'Modifier l’offre' if offre else 'Nouvelle offre de prestation',sauver,lambda:reverse('acteurs:prestataire',args=[offre.pk]) if offre else reverse('acteurs:prestataires'))
    return render(request,'acteurs/prestataires.html',{'offre':offre,'offres':OffrePrestataire.objects.select_related('lieu'),'tarifs':offre.tarifs.select_related('tarif') if offre else []})
