"""NAV10 : présence d'informations dans les seules rubriques déjà autorisées.

Aucun score de complétude, aucune lecture supplémentaire des modèles.
"""
from . import models as m


def etat_rubrique(groupe):
    connu = inconnu = False
    for fiche in groupe['fiches']:
        fait = fiche['fait']
        etat = getattr(fait, 'etat', None)
        if etat == 'inconnu':
            inconnu = True
            continue
        if etat == 'aucun':
            connu = True
            continue
        if isinstance(fait, m.SituationPersonnelle) and fait.valeur == 'inconnu':
            # Cette ancienne valeur signifie « Non renseigné », pas une
            # déclaration explicite « Non connu » des collections modernes.
            continue
        for champ in fiche['resume']:
            if champ['nom'] == 'etat': continue
            valeur = getattr(fait, champ['nom'])
            field = fait._meta.get_field(champ['nom'])
            if field.choices and valeur in ('inconnu', 'inconnue', 'non_renseigne'):
                continue
            connu = True
            break
    # Une rubrique mixte compte une fois, parmi celles qui ont des informations.
    return 'informations' if connu else 'non_connu' if inconnu else 'vide'


def compter(groupes):
    etats = [etat_rubrique(g) for g in groupes if not g.get('hors_collecte')]
    return {'total': len(etats), 'informations': etats.count('informations'),
            'non_connu': etats.count('non_connu')}


def bilan(personnes, projets):
    total = {'personnes': len(personnes), 'total': 0, 'informations': 0, 'non_connu': 0,
             'projet_total': len(projets), 'projet_informations': sum(bool(g['items']) for g in projets)}
    for personne in personnes:
        repere = compter(personne['groupes'])
        personne['reperes'] = repere
        for cle in ('total', 'informations', 'non_connu'): total[cle] += repere[cle]
    return total
