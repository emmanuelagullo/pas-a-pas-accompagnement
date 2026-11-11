"""Codes stables du parcours résidentiel, indépendants des suggestions libres."""

DISPOSITIFS = [
    ('iml', 'Intermédiation locative'), ('maison_relais', 'Maison relais'),
    ('residence_sociale', 'Résidence sociale'), ('chu_diffus', 'CHU diffus'),
    ('stabilisation', 'Stabilisation en diffus'), ('autre', 'Autre dispositif'),
]
TYPES_LOGEMENT = [('studio', 'Studio'), *((f't{n}', f'T{n}') for n in range(1, 6))]
SITUATIONS_ENTREE = [
    ('rue', 'Sans abri, à la rue'), ('urgence', 'Hébergement d’urgence'),
    ('hotel', 'Hôtel hors urgence'), ('insertion', 'Hébergement d’insertion'),
    ('tiers', 'Hébergé chez un tiers'), ('precaire', 'Autre habitat précaire ou inadapté'),
    ('transition', 'Logement de transition'), ('durable', 'Logement durable adapté'),
    ('incarceration', 'Sortie d’incarcération'), ('hospitalisation', 'Sortie d’hospitalisation'),
    ('asile', 'Sortie de CADA ou HUDA'), ('expulsion', 'Menacé d’expulsion'),
    ('violences', 'Menacé de violences domestiques'), ('squat', 'Habitat non conventionnel ou squat'),
    ('indigne', 'Habitat indigne ou insalubre'), ('ase', 'Sortie de l’aide sociale à l’enfance'),
    ('autre', 'Autre situation'),
]
MOTIFS_SECONDAIRES = [
    ('violences_conjugales', 'Violences conjugales'),
    ('traite', 'Traite des êtres humains'),
]
DESTINATIONS = [
    ('logement_social', 'Logement social'), ('logement_prive', 'Logement privé'),
    ('pension_famille', 'Pension de famille'), ('residence_accueil', 'Résidence accueil'),
    ('iml_glissant', 'Intermédiation locative avec bail glissant'),
    ('iml_mandat', 'Intermédiation locative avec mandat de gestion'),
    ('iml_sans_glissement', 'Intermédiation locative sans bail glissant'),
    ('residence_sociale', 'Résidence sociale'), ('urgence', 'Hébergement d’urgence'),
    ('chrs', 'CHRS'), ('asile', 'Dispositif d’asile'), ('autre', 'Autre destination'),
    ('inconnue', 'Sans information'), ('hors_champ', 'Hors champ'),
]
CHAMPS_CODES = ('dispositif_logement', 'type_logement', 'situation_logement_entree', 'categorie_sortie')
