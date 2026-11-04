# Retour COL1–4 — déploiement, navigation et offre de prestations

Audit du 4 novembre 2026 sur `464e4a27fa43072adf21552539c0265043d12865`,
main Inria et miroir GitHub identiques. Lecture du code, pas un essai navigateur.
Le correctif associé corrige seulement la recette de déploiement et son témoin
sur les habilitations. Les évolutions ci-dessous sont proposées, non implémentées.

## Conclusions

Le fonctionnement collectif doit simplifier les formulaires et les opérations,
pas introduire une seconde interface. Conserver les groupes de prestations,
les cartes, les commandes d’ouverture, l’édition sur place et les choix de
repliage de NAV. Aucun intitulé « Prestations collectives » n’est nécessaire.

La sélection des bénéficiaires d’une opération commune est indépendante du suivi
individuel. Elle doit être possible en mode collectif uniquement. Le catalogue
des lieux et de leurs offres manque réellement ; le choix actuel parmi tous les
partenaires et le seul mode collectif/individuel ne le remplacent pas.

## Déploiement éphémère

`scripts/exercer-deploiement.py` attendait encore 36 personnes, contre 37 depuis
l’ajout d’Élise Laurent. La vérification par dictionnaire des tâches écrasait les
habilitations de même compte dans plusieurs services. Vérifier les six triplets
service/compte/tâche, dont les deux habilitations sociales d’essai, ainsi que les
comptes non administrateurs et l’activation du contrôle. Ne pas réduire ces
contrôles à « au moins une personne » ou « essai peut se connecter ».

## Frictions confirmées et reprise NAV

| Observation du code | Conséquence | Recommandation |
| --- | --- | --- |
| `templates/collectifs/prestations.html` mélange hébergement et restauration dans un panneau séparé | Organisation différente selon le mode de suivi | Insérer les prestations communes dans les groupes existants : séjours d’hébergement, séjours alimentaires, autres aides |
| `personnes/templatetags/collectifs.py` crée des URL `col_action` ; `static/collectifs.js` finit le POST par `window.location.assign` | Le formulaire est rendu dans la page mais les échanges rechargent le document | Réutiliser les hôtes de cartes et le protocole NAV7 de `prestation_navigation.py` et `dossier-en-place.js` ; repli pleine page sans JavaScript |
| Actions et historique propres au nouveau panneau | Deux conventions concurrentes | Même sélection, Ouvrir/Refermer, emplacement de l’éditeur et restitution après action |
| `ProfilForm` impose un mode aux deux familles | Impossible de désactiver réellement l’offre d’une famille | Séparer « prestation proposée » et « mode de suivi » |
| `acteurs/views.py` et `vues_collectif.py` utilisent un formulaire pleine page | Paramétrage dispersé, sans édition sur place | Fiche service avec sections lisibles et Modifier sur place ; garder les vues métier, droits, CSRF, transactions, jetons et journaux |

Les anciennes prestations restent dans leurs groupes, même si leur famille est
retirée des nouvelles offres. Retirer une offre doit empêcher la création côté
serveur, pas empêcher les corrections autorisées ou masquer l’histoire. Ne pas
charger de données personnelles supplémentaires pour fabriquer une carte commune.

## Choisir un groupe sans suivi individuel

Actuellement `PrestationForm` et `collectifs.creer` n’acceptent `selection` que
pour le mode `option`. En mode collectif uniquement, toute la composition est
reprise : la limite signalée est donc réelle.

Proposer « Bénéficiaires : tout le groupe » puis « Choisir un groupe ». La seconde
commande permet de sélectionner les personnes déjà identifiées et les nombres
complémentaires par catégorie. Exemple : le ménage comporte un adulte identifié,
un adulte non identifié et deux enfants ; la restauration peut concerner l’adulte
identifié et un enfant, sans créer l’identité de cet enfant. La personne de
référence du ménage peut rester extérieure à ce sous-groupe : elle décrit le
ménage, elle ne prouve pas qu’elle reçoit chaque prestation. Ne pas exiger une
nouvelle « personne de référence de la sélection » pour pouvoir nourrir des enfants.

Conserver une photographie propre à la prestation, avec provenance et date ; ne
pas modifier la composition du ménage ou les bénéficiaires de la prise. Les
modèles de composition versionnée existants donnent une base, mais la référence
obligatoire et la sélection actuelle sans compléments doivent être adaptées.
Un sous-groupe n’est ni une ventilation en prestations individuelles ni une
exception de présence. Le mode « collectif avec suivi fin » règle seulement ces
exceptions et leurs commandes. L’effectif sélectionné propose les couverts,
qui restent ajustables explicitement ; un changement de sélection doit signaler
les nombres déjà personnalisés et ne pas les écraser silencieusement.

