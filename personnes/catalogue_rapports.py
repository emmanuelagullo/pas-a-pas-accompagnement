"""Catalogue fermé des rapports proposés, de leurs accès et de leurs éditeurs."""
from django.urls import reverse

SOURCES={
 'statistiques':('Statistiques d’activité','statistiques'),
 'financements':('Coûts et financements','dossiers:rapport_financements'),
 'hebergement':('Hébergement — périodes individuelles','dossiers:rapport_hebergement_individuel'),
 'aides':('Prestations : autorisations et réalisations','dossiers:rapport_aides'),
 'parcours':('Demandes, orientations et projet','dossiers:rapport_parcours'),
 'personnel':('Déclarations économiques et administratives','dossiers:rapport_a'),
 'coordonnees':('Coordonnées personnelles','dossiers:rapport_coordonnees'),
 'familles':('Déclarations familiales','dossiers:rapport_familles'),
 'identite':('Compléments d’identité','dossiers:rapport_complements_identite'),
 'relations':('Liens personnels déclarés','dossiers:rapport_relations'),
 'appels':('Appels 115','dossiers:appels115'),
}
CLE_SOURCE='_rapport_source'


def accessible(acteur,source,rapport=None):
    if source=='statistiques':
        droits=['view_accompagnement','view_sejour','view_repasdistribue']
        if rapport=='ages':droits+=['view_personne']
        if rapport=='exploration_hebergement':droits+=['view_affectation','view_lieuhebergement']
    elif source=='financements':
        from .financements import LECTURE
        droits=LECTURE
    elif source=='coordonnees':
        from .coordonnees import DROITS_LECTURE
        return acteur.has_perms(DROITS_LECTURE)
    elif source=='familles':
        from .famille import DROITS_LECTURE
        return acteur.has_perms(DROITS_LECTURE)
    elif source=='identite':
        from .complements_identite import DROITS_LECTURE
        return acteur.has_perms(DROITS_LECTURE)
    elif source=='relations':
        from .relations_personnelles import DROITS_LECTURE
        return acteur.has_perms(DROITS_LECTURE)
    elif source=='personnel':
        from . import dossier_complet as s
        return acteur.has_perm('personnes.view_personne') and (acteur.has_perms(s.ADMIN_LECTURE) or any(acteur.has_perms(s.droits_lecture(c)) for c in s.RUBRIQUES))
    elif source=='parcours':
        from . import parcours as s
        return acteur.has_perm('personnes.view_personne') and (any(acteur.has_perms(s.droits(c)) for c in s.RUBRIQUES) or acteur.has_perms(['personnes.view_menage','personnes.view_accompagnement','personnes.view_informationsaccompagnement']))
    elif source=='appels':
        from .appels115 import LECTURE
        droits=LECTURE
    elif source=='aides':
        from .aides import LECTURE
        droits=LECTURE
    elif source=='hebergement':
        droits=['view_personne','view_menage','view_accompagnement','view_accordhebergement','view_sejour','view_continuitesejour','view_absence','view_affectation','view_lieuhebergement']
    else:return False
    return acteur.has_perms(['personnes.'+d if '.' not in d else d for d in droits])


def catalogue(acteur):
    from .vues_statistiques import RAPPORTS
    from urllib.parse import urlencode
    resultat=[]
    for code,titre in RAPPORTS.items():
        if accessible(acteur,'statistiques',code):resultat.append(dict(cle='statistiques:'+code,titre=titre,url=reverse('statistiques')+'?'+urlencode({'rapport':code}),source='statistiques',rapport=code))
    for source,(titre,route) in SOURCES.items():
        if source!='statistiques' and accessible(acteur,source):resultat.append(dict(cle=source,titre=titre,url=reverse(route),source=source))
    return resultat


def ouvrir(modele):
    from urllib.parse import urlencode
    source=modele.parametres.get(CLE_SOURCE)
    if source in SOURCES:return reverse('dossiers:rapport_composer',args=[source])+'?'+urlencode({'modele':modele.pk})
    return reverse('dossiers:explorer' if modele.parametres.get('exploration') else 'statistiques')+'?'+urlencode({'modele':modele.pk})
