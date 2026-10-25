"""Suggestion explicite de bénéficiaires, jamais une admission ou distribution."""
from django import forms
from django.core.exceptions import ValidationError
from . import repas, famille, suivi

CHAMPS=('regle_petit_dejeuner','date_reference_petit_dejeuner','age_min_petit_dejeuner','age_max_petit_dejeuner')


def proposer(acteur,prise,reference,regle,age_min=2,age_max=12):
    repas.droit(acteur,'add_accordrepas')
    if regle not in ('tous','age','age_grossesse'):raise ValidationError('Choisissez une règle de proposition.')
    if type(age_min) is not int or type(age_max) is not int or not 0<=age_min<=age_max<=120:raise ValidationError('Les seuils doivent vérifier 0 ≤ borne basse exclue ≤ borne haute incluse ≤ 120.')
    personnes=list(prise.beneficiaires.order_by('designation','pk'))
    if regle=='tous':return personnes,[]
    grossesses={}
    if regle=='age_grossesse':
        suivi.exiger(acteur,'view_declarationfamiliale','view_revisiondeclarationfamiliale')
        grossesses={f.personne_id:f.grossesse for f in famille.a_date(personnes,reference)}
    selection=[];a_verifier=[]
    for p in personnes:
        categorie=repas.proposer_categorie(p,reference,age_jeune=age_max,age_bas_age=age_min)
        if categorie=='jeune' or regle=='age_grossesse' and grossesses.get(p.pk) is True:selection.append(p)
        if categorie is None or regle=='age_grossesse' and grossesses.get(p.pk) is None:a_verifier.append(p)
    return selection,a_verifier


def sans_preparation(d):return {k:v for k,v in d.items() if k not in CHAMPS}


def preparer_formulaire(form,request,prise):
    regles=[('','Aucune proposition automatique'),('tous','Tous les bénéficiaires explicites'),('age','Âge entre les deux seuils')]
    if request.user.has_perms(famille.DROITS_LECTURE):regles.append(('age_grossesse','Âge entre les seuils ou grossesse déclarée à la date choisie'))
    form.fields.update({
        CHAMPS[0]:forms.ChoiceField(label='Règle à appliquer volontairement',choices=regles,required=False),
        CHAMPS[1]:forms.DateField(label='Date de référence des déclarations et âges',required=False,help_text='À choisir explicitement ; à défaut, le début demandé. Ce calcul ne prouve pas une présence ni une situation future.'),
        CHAMPS[2]:forms.IntegerField(label='Borne basse d’âge exclue',min_value=0,max_value=120,initial=2,required=False),
        CHAMPS[3]:forms.IntegerField(label='Borne haute d’âge incluse',min_value=0,max_value=120,initial=12,required=False),
    })
    form.aide_petit_dejeuner=True
    form.champs_repas=[form[k] for k in form.fields if k not in CHAMPS]
    form.champs_preparation=[form[k] for k in CHAMPS]
    form.preparation_seule=request.method=='POST' and request.POST.get('action')=='proposer_petit_dejeuner'
    if form.preparation_seule:
        try:
            regle=form.fields[CHAMPS[0]].clean(request.POST.get(CHAMPS[0],''))
            reference=form.fields[CHAMPS[1]].clean(request.POST.get(CHAMPS[1])) or form.fields['debut'].clean(request.POST.get('debut'))
            bas=form.fields[CHAMPS[2]].clean(request.POST.get(CHAMPS[2]));haut=form.fields[CHAMPS[3]].clean(request.POST.get(CHAMPS[3]))
            ps,inconnus=proposer(request.user,prise,reference,regle,2 if bas is None else bas,12 if haut is None else haut)
        except ValidationError as erreur:form.add_error(None,erreur)
        else:
            data=form.data.copy();data.setlist('beneficiaires',[str(p.pk) for p in ps])
            data.setlist('services',['petit_dejeuner']);data['service']='petit_dejeuner';data[CHAMPS[1]]=reference.isoformat()
            form.data=data
            form.message_preparation=f'Proposition pour le petit-déjeuner uniquement au {reference:%d/%m/%Y} : {len(ps)} bénéficiaire(s) sélectionné(s). Vérifiez et ajustez les cases avant d’accorder les repas. Aucun accord ni repas distribué n’a été enregistré.'
            if inconnus:form.message_inconnus='Informations d’âge ou de grossesse à vérifier : '+', '.join(str(p) for p in inconnus)+'. Une valeur inconnue n’est pas une réponse négative.'
    return form