Pour éviter les doublons, avertir d’un chevauchement sur le même groupe, lieu et
repas. Des nombres anonymes ne permettent pas de prouver que deux groupes sont
disjoints : le signaler sans fabriquer d’identités ni promettre une détection
exhaustive. Conserver les statistiques de volumes distinctes des bénéficiaires.

## Lieux d’alimentation et tarifs

Solenne `Form3.java`, `modifie_pt_dej`, lit les champs 4, 5 et 6 du lieu choisi
pour les prix adulte, jeune et bas âge. `calculePrixRepas` affiche le coût du
repas pour le groupe puis le total de la période. Cette méthode utilise un même
prix par catégorie pour les services midi et soir ; elle ne démontre pas une
politique de prix différenciés entre ces deux repas.

Aujourd’hui `VersionTarif` conserve déjà prestataire, catégorie, unité, devise,
dates et versions. `collectifs.tarifs_proposes` cherche les prix par partenaire,
libellé de catégorie et unité `repas` ; il refuse de choisir lorsqu’il trouve
plusieurs candidats. `PrestationForm` propose tous les partenaires accessibles.
Il n’y a ni catalogue de lieux alimentaires autorisés par service, ni offre
midi/soir, ni sélection fiable d’un tarif différent par repas. Créer deux tarifs
homonymes ne résout pas cette absence : cela peut rendre la suggestion ambiguë.

Recommandation :

- Un prestataire peut posséder plusieurs lieux internes ou externes. Ne pas
  confondre ces lieux avec l’établissement organisationnel des services.
- Chaque lieu a des offres explicites : hébergement, déjeuner, dîner, transport,
  etc. Un nouveau lieu de restauration propose déjeuner et dîner par défaut,
  sous réserve de confirmation ; ce défaut ne s’applique pas à un hôtel ou à un
  transporteur. Un lieu peut proposer seulement le midi.
- Le service choisit les offres qu’il utilise, parmi celles des prestataires.
  Par défaut, un seul lieu autorisé est préselectionné. L’étiquette quotidienne
  reste « Lieu d’alimentation ».
- Prix commun midi/soir par catégorie par défaut. Une option « Prix du dîner
  différent » permet une dérogation ; ne pas imposer deux grilles identiques.
  Hébergement et petits déjeuners gardent leurs propres unités et tarifs.
- Réutiliser les versions tarifaires et les partenaires existants, en ajoutant
  une définition structurée de l’offre et un lien service/offre. Ne pas ajouter
  des prix concurrents dans le JSON du profil de service. Identifier les
  catégories de manière stable plutôt que par égalité de leur seul libellé.
- Photographier le lieu, les repas, les quantités, les prix retenus et leur
  provenance pour chaque version. Une modification du catalogue ne réécrit pas
  les séjours. Distinguer tarif proposé, prix particulier et prix inconnu.

Une prestation alimentaire peut regrouper déjeuner et dîner si son lieu et son
groupe sont communs. Des prix différents n’obligent pas à la scinder. Deux lieux
ou deux groupes différents justifient deux prestations. Une granularité par jour
ou par personne reste inutile pour calculer un accord de période.

## Calculs et garde-fous dans le formulaire

Le moteur `collectifs.bilan` calcule déjà des services de repas, couverts et
montants ; son absence dans le formulaire est une lacune d’affichage. L’élément
`data-collectif-calcul` est actuellement vide. Il ne suffit donc pas d’indiquer
que le bilan existe.

Afficher après les effectifs/prix, sans ouvrir une page annexe :

- « Par déjeuner : 26 € pour le groupe » ; idem dîner lorsque nécessaire ;
- « Période : 3 déjeuners + 2 dîners, 20 repas, total calculé 130 € » dans
  l’exemple de deux adultes à 8 € et deux enfants à 5 €, avec prix commun ;
- « Total incomplet — prix enfant non renseigné » si un tarif manque, jamais
  transformer un prix inconnu en zéro ;
- « Total de la période non calculable sans date de fin » pour une période
  ouverte, tout en conservant le coût d’un repas pour le groupe.

Calcul immédiat à chaque modification de période, repas, sélection, effectifs,
prix ou lieu. Le serveur reste l’autorité ; même arrondi décimal et même résultat
avec ou sans JavaScript. Ne pas lancer un second moteur divergent en flottants.
Un aperçu serveur contrôlé peut réutiliser une fonction pure de calcul commune
au bilan et à la validation. Un changement de date ou devise doit aussi actualiser
les propositions tarifaires, en préservant les prix explicitement personnalisés.
Les petites décimales doivent être arrondies selon une règle affichable et
identique au bilan ; la règle actuelle arrondit par ligne de catégorie/période.

