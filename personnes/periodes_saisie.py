"""Aide de saisie civile ; seule la période validée est transmise au métier."""
from datetime import timedelta
from django import forms


def preparer(form):
    noms=getattr(form,'saisie_periode',None)
    if not noms or any(n not in form.fields for n in noms):return
    debut,fin=noms
    form.fields[debut].widget.attrs['data-periode-debut']='1'
    form.fields[fin].widget.attrs['data-periode-fin']='1'
    form._fin_periode_obligatoire=form.fields[fin].required
    # Sans JavaScript, l'utilisateur choisit explicitement le calcul souhaité.
    if form.is_bound and form.data.get(form.add_prefix('calcul_periode'))=='duree':
        form.fields[fin].required=False
    form.fields['duree']=forms.IntegerField(label='Durée civile (jours / nuits d’hébergement)',required=False,
        min_value=1,max_value=3652058,widget=forms.NumberInput(attrs={'data-periode-duree':'1','inputmode':'numeric'}),
        help_text='Début inclus, fin exclue. Ce nombre ne compte ni les personnes ni les repas réalisés. Vide : durée non définie.')
    form.fields['calcul_periode']=forms.ChoiceField(label='Calculer avec',required=False,
        choices=[('dates','Les dates'),('duree','Le début et la durée')],initial='dates',
        widget=forms.RadioSelect(attrs={'data-periode-calcul':'1'}),
        help_text='Les champs se synchronisent pendant la saisie. Sans JavaScript, choisissez le calcul puis enregistrez.')
    if not form.is_bound:
        try:
            d=form.fields[debut].clean(form.initial.get(debut,form.fields[debut].initial))
            f=form.fields[fin].clean(form.initial.get(fin,form.fields[fin].initial))
            if d and f and f>d:form.initial['duree']=(f-d).days
        except forms.ValidationError:pass
    ordre=list(form.fields);ordre.remove('duree');ordre.remove('calcul_periode')
    i=ordre.index(fin)+1;ordre[i:i]=['duree','calcul_periode'];form.order_fields(ordre)


def nettoyer(form,donnees):
    if not getattr(form,'saisie_periode',None) or 'calcul_periode' not in form.fields:return donnees
    debut,fin=form.saisie_periode
    mode=donnees.pop('calcul_periode','dates') or 'dates'
    duree=donnees.pop('duree',None)
    if mode=='duree' and debut in donnees:
        if duree is not None:
            try:donnees[fin]=donnees[debut]+timedelta(days=duree)
            except (OverflowError,TypeError):form.add_error('duree','La date de fin dépasserait les dates possibles.')
        elif form._fin_periode_obligatoire:form.add_error('duree','Précisez une durée ou choisissez les dates.')
        else:donnees[fin]=None
    return donnees
