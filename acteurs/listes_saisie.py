"""Suggestions locales pour les champs textuels de la prise en charge."""

DESTINATION_SORTIE = "Destination à la sortie"

LISTES = {
    'situation_sejour': ('Situation de séjour déclarée', ()),
    'nature_ressource': ('Nature du revenu', ()),
    'couverture_sociale': ('Couverture déclarée', ()),
    'droits_ouverts': ('Droits sociaux ouverts', ()),
    'motif_entree': ('Motif d’entrée', ('Mise à l’abri', 'Orientation vers un logement')),
    'qualification_sortie': ('Précision sur la sortie', ()),
    'motif_sortie': ('Motif de sortie', ('Fin de prise en charge', 'Départ volontaire')),
    'destination_sortie': (DESTINATION_SORTIE, ('Logement social', 'Logement privé', 'Hébergement d’urgence')),
}


def choix(champ, *, etablissement, service=None):
    if service and champ in service.listes_saisie:
        return service.listes_saisie[champ]
    return etablissement.listes_saisie.get(champ, LISTES[champ][1])
