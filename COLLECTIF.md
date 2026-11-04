# COL1–4 — collecte et prestations collectives

Le collectif est une unité métier, pas une addition d'écritures personnelles.
Les services existants restent en profil historique jusqu'à configuration
explicite. Aucune migration n'accorde de droit ni ne convertit l'histoire.

COL1 : contrat et scénario. COL2 : composition déclarée datée, identification
partielle et situation du ménage. COL3 : hébergement commun. COL4 : restauration
par période, couverts et prix particuliers, bilan de volumes calculés.

Une personne de référence pour la collecte n'est ni un contact ni un représentant
légal. Les effectifs non individualisés sont supplémentaires aux personnes
identifiées ; aucune identité fictive n'est créée. Une date de naissance permet
une catégorie calculée à la date choisie ; un âge ou une catégorie déclarés ne
permettent pas une actualisation automatique certaine.

La prise ne représente pas une présence. Les prestations reprennent ses dates
comme proposition modifiable. Les bornes fines appartiennent à la restauration.
L'hébergement et la restauration restent séparés. Les prestations conservent
leur composition d'origine ; une correction ne réécrit pas les autres périodes.

Les versions datées du ménage et de prise restent distinctes. Reprendre la
composition de la prise au ménage exige confirmation et preuve que le ménage
n'a pas changé. Une saisie ancienne ne remplace pas la dernière déclaration.

Le choix d’un sous-groupe est disponible dans tout mode collectif. Il comprend
les personnes identifiées choisies et les effectifs complémentaires déclarés,
sans modifier le ménage. La personne de référence du ménage n’est pas
nécessairement bénéficiaire. Ce choix n’active pas un suivi individuel. Le mode
historique individuel reste disponible.

Les nuits et repas calculés ne sont pas des présences ou distributions pointées.
Les volumes des groupes partiellement identifiés ne sont pas des effectifs de
personnes distinctes. Les anciens rapports nominatifs conservent leur définition.
Le bilan collectif distingue les volumes déclarés, les coûts et les unités.

Les Amandiers est le scénario minimal : une personne de référence, deux adultes
et deux enfants au total, un revenu mensuel du ménage, un hébergement commun et
une restauration du dîner du 10 au déjeuner du 13 (trois déjeuners et trois
dîners par couvert). Habitat et parcours prépare le jalon AHI ultérieur ; aucun
rapport n'est présenté comme conforme à cette fiche avant sa qualification.

Hors COL1–4 : inventaire capacitaire et garantie de disponibilité des lieux,
rapport AHI, rapprochement automatique des identités, moteur de champs libres,
pointage anonyme et facturation. Les interfaces de ces fonctions ne sont pas
annoncées comme disponibles.


## Utilisation et installation

Dans Établissement, ouvrir un service puis « Configurer la collecte et les
prestations collectives ». Le profil proposé identifie une personne de référence,
avec effectifs complémentaires par catégories adaptables et gestion collective
uniquement. Les modes de suivi sont distincts pour hébergement et restauration.
Les services existants ne sont pas activés automatiquement.

Le compte de configuration doit avoir acteurs.gerer_organisation ; ce droit
ne donne pas accès aux dossiers. Hors contrôle par service, accorder volontairement
les permissions aux comptes existants avec `python3 manage.py autoriser_collectif NOM`.
Lorsque le contrôle est actif, les nouvelles données sociales collectives relèvent
actuellement de la tâche accompagnement social, sous les portées de service.
Les tâches accueil/gestion historiques continuent leurs anciens parcours ; leur
accès à une projection collective sans données économiques doit être traité
explicitement, pas par ouverture de toute la composition sociale.

Dans le dossier ou la prise : Situation sociale et projet → Composition et
situation du ménage → Renseigner/Modifier. Les nombres supplémentaires excluent
les personnes identifiées. Les âges ou naissances sans identité sont une option
secondaire, sans création d'identités. Un âge déclaré ne définit pas d'anniversaire.
Les données personnelles détaillées sont présentées seulement pour les personnes
retenues par le profil ; les données anciennes restent accessibles sous leurs droits.

Dans une prise : Nouvel hébergement / Nouvelle restauration. Les dates sont
proposées depuis la prise et modifiables ; les prestations ne sont pas une présence
implicite. Un hébergement prévu n'a ni arrivée ni lieu effectif. Le tableau de
restauration distingue couverts par repas et prix unitaires. Un prix de catalogue
non ambigu pour le prestataire, la catégorie, la date et la devise est proposé ;
un prix édité devient particulier. Une correction ne réécrit pas le catalogue.

Le mode avec détail facultatif permet une sélection de personnes identifiées
pour une nouvelle prestation distincte. Il ne réalise pas automatiquement la
scission d'une prestation existante : terminer/corriger la période précédente
si nécessaire pour éviter le recouvrement. Les identités non recueillies ne
peuvent pas être inventées pour obtenir une exception personnelle.

Le bilan de la prise réunit les volumes collectifs, sans addition avec les anciens
rapports de distributions. Il indique les prix manquants et les unités ; les
petits déjeuners associés suivent les matins après l'arrivée jusqu'au départ.
Une absence ne libère pas le lieu et ne suspend pas implicitement la restauration.
L'impression utilise le navigateur ; ce bilan n'est pas une facture émise.

Limites explicites de cette livraison : pas de garantie capacitaire, pas de
statistiques AHI ni d'intégration des populations collectives dans le compositeur
historique. Les données physiques restent dans les sauvegardes SQLite complètes.


## COL4b — mêmes gestes entre services

Les prestations communes apparaissent dans Hébergement et Repas : Nouveau séjour,
Nouvelle période de repas, Ouvrir, Corriger, Prolonger, Annuler et Refermer.
Le transport NAV7 maintient la page et ses autres rubriques en place. Sans
JavaScript, les mêmes vues métier et validations restent utilisables.
Le formulaire alimentaire présente un calcul serveur, sans mutation ; Calculer
est disponible sans JavaScript. Les totaux sont ceux de la période accordée,
jamais des preuves de distributions ni des factures.

Paramétrage réunit Services et Prestataires, avec édition sur place. Une offre
associe un lieu partenaire, une famille et, pour les repas, déjeuner/dîner
(les deux par défaut). Le service peut limiter ses nouvelles attributions aux
offres sélectionnées. Les anciens profils gardent leurs choix historiques tant
que cette limitation n’est pas activée. Retirer une offre ou désactiver les
nouvelles saisies ne supprime pas l’histoire et ne bloque pas les rectifications
autorisées. Les noms d’offres sont photographiés dans les versions.

Les prix réutilisent les tarifs datés : prix commun par catégorie, avec dîner
différent facultatif. Les valeurs particulières restent éditables. Le droit
acteurs.view_tarifoffre ouvre uniquement la projection des prix des offres ;
il est ajouté par la commande volontaire autoriser_collectif et dans le jeu
neuf, jamais par migration sur les comptes existants. Modifier les prix conserve
les permissions financières explicites existantes. Le catalogue ne représente
ni un stock de chambres/lits ni une disponibilité garantie.
