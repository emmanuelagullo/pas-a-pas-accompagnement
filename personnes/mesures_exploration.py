"""Mesures explicites : personnes uniques, déclarations et nuitées ventilées.

Les catégories d'âge des nuitées sont évaluées à chaque nuit civile, jamais
à partir de l'âge à la fin du rapport ou d'un effectif familial recopié.
"""
from datetime import date
from django.core.exceptions import ValidationError
from . import models as m, suivi

PERSONNES = {
    'adultes_connus': 'Personnes majeures distinctes à la référence',
    'enfants_connus': 'Personnes mineures distinctes à la référence',
    'ages_inconnus': 'Personnes distinctes sans âge exact à la référence',
}
FAMILLE = {
    'enfants_charge_declares': ('enfants_a_charge', 'Enfants à charge déclarés, par déclarant distinct'),
    'enfants_non_charge_declares': ('enfants_non_a_charge', 'Enfants non à charge déclarés, par déclarant distinct'),
    'enfants_famille_declares': (None, 'Enfants à charge ou non déclarés, par déclarant distinct'),
    'grossesses_famille_declarees': ('grossesse', 'Grossesses déclarées, par déclarant distinct'),
}
NUITEES = {
    'nuitees_adultes': 'Nuitées de personnes majeures — âge à chaque nuit',
    'nuitees_enfants': 'Nuitées de personnes mineures — âge à chaque nuit',
    'nuitees_age_inconnu': 'Nuitées sans âge exact connu',
}
CHOIX = [*PERSONNES.items(), *((k, v[1]) for k, v in FAMILLE.items()), *NUITEES.items()]


def anniversaire_majorite(naissance):
    try:
        return naissance.replace(year=naissance.year + 18)
    except ValueError:
        # Une naissance du 29 février atteint cet âge civil le 1er mars
        # lorsque l'année d'anniversaire ne possède pas ce jour.
        if naissance.year + 18 > 9999:
            return date.max
        return date(naissance.year + 18, 3, 1)


def ventiler_nuitees(personne, debut, fin):
    """Retourne adultes, enfants, inconnus ; leur somme vaut fin-début."""
    jours = max(0, (fin - debut).days)
    naissance = personne.date_naissance
    if personne.precision_naissance != 'exacte' or not naissance:
        return (0, 0, jours)
    inconnus = max(0, (min(fin, naissance) - debut).days)
    majorite = anniversaire_majorite(naissance)
    adultes = max(0, (fin - max(debut, majorite)).days)
    return (adultes, jours - inconnus - adultes, inconnus)


def preparer(acteur, lignes, d):
    mesure = d['mesure']
    if mesure not in PERSONNES and mesure not in FAMILLE and mesure not in NUITEES:
        return []
    if mesure in FAMILLE:
        suivi.exiger(acteur, 'view_declarationfamiliale', 'view_revisiondeclarationfamiliale')
        return ['famille.enfants_a_charge', 'famille.enfants_non_a_charge', 'famille.grossesse']
    if mesure in NUITEES:
        if d['population'] not in ('sejours','affectations'):
            raise ValidationError('Les nuitées par âge concernent les épisodes de séjour ou leurs périodes de lieu.')
        ids = {p for x in lignes for p in x['personnes']}
        personnes = {p.pk: p for p in m.Personne.objects.filter(pk__in=ids)}
        indice = list(NUITEES).index(mesure)
        for x in lignes:
            compteurs = {p: 0 for p in x['personnes']}
            for debut, fin, beneficiaires in x['_fragments']:
                for pk in beneficiaires:
                    compteurs[pk] += ventiler_nuitees(personnes[pk], debut, fin)[indice]
            x['_quantites_personnelles'] = compteurs
        return []
    return ['age']


def mesurer(xs, code):
    """Les sommes déclarées ignorent les inconnus et restent None si aucun connu."""
    if code in NUITEES:
        return sum((x['_quantites_personnelles'][p] for x in xs for p in x['personnes']), 0)
    if code in PERSONNES:
        resultat = set()
        for x in xs:
            for pk in x['personnes']:
                ages = x['_par_personne'][pk].get('age', [])
                if (code == 'ages_inconnus' and not ages or code == 'adultes_connus' and any(a >= 18 for a in ages) or code == 'enfants_connus' and any(a < 18 for a in ages)):
                    resultat.add(pk)
        return len(resultat)
    if code in FAMILLE:
        valeurs=[v for v in valeurs_familiales(xs,code).values() if v is not None]
        return sum(valeurs) if valeurs else None
    raise ValidationError('Mesure non reconnue.')


def valeurs_familiales(xs,code):
    """Une valeur par déclarant distinct ; inconnus conservés pour la restitution."""
    resultat={}
    for x in xs:
        for pk in x['personnes']:
            carte=x['_par_personne'][pk]
            def valeur(champ):
                vs=carte.get('famille.'+champ,[])
                return vs[0] if len(vs)==1 else None
            if code=='enfants_famille_declares':
                a,b=valeur('enfants_a_charge'),valeur('enfants_non_a_charge')
                v=a+b if a is not None and b is not None else None
            else:v=valeur(FAMILLE[code][0])
            if code=='grossesses_famille_declarees':v=1 if v=='Oui' else 0 if v=='Non' else None
            if pk in resultat and resultat[pk]!=v:raise ValidationError('Les déclarations diffèrent selon la date de chaque objet : choisissez la référence commune pour une somme par déclarant distinct.')
            resultat[pk]=v
    return resultat


def inconnus(xs,code):
    return sum(v is None for v in valeurs_familiales(xs,code).values()) if code in FAMILLE else None
