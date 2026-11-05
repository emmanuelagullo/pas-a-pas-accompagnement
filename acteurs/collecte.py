"""Choix de collecte du service ; ils ne donnent aucun droit de lecture."""
from django.core.exceptions import ValidationError

# Une portée ménage n'est proposée que pour un schéma déjà distinct et stocké.
RUBRIQUES={
 'identite':('Identité',()),'complements':('Identité déclarée',()),
 'famille':('Situation familiale',()),'coordonnees':('Coordonnées',('telephone','courriel')),
 'logement':('Logement',('logement',)),'emploi':('Emploi et formation',()),
 'ressources':('Ressources',('revenu',)),'dettes':('Dettes',('dette',)),
 'administration':('Administration et droits',()),'pieces':('Pièces présentées',()),
 'couvertures':('Couvertures sociales',()),'protections':('Protection juridique',()),
 'besoins':('Besoins pratiques et adaptations',()),'antecedents':('Antécédents institutionnels',()),
 'territoires':('Ancrage territorial',()),'evolutions':('Évolutions déclarées',()),
 'relations':('Liens personnels',()),'projet':('Projet du ménage',('projet',))}
PORTEES=[('personne','Pour chaque personne concernée'),('menage','Pour le ménage'),('deux','Pour le ménage et chaque personne concernée, séparément'),('non','Non demandée')]
POPULATIONS=[('tous','Toutes les personnes identifiées'),('reference','Personne de référence du ménage'),('adultes','Adultes (18 ans et plus)')]

def verifier(valeur,categories=()):
    if valeur=={}:return
    if not isinstance(valeur,dict) or set(valeur)!=set(RUBRIQUES):raise ValidationError('Définissez une règle par rubrique connue.')
    populations={x[0] for x in POPULATIONS}|{'categorie:'+x['code'] for x in categories}
    for code,r in valeur.items():
        if not isinstance(r,dict) or set(r)-{'portee_preferee'}!={'portee','population'} or r['portee'] not in dict(PORTEES) or r['population'] not in populations:
            raise ValidationError('Règle de collecte inconnue.')
        portee = r.get('portee_preferee', r['portee'])
        if 'portee_preferee' in r and (r['portee'] != 'non' or portee not in ('personne','menage','deux')):
            raise ValidationError('Rattachement préféré inconnu.')
        if portee in ('menage','deux') and not RUBRIQUES[code][1]:raise ValidationError('Cette rubrique ne peut pas être attribuée au ménage.')
        if code=='projet' and portee not in ('menage','non'):raise ValidationError('Le projet du ménage reste distinct des objectifs et projets personnels de parcours.')
        if code=='identite' and (r['portee']!='personne' or r['population']!='tous'):raise ValidationError('L’identité des personnes identifiées reste personnelle.')

def profil(nom):
    regles={k:{'portee':'menage' if k=='projet' else 'personne','population':'tous'} for k in RUBRIQUES}
    if nom=='menage':
        for k,(_,champs) in RUBRIQUES.items():
            regles[k]={'portee':'menage' if champs else 'personne','population':'reference'}
    elif nom=='adultes':
        for k in regles:
            if k not in ('identite','projet'):regles[k]['population']='adultes'
    elif nom!='detail':raise ValidationError('Profil de collecte inconnu.')
    regles['identite']={'portee':'personne','population':'tous'}
    return regles

def champs_menage(regles):
    return [c for code,(_,champs) in RUBRIQUES.items() if regles[code]['portee'] in ('menage','deux') for c in champs]
