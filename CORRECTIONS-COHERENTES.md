# Précisions de correction : comportement commun

Base publique examinée : `f82cbfb3f4d8db58ec93539eed809332a1beb2cb`.
Le lot s'applique après les patches 0008 (repas/options) et 0009 (aide Frise).
Données de qualification exclusivement fictives. Aucun changement du socle,
des sources sociales, des droits ou des définitions statistiques.

## Règle

La précision d'une correction ordinaire peut rester vide. La trace conserve
l'auteur, l'enregistrement, les valeurs ou versions précédentes et suivantes.
Une phrase libre n'est pas une preuve d'état, une source ou une confirmation de
portée. Les dates, bénéficiaires, droits, verrous, signatures, conflits,
dépendances et confirmations restent contrôlés par leurs services.

La règle vaut sur place et dans les formulaires en pleine page. Les champs de
précision facultatifs utilisent le composant Précisions facultatives, fermé initialement et ouvert si un champ contient une
erreur. Les champs métier « motif de demande », « motif de décision », « motif
de sortie » ne deviennent pas des annotations de correction.

## Audit et couverture

| Famille | Traitement de la rectification | Principaux services |
| --- | --- | --- |
| Identité personnelle | Déjà facultative ; présentation complète harmonisée | `identite` |
| Situation personnelle datée, famille, coordonnées, compléments d'identité | Déjà facultative ; mêmes précisions repliées en pleine page | `bd6`, `series_personnelles` |
| Contact désigné, fiches de professionnels et partenaires | Précision désormais facultative, y compris insertion antérieure ; plus d'obligation dépendant du type de journal | `series_personnelles` et vues spécialisées |
| Situation sociale des anciens suivis | Correction et insertion antérieure facultatives ; source et bornes restent vérifiées | `social` |
| Dates de ménage, appartenance, prise, accords, séjour, affectation et absence | Correction facultative ; contrôles de dépendances conservés | `corrections` |
| Événements et bilans | Correction de texte/date/source facultative | `corrections` |
| Prévisions des prises en charge | Correction facultative ; prolongation distincte | `bd6` |
| Continuité individuelle | Correction de la date de coupure facultative ; aucun épisode créé implicitement | `continuite_hebergement` |
| Informations des lieux | Correction facultative | `hebergement` |
| Repas : quantité, catégorie, jours et prestataire | Correction facultative ; catégorie visible et préremplie | `correction_repas` |
| Missions des intervenants | Correction et insertion antérieure facultatives ; clôture séparée | `interventions` |
| Aides : autorisations, remises et constats d'utilisation | Précision de rectification facultative ; sources et bornes conservées | `aides` |
| Informations et projet d'une prise, déclarations sociales détaillées, parcours et objectifs | Déjà facultatives ; sources et journal métier existants préservés | `informations_suivi`, `dossier_complet`, `parcours` |
| Commentaire du dossier | Versions ultérieures possibles sans explication obligatoire, y compris effacement | `bd6` |
| Notes et transmissions | Correction de texte/date facultative ; versions, conflits et annulations conservés | `transmissions` |
| Actions de relais | Correction du libellé/de l'échéance facultative ; changements de statut séparés | `releve` |
| Appels au 115 | Correction facultative ; suite et associations distinctes | `appels115` |
| Documents joints | Correction ou remplacement versionné facultatif ; provenance toujours demandée | `pieces_dossier` |
| Prix et calculs de financement | Correction facultative ; ancienne version et documents émis inchangés | `financements` |
| Propositions de saisie et types d'aide | Correction d'une entrée existante facultative ; définition/import séparés | `propositions`, `aides` |
| Acteurs : message d'attribution/relais | Déjà facultatif, distinct du motif de correction ; inchangé | `acteurs.services` |

## Opérations distinctes conservant leur justification

L'obligation n'est plus attachée au domaine « repas », « finance » ou au type du
journal. Elle reste attachée aux opérations explicites suivantes :

