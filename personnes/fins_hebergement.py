"""Borne de séjour utilisée pour le calendrier, sans constater de départ."""
from acteurs.profils_collectifs import fin_hebergement_unique


def fin_sejour(sejour):
    if sejour.fin is not None:
        return sejour.fin
    accord = sejour.accord
    if accord.fin and fin_hebergement_unique(accord.accompagnement):
        return accord.fin
    return None


def fin_collective(version):
    if version.fin is not None:
        return version.fin
    if (version.fin_prevue and version.prestation.nature == 'hebergement'
            and fin_hebergement_unique(version.prestation.accompagnement)):
        return version.fin_prevue
    return None
