from django import forms
from django.contrib.auth import get_user_model
from personnes.champs_saisie import FormulaireMetier, FormulaireModeleMetier
from personnes.models import Intervenant, Partenaire
from .models import Service, Etablissement, Habilitation


class ServiceForm(FormulaireModeleMetier):
    class Meta:
        model=Service
        fields=['etablissement','libelle','politique']


class AppartenanceForm(FormulaireMetier):
    professionnel=forms.ModelChoiceField(Intervenant.objects.all(),label='Professionnel existant')
    compte=forms.ModelChoiceField(get_user_model().objects.filter(is_active=True),required=False,label='Compte existant à relier (facultatif)',help_text='Aucun compte n’est créé ; ce lien n’accorde aucun accès.')
    fonction=forms.CharField(max_length=160,required=False)
    debut=forms.DateField(label='Début inclus',widget=forms.DateInput(attrs={'type':'date'}))
    fin=forms.DateField(label='Fin exclue',required=False,widget=forms.DateInput(attrs={'type':'date'}))


class HabilitationForm(FormulaireMetier):
    compte=forms.ModelChoiceField(get_user_model().objects.filter(is_active=True),label='Compte existant')
    tache=forms.ChoiceField(choices=Habilitation.TACHES,label='Tâches autorisées')
    debut=forms.DateField(label='Début inclus',widget=forms.DateInput(attrs={'type':'date'}))
    fin=forms.DateField(label='Fin exclue',required=False,widget=forms.DateInput(attrs={'type':'date'}))
    statistiques_service=forms.BooleanField(required=False,label='Statistiques regroupées de ce service')
    statistiques_etablissement=forms.BooleanField(required=False,label='Statistiques regroupées de cet établissement')
    exporter=forms.BooleanField(required=False,label='Documents individuels et exports autorisés')
    corriger_autrui=forms.BooleanField(required=False,label='Rectifier les contributions et reprendre le suivi d’un collègue')


class RelaisForm(FormulaireMetier):
    message=forms.CharField(label='Message accompagnant le relais — facultatif',required=False,max_length=1000,widget=forms.Textarea(attrs={'rows':3}),help_text='Partagé dans le cahier de chaque élément transféré et la notification du destinataire, selon leurs droits. Ce n’est pas un message privé.')
    entrant=forms.ModelChoiceField(Intervenant.objects.none(),label='À qui ?')
    sortant=forms.ModelChoiceField(Intervenant.objects.none(),label='Relayer qui ?')
    date=forms.DateField(label='À partir de quand ?',widget=forms.DateInput(attrs={'type':'date'}))
    descendants=forms.BooleanField(required=False,initial=True,label='Inclure les éléments en cours dont cette personne s’occupe')
    attendu=forms.CharField(widget=forms.HiddenInput)
    proposition=forms.CharField(widget=forms.HiddenInput,required=False)
