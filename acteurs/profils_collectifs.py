"""Profils fermés, adaptés par service, sans attribution de droits."""
from django.core.exceptions import ValidationError

MODES = [('collectif','Collectif uniquement'), ('option','Collectif avec détail facultatif'), ('individuel','Suivi individuel')]
IDENTIFICATIONS = [('reference','Personne de référence et composition'), ('adultes','Adultes identifiés'), ('tous','Tous les bénéficiaires identifiés')]

FAMILLES = [('hebergement', 'Hébergement'), ('restauration', 'Repas'),
            ('transport', 'Transport'), ('bon_alimentaire', 'Bons alimentaires'),
            ('produits', 'Produits alimentaires'), ('accueil_jour', 'Accueil de jour')]


def parcours_simple(prise, famille):
    from personnes.collectifs import service_objet
    try:
        service = service_objet(prise)
    except ValidationError:
        return False
    profil = service.profil_collectif
    return famille in profil.get('parcours_simples', ()) or (
        famille == 'hebergement' and profil.get('fin_hebergement_unique', False)
    )


def fin_hebergement_unique(prise):
    from personnes.collectifs import service_objet

    try:
        return service_objet(prise).profil_collectif.get('fin_hebergement_unique', False)
    except ValidationError:
        return False


def categories_defaut():
    return [{'code':'adulte','libelle':'Adulte','min':18,'max':120},
            {'code':'enfant','libelle':'Enfant','min':3,'max':17},
            {'code':'bas_age','libelle':'Bas âge','min':0,'max':2}]

def verifier_categories(valeur):
    import re
    if not isinstance(valeur,list) or not 1 <= len(valeur) <= 8:
        raise ValidationError('Définissez entre une et huit catégories.')
    codes=set();ages=set()
    for c in valeur:
        if not isinstance(c,dict) or set(c)!={'code','libelle','min','max'}:
            raise ValidationError('Chaque catégorie contient code, libelle, min et max.')
        if not isinstance(c['code'],str) or not re.fullmatch('[a-z][a-z0-9_]{0,39}',c['code']) or c['code'] in codes:
            raise ValidationError('Codes de catégorie distincts attendus.')
        if not isinstance(c['libelle'],str) or not c['libelle'].strip() or len(c['libelle'])>80:
            raise ValidationError('Libellé de catégorie attendu (80 caractères maximum).')
        if type(c['min']) is not int or type(c['max']) is not int or not 0<=c['min']<=c['max']<=120:
            raise ValidationError('Bornes d’âge inclusives entre 0 et 120 attendues.')
        intervalle=set(range(c['min'],c['max']+1))
        if ages & intervalle:raise ValidationError('Les catégories d’âge ne doivent pas se recouvrir.')
        ages |= intervalle;codes.add(c['code'])
    if ages!=set(range(121)):raise ValidationError('Les catégories doivent couvrir les âges de 0 à 120 ans.')

def defaut():
    return {'identification':'reference','hebergement':'collectif','restauration':'collectif',
            'petits_dejeuners':False,'categories':categories_defaut(),
            'prestations':['hebergement','restauration'],'rubriques':['logement','revenu','dette','telephone','courriel','projet'],'aides':[]}

def defaut_individuel(*, collecte_configuree=False):
    return {
        **defaut(),
        'identification': 'tous',
        'hebergement': 'individuel',
        'restauration': 'individuel',
        'rubriques': [],
        'aides': [] if collecte_configuree else ['transport', 'bon_alimentaire', 'produits', 'accueil_jour'],
    }


def verifier(valeur):
    if not isinstance(valeur,dict) or set(valeur)-set(defaut())-{'parcours_simples','fin_hebergement_unique','fiche_ahi'} or set(defaut())-set(valeur)-{'aides','prestations'}:raise ValidationError('Profil collectif incomplet ou champ inconnu.')
    if type(valeur.get('fin_hebergement_unique', False)) is not bool:
        raise ValidationError('Réglage de fin d’hébergement invalide.')
    if type(valeur.get('fiche_ahi', False)) is not bool:
        raise ValidationError('Le réglage de la fiche AHI doit être activé ou désactivé.')
    simples = valeur.get('parcours_simples', [])
    if not isinstance(simples, list) or any(not isinstance(x, str) or x not in dict(FAMILLES) for x in simples):
        raise ValidationError('Famille de parcours simple inconnue.')
    familles=valeur.get('prestations',['hebergement','restauration'])
    if not isinstance(familles,list) or set(familles)-{'hebergement','restauration'}:raise ValidationError('Famille de prestation inconnue.')
    aides=valeur.get('aides',[])
    if not isinstance(aides,list) or any(x not in ('transport','bon_alimentaire','produits','accueil_jour') for x in aides):raise ValidationError('Famille d’aide inconnue.')
    if valeur['identification'] not in dict(IDENTIFICATIONS):raise ValidationError('Identification inconnue.')
    if any(valeur[k] not in dict(MODES) for k in ('hebergement','restauration')):raise ValidationError('Mode de suivi inconnu.')
    if type(valeur['petits_dejeuners']) is not bool:raise ValidationError('Option petits déjeuners invalide.')
    if not isinstance(valeur['rubriques'],list) or len(set(valeur['rubriques']))!=len(valeur['rubriques']) or set(valeur['rubriques'])-set(defaut()['rubriques']):raise ValidationError('Rubriques collectives inconnues ou répétées.')
    verifier_categories(valeur['categories'])
