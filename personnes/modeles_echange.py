"""Échange explicite de paramètres de rapports, sans résultats ni droits importés."""
import json
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from . import models as m,suivi
from .forms_exploration import ExplorationForm

MAX_MODELE=65536


def lire(contenu):
    if len(contenu)>MAX_MODELE:raise ValidationError('Le fichier de modèle dépasse 64 Kio.')
    try:d=json.loads(contenu)
    except (ValueError,UnicodeError):raise ValidationError('Choisissez un fichier JSON de paramètres de rapport.')
    if not isinstance(d,dict) or d.get('schema')!=1 or d.get('application')!='pas-a-pas-accompagnement' or d.get('type')!='modele-exploration':raise ValidationError('Format, application ou version de modèle non pris en charge.')
    p=d.get('parametres')
    if not isinstance(p,dict) or any(not isinstance(k,str) or not isinstance(v,(str,int,bool)) for k,v in p.items()):raise ValidationError('Paramètres de modèle invalides.')
    return d


def valider(acteur,params):
    if params.get('schema')!=1 or params.get('exploration') is not True:raise ValidationError('Version de paramètres non prise en charge.')
    data=params.copy()
    if data.get('periode'):
        from .vues_statistiques import bornes_periode
        try:debut,fin=bornes_periode(data['periode'],timezone.localdate(),decalage_debut=data.get('decalage_debut',-6),decalage_fin=data.get('decalage_fin',1))
        except (ValueError,TypeError,OverflowError):raise ValidationError('Période relative ou bornes non reconnues.')
        data.update(debut=debut.isoformat(),fin=fin.isoformat(),reference=(fin-timedelta(days=1)).isoformat())
    f=ExplorationForm(data,acteur=acteur)
    if not f.is_valid():raise ValidationError('Paramètres non valides : '+' ; '.join(str(c)+': '+', '.join(es) for c,es in f.errors.items()))
    from . import exploration as e
    codes=[f.cleaned_data['mesure'],*[f.cleaned_data.get('mesure'+str(i)) for i in range(2,10) if f.cleaned_data.get('mesure'+str(i))]]
    for code in dict.fromkeys(codes):e.calculer(acteur,{**f.cleaned_data,'mesure':code})
    # Seuls les champs fermés du formulaire sont conservés ; aucun chemin,
    # résultat ou attribut de compte transmis par le fichier n'est importé.
    retour={k:str(v) if v is not None else '' for k,v in f.cleaned_data.items()}
    retour.update(schema=1,exploration=True)
    return retour


def importer(acteur,contenu):
    suivi.exiger(acteur,'view_modelerapport','add_modelerapport')
    d=lire(contenu);nom=d.get('nom','')
    if not isinstance(nom,str) or not nom.strip() or len(nom)>100:raise ValidationError('Le modèle doit porter un nom de 100 caractères au plus.')
    params=valider(acteur,d['parametres'])
    if m.ModeleRapport.objects.filter(auteur=acteur).count()>=30:raise ValidationError('Limite de 30 modèles personnels atteinte.')
    description=d.get('description','');nature=d.get('nature','modele')
    if not isinstance(description,str) or len(description)>6000 or nature not in ('modele','personnalisation'):raise ValidationError('Description ou nature invalide.')
    return m.ModeleRapport.objects.create(auteur=acteur,nom=nom.strip(),parametres=params,description=description,nature=nature)


def exporter(acteur,modele):
    suivi.exiger(acteur,'view_modelerapport','add_modelerapport')
    if modele.auteur_id!=acteur.pk:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    params=valider(acteur,modele.parametres)
    return json.dumps(dict(schema=1,application='pas-a-pas-accompagnement',type='modele-exploration',nom=modele.nom,parametres=params,description=modele.description,nature=modele.nature),ensure_ascii=False,indent=2).encode()