Dans la carte repliée, privilégier lieu, dates, repas et effectif. Ajouter au plus
une mention « Total calculé : … € » lorsque la période et les prix sont complets ;
le détail du calcul reste dans la consultation. Ce montant n’est ni une facture,
ni un paiement, ni la preuve de repas distribués. La fin prévue ne doit pas se
faire passer pour une réalisation. Les bornes fines restent dans la restauration.

| Repas sélectionnés | Premier et dernier repas |
| --- | --- |
| Déjeuner seulement | Déjeuner automatique, commandes grisées |
| Dîner seulement | Dîner automatique, commandes grisées |
| Les deux | Choix actifs, déjeuner puis dîner proposés par défaut |
| Aucun | Erreur explicite, pas de calcul trompeur |

Le serveur impose déjà le cas mono-repas dans `PrestationForm.clean` ; le
navigateur ne le montre pas encore. Les champs désactivés ne sont pas envoyés :
le serveur doit les reconstruire avant leur validation de champ, et pas seulement
les remplacer après celle-ci. Sans JavaScript, les valeurs doivent rester
compréhensibles et être normalisées selon les repas cochés. Si le lieu ne sert
que le midi, aucune activation du dîner ne doit être acceptée côté serveur.

## Paramétrage et vocabulaire

Recommander une entrée commune **Paramétrage**, accessible depuis Établissement,
avec deux entrées **Services** et **Prestataires**. Pas un tableau géant de cases.
La gestion des partenaires d’orientation n’est pas remplacée par celle des offres.
Les mêmes fiches partenaires peuvent être réutilisées, avec seulement leurs
rôles pertinents affichés dans Prestataires.

Une fiche service comporte : **Informations demandées**, **Prestations proposées**,
**Membres du service**, **Accès aux dossiers**. Les profils métier proposent un
ensemble cohérent ; les dérogations ciblées sont visibles. L’appartenance d’un
professionnel au service ne lui confère toujours pas automatiquement de droits.
La fiche prestataire présente ses lieux, offres, tarifs et périodes d’activité ;
les affectations/chambres restent dans leur domaine, sans inventer une capacité
ou une disponibilité à partir d’un libellé de lieu.

| Libellé actuel | Libellé recommandé |
| --- | --- |
| Prestations collectives | Aucun panneau supplémentaire ; groupes habituels |
| Personne de référence pour la collecte | Personne de référence du ménage |
| Changer la politique du service | Modifier l’accès aux dossiers du service |
| Professionnels du service | Membres du service |
| Inscrire un professionnel existant | Ajouter un membre |
| Configurer la collecte et les prestations collectives | Informations demandées et prestations proposées |
| Tâches autorisées | Habilitations, avec rôle et droits expliqués |

La personne de référence du ménage ne devient ni le professionnel référent, ni
le bénéficiaire obligatoire, ni le détenteur supposé des revenus ou droits du
ménage. Le titre « Accès aux dossiers » décrit la politique existante, distincte
de la politique de collecte. L’utilisateur peut ajuster sa présentation, jamais
élargir son droit ou réactiver une collecte interdite.

## Reprise recommandée et critères de réception

1. Correctif CI isolé : vérifier les deux démarrages éphémères réels, les
   habilitations par service et l’absence de droits administrateurs.
2. Reprise ergonomique cohérente : groupes et cartes NAV communs, édition et
   annulation sur place, lexique, sélection d’un groupe en mode collectif seul,
   aperçu des totaux et mono-repas. Vérifier les quatre modes JavaScript/sans
   JavaScript et mobile/large ; préserver le contexte, le repliage et le focus.
   Tester correction, prolongation, fin, annulation et création, pas seulement
   l’ouverture d’un formulaire. Les prix existants restent utilisables.
3. Catalogue prestataires/offres/services et tarifs par repas : modèle et
   migration explicites, configuration sur place, interdictions revalidées sur
   les routes de création et fragments, prix photographiés. Retirer une offre
   interdit les nouvelles attributions mais conserve sa consultation historique
   et les corrections autorisées. Tester les tarifs changeant à date, les prix
   personnalisés, les lieux midi seul et les services utilisant un même lieu.

La réception des Amandiers exige un seul accord commun pour le groupe choisi,
une seule prolongation/correction et aucune saisie individuelle imposée. Le
service Accompagnement doit conserver les mêmes conventions de navigation. Ne
pas ajouter ces trois lots à la qualification déjà annoncée de COL1–4 : ils
constituent une reprise à tester. Le profil AHI et les vues d’occupation restent
des chantiers distincts ; ne pas les annoncer comme réalisés avec ce correctif.
