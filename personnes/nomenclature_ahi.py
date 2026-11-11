"""Choix déclarés pour la fiche AHI du 8 avril 2026."""

ADMINISTRATION = {
    'france': 'Nationalité française',
    'ue_droits': 'Autre nationalité de l’UE, avec droits',
    'ue_sans_droits': 'Autre nationalité de l’UE, sans droit',
    'hors_ue': 'Hors UE, autre situation',
    'asile_normale': 'Hors UE, demande d’asile en procédure normale',
    'asile_en_cours': 'Hors UE, demande d’asile en cours de procédure',
    'sans_aps': 'Hors UE, sans APS',
    'dublin': 'Hors UE, procédure Dublin',
    'prioritaire': 'Hors UE, procédure prioritaire',
    'titre': 'Hors UE, titre de séjour',
    'aps_maladie': 'Hors UE, APS liée à la maladie',
    'vpf': 'Hors UE, carte vie privée et familiale',
    'resident': 'Hors UE, carte de résident',
    'deboute': 'Hors UE, débouté du droit d’asile',
    'refugie': 'Hors UE, réfugié statutaire',
}
LOGEMENT = {
    'rue': 'À la rue',
    'chu': 'CHU sur site ou en diffus',
    'hotel': 'Hôtel hors urgence',
    'incarceration': 'Sortie d’incarcération',
    'hospitalisation': 'Sortie d’hospitalisation',
    'asile': 'Sortie de CADA ou HUDA',
    'insertion': 'Hébergement d’insertion',
    'tiers': 'Hébergé chez un tiers',
    'expulsion': 'Menacé d’expulsion au stade de l’assignation',
    'violences': 'Menacé de violences domestiques',
    'squat': 'Habitat non conventionnel ou squat',
    'indigne': 'Habitat indigne ou insalubre',
    'durable': 'Logement durable adapté',
    'transition': 'Logement de transition',
    'ase': 'Sortie de l’aide sociale à l’enfance',
}
ACTIVITE = {
    'emploi': 'En emploi', 'recherche': 'En recherche d’emploi',
    'formation': 'En formation', 'sans_activite': 'Sans activité',
}
DROITS_SOCIAUX = {
    'aucun': 'Aucun droit ouvert', 'prestations': 'Accès aux prestations sociales et familiales',
    'autres': 'Autres droits ouverts',
}
COUVERTURE = {
    'ame': 'AME', 'puma': 'CMU/PUMA', 'autre': 'Autre couverture', 'aucune': 'Sans couverture',
}
SORTIES = {
    'social': 'Parc social', 'prive': 'Parc privé', 'prive_mandat': 'Parc privé avec mandat de gestion',
    'ordinaire_autre': 'Autre logement ordinaire',
    'pension': 'Pension de famille', 'residence_accueil': 'Résidence accueil',
    'iml_glissant': 'Intermédiation locative avec bail glissant',
    'iml_mandat': 'Intermédiation locative avec mandat de gestion',
    'sous_location_glissante': 'Sous-location avec bail glissant',
    'residence_sociale': 'Résidence sociale', 'fjt': 'Foyer de jeunes travailleurs',
    'ftm': 'Foyer de travailleurs migrants',
    'iml_sans_glissement': 'Intermédiation locative sans bail glissant',
    'sous_location_sans_bail': 'Sous-location sans bail glissant',
    'chu': 'CHU sur site ou en diffus', 'stabilisation': 'Stabilisation', 'hotel': 'Hôtel social',
    'chrs': 'CHRS', 'appartement_relais': 'Appartement relais',
    'hospitalisation': 'Hospitalisation', 'incarceration': 'Incarcération',
    'tiers': 'Chez un tiers', 'rue': 'Rue', 'domicile': 'Retour au domicile',
    'etablissement': 'Établissement pour personnes âgées ou handicapées',
    'medico_social': 'Structure médico-sociale', 'huda': 'HUDA', 'cada': 'CADA',
    'inconnue': 'Sans information', 'hors_champ': 'Hors champ',
}
QUALIFICATIONS_SORTIE = {
    'dalo': 'DALO', 'syplo': 'Syplo', 'mdes': 'MDES', 'logement_abord': 'Logement d’abord',
    'hors_departement': 'Hors département', 'exclusion': 'Exclusion du dispositif',
    'depart_volontaire': 'Départ volontaire', 'deces': 'Décès',
}
ADULTE = {
    'administration': ('Classement administratif à l’entrée', ADMINISTRATION),
    'logement': ('Situation résidentielle à l’entrée', LOGEMENT),
    'activite': ('Situation socio-professionnelle à l’entrée', ACTIVITE),
}
MENAGE = {
    'droits': ('Droits ouverts de la personne de référence à l’entrée', DROITS_SOCIAUX),
    'couverture': ('Classement de sa couverture santé à l’entrée', COUVERTURE),
    'sortie': ('Catégorie de destination à la sortie', SORTIES),
}

RESSOURCES = {
    'salaire': 'Salaire', 'formation': 'Formation', 'chomage': 'Allocations chômage',
    'indemnites': 'Indemnités journalières', 'rsa': 'RSA', 'aah': 'AAH',
    'familiales': 'Allocations familiales', 'autres': 'Autres ressources',
}
MOTIFS = {'violences': 'Violences conjugales', 'traite': 'Traite des êtres humains'}
CHOIX_MULTIPLES = {
    'ressources': ('Natures des ressources à l’entrée', RESSOURCES),
    'motifs': ('Motifs secondaires à l’entrée', MOTIFS),
}
GROUPES_LOGEMENT = {
    'Sans logement': {'rue', 'chu', 'hotel', 'incarceration', 'hospitalisation', 'asile', 'insertion'},
    'Habitat précaire ou inadapté': {'tiers', 'expulsion', 'violences', 'squat', 'indigne'},
}
GROUPES_SORTIES = {
    'Logement ordinaire': {'social', 'prive', 'prive_mandat', 'ordinaire_autre'},
    'Logement durable adapté': {'pension', 'residence_accueil', 'iml_glissant', 'iml_mandat', 'sous_location_glissante'},
    'Logement de transition': {'residence_sociale', 'fjt', 'ftm', 'iml_sans_glissement', 'sous_location_sans_bail'},
    'Hébergement d’urgence ou d’insertion': {'chu', 'stabilisation', 'hotel', 'chrs', 'appartement_relais'},
    'Dispositif d’asile': {'huda', 'cada'},
}