- Annuler une saisie, une arrivée, une contribution, un lien ou un document :
  cette action écarte explicitement un fait des restitutions courantes, sans
  le supprimer. Le motif d'annulation demeure distinct de la correction.
- Prolonger une autorisation ou une prévision, définir/changer un prix ou un
  calcul de financement : il s'agit d'une décision ou d'une nouvelle version
  métier, pas de la rectification d'une valeur. La source n'est pas remplacée
  par le motif et les documents antérieurs restent figés.
- Clore explicitement une relation, une déclaration ou une mission, terminer ou
  rouvrir une action : les contrats spécialisés des changements réels restent
  en place. Corriger une date déjà renseignée demeure facultatif.
- Créer la continuité individuelle initiale : l'opération transforme la portée
  d'un séjour collectif ; sa rectification ultérieure n'exige plus de précision.
- Associer/dissocier explicitement demande et prise ou appel et parcours : il
  s'agit du choix d'un lien métier, avec contrôles dédiés.
- Compléter un appel par une suite, définir un catalogue initial ou importer un
  paramétrage : ces opérations n'ont pas été assimilées à une correction.

Ce sont les règles actuelles conservées pour ces opérations distinctes, pas une
exigence légale générale ni une nouvelle définition de leurs sources.

## Formulaires proposant plusieurs opérations

Les formulaires de tarifs, financement, appels et actions de relais déterminent
l'obligation à partir de l'opération choisie. En mode Correction, la précision
est facultative et repliée ; pour une opération nécessitant une justification,
le champ est visible et requis. Changer l'opération ne perd pas le texte saisi.
Le serveur recalcule la règle depuis les données soumises, indépendamment du JS.
Sans JavaScript, ces formulaires laissent le serveur valider le mode sélectionné
à l'enregistrement, sans blocage natif lié au mode initial. Une erreur laisse
les données saisies et affiche le champ concerné.

## Données et migration

La migration `0045_precisions_corrections_facultatives` rend facultatif le motif
pour les journaux généraux de dates, textes et contributions, les évolutions de
prévision, les versions de prix/calcul et les révisions de propositions. Elle
ne remplit, n'efface et ne réécrit aucun ancien motif. Les opérations spécialisées
continuent à exiger leur justification dans les services et formulaires.
Aucune annotation automatique « erreur de saisie » n'est inventée pour remplir
un journal. Le contexte commun reste facultatif et distinct de la provenance ;
seuls les journaux qui le prenaient déjà en charge le conservent.

## Qualification

La recette `personnes.qualification_evolution` couvre l'édition d'un événement
sur place sans précision, le maintien d'Évolution et des dépliements, les repas,
les tarifs avec bascule Correction / Nouvelle décision, le clavier, 390 px, le
repli sans JavaScript et l'aide Frise. Les tests HTTP/services couvrent également
les versions de financement, les octets des pièces anciennes, les journaux vides,
les preuves périmées, les refus d'annulation sans motif et la longueur maximale.
Chromium n'est pas une qualification de Firefox, des programmes natifs,
PostgreSQL ou du vrai Pyodide/OPFS.

Résultats : 165 tests ciblés réussis, puis 81 tests de confirmation réussis
(passes non disjointes), ainsi que cinq recettes réelles Chromium. La suite
générale a exécuté 986 tests, avec trois ignorés et quatre anciennes attentes
sur les motifs devenues obsolètes : commentaire, identité, insertion antérieure
et correction de prévision. Ces attentes sont adaptées à la règle validée ;
les 52 tests de leurs quatre modules sont ensuite tous réussis. La suite
générale n'a pas été répétée après ces adaptations de tests uniquement.
Contrôles Django, absence de migration manquante, syntaxe JS et diff réussis.
Les contrôles d'accès, de doublons, de bornes et de formulaires périmés de ces
tests sont conservés ; les nouveaux cas vérifient aussi le journal vide.
