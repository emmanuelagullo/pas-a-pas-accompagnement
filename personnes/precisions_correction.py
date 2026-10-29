"""Précision facultative d'une rectification, distincte de la décision métier."""
from django.core.exceptions import ValidationError

LIBELLE = 'Précision sur la correction (facultative)'


def valider(motif):
    if not isinstance(motif, str) or len(motif) > 240:
        raise ValidationError({'motif': 'La précision est limitée à 240 caractères.'})
    return motif.strip()


def preparer(form):
    champ = form.fields.get('motif')
    if champ is not None:
        champ.required = False
        champ.label = LIBELLE
    return form


def operation(form, nom='action', facultatives=('correction',)):
    """Un formulaire mixte conserve les exigences de chaque opération au serveur."""
    choix=form.fields[nom]
    valeur=form.data.get(nom) if form.is_bound else form.initial.get(nom, choix.initial)
    if not valeur:
        valeur=next(iter(choix.choices))[0]
    form.precision_conditionnelle=True
    choix.widget.attrs['data-precision-operation']=','.join(facultatives)
    champ=form.fields['motif']
    champ.required=valeur not in facultatives
    champ.label=(LIBELLE if valeur=='correction' else 'Précision sur l’opération (facultative)') if not champ.required else 'Justification de l’opération'
    champ.help_text='Facultative pour une correction ; requise pour les autres opérations proposées ici.'
    return form
