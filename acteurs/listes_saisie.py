"""Suggestions locales pour les champs textuels de la prise en charge."""

LISTES = {
    'motif_entree': ('Motif d’entrée', ('Mise à l’abri', 'Orientation vers un logement')),
    'motif_sortie': ('Motif de sortie', ('Fin de prise en charge', 'Départ volontaire')),
    'destination_sortie': ('Destination à la sortie', ('Logement social', 'Logement privé', 'Hébergement d’urgence')),
}


def choix(champ, *, etablissement, service=None):
    if service and champ in service.listes_saisie:
        return service.listes_saisie[champ]
    return etablissement.listes_saisie.get(champ, LISTES[champ][1])
