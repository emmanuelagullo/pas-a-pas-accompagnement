"""Préférence de présentation uniquement : les deux exports restent disponibles."""
from django.core.exceptions import ValidationError

CHOIX=[('', 'Automatique selon le rapport'), ('pdf', 'PDF — document à lire ou imprimer'), ('csv', 'CSV — tableau à exploiter')]
DEFAUTS_STATISTIQUES={
    'mouvements':'pdf','ages':'pdf','synthese':'pdf','hebergement':'pdf','repas':'pdf',
    'mensuel':'csv','exploration_repas':'csv','exploration_hebergement':'csv',
}
DEFAUTS_SOURCES={
    'financements':'csv','hebergement':'csv','aides':'csv','parcours':'csv','personnel':'csv',
    'coordonnees':'csv','familles':'csv','identite':'csv','relations':'csv','appels':'csv',
}


def valider(valeur):
    if valeur not in ('', 'pdf', 'csv'):raise ValidationError('Choisissez PDF ou CSV pour l’export mis en avant.')
    return valeur


def prioritaire(source,params):
    valeur=params.get('export_prioritaire','')
    if valeur in ('pdf','csv'):return valeur
    if source=='statistiques':return DEFAUTS_STATISTIQUES.get(params.get('rapport','synthese'),'pdf')
    if source=='exploration':return 'csv' if params.get('affichage')=='detail' else 'pdf'
    return DEFAUTS_SOURCES.get(source,'pdf')
