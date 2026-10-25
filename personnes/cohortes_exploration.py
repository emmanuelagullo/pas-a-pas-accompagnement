"""Un seul objet retenu par personne connue, après tous les filtres du rapport."""
from collections import defaultdict
from django.core.exceptions import ValidationError


POPULATIONS={'prises','demandes','sejours','accords_hebergement','accords_repas','repas','aides'}
MESURES={'personnes','adultes_connus','enfants_connus','ages_inconnus'}


def verifier(d):
    mode=d.get('cohorte') or 'tous'
    if mode not in ('tous','premier','dernier'):raise ValidationError('Sélection chronologique inconnue.')
    if mode!='tous' and (d['population'] not in POPULATIONS or d['mesure'] not in MESURES):
        raise ValidationError('Le premier ou dernier objet par personne concerne les prises en charge, demandes et prestations, avec une mesure de personnes distinctes ou de leur âge. Aucune quantité collective n’est répartie artificiellement.')
    return mode


def retenir(lignes,mode):
    if mode=='tous':return lignes
    choix={}
    def ordre(x):return x['date'],x.get('_ordre_saisie',''),x['id']
    for x in lignes:
        for p in x['personnes']:
            if p not in choix or (ordre(x)<ordre(choix[p]) if mode=='premier' else ordre(x)>ordre(choix[p])):choix[p]=x
    retenus=defaultdict(set)
    for p,x in choix.items():retenus[x['id']].add(p)
    return [{**x,'personnes':retenus[x['id']]} for x in lignes if x['id'] in retenus]
