## BD4 — chercher puis ouvrir un dossier

- Recherche centrale dès l’accueil : ménages ou personnes, filtrage dynamique
  progressif, recherche des membres actuels et anciens, pagination et repli GET.
- Dossier personne/ménage réunissant les prestations de toutes les périodes,
  bascule explicite et retour au ménage d’origine avec sélection conservée.
- Création explicite depuis la saisie, sans suivi social ni prestation implicite ;
  choix de la période avant toute nouvelle prestation.
- Retours signés des opérations, notes personne et corrections d’identité ;
  entrée Sauvegardes & Transferts adaptée au profil. Aucun changement de modèle.

## BD3 — décisions sur les accords

- Prolongation motivée des accords d’hébergement et de repas : nouvelle fin
  exclue ou période ouverte, sans admission ni distribution implicite.
- Annulation tracée d’un accord erroné sans séjour ni distribution rattachée ;
  conservation des données et du journal d’origine, refus des nouvelles réalisations.
- Droits dédiés attribués volontairement, migration additive et décisions
  conservées dans les copies locales ; aucun droit ajouté aux comptes existants.

## BD1–BD2 — dossier et navigation

- Dossier d’accompagnement : tous les séjours et périodes de repas, sélection
  explicite et actions selon les droits et l’état.
- Retours depuis les formulaires et pages liées avec sélections conservées,
  recherche et date de travail si transmises.
- Services, historiques, contrôles de concurrence et anciens parcours conservés ;
  aucune migration, prolongation dédiée ou annulation d’accord nouvelle.

## CHRS26 — parcours quotidiens et rapports

- Actions d’hébergement adaptées aux périodes enregistrées et aux séjours clos.
- Rappel du ménage et des bénéficiaires dans les formulaires de séjour ; cible des notes selon les droits.
- Date de la journée conservée dans les accords, les notes et leurs corrections ; annulation explicite.
- Auteur des transmissions visible dans la relève du travail du jour.
- Rapports : filtres pertinents, résultats avant les modèles, options secondaires repliables.
- Aucun nouveau champ, calcul statistique ou droit implicite.

## CHRS7 — corrections motivées

- Dates corrigibles sans exclure les réalisations ou créer des chevauchements.
- Dates/sources sociales et textes d’événements/bilans, avec historique avant/après.
- Refus des formulaires périmés, droits explicites et sérialisation des écritures liées.
- Nouveaux jeux fictifs CHRS1–7 ; espaces et permissions existants préservés.

## CHRS6 — travail du jour

- Séjours, lieux et absences enregistrés à une date ; alertes d’accord expiré.
- Distributions de repas par lot atomique, sans création automatique ni doublon.

## CHRS5 — fiche d’accompagnement

- Navigation depuis les personnes et ménages, rubriques repas/hébergement/social.
- Retour contextuel après écriture et message de confirmation.

## Historique des travaux — copies locales communes

- #SOC : démonstration métier fictive Les Passerelles, parcours CHRS1–4 guidé,
  serveur jetable et chargement facultatif au premier démarrage PWA/bureau.

- Parcours de sauvegarde/restauration du programme repris de Petits Pas :
  vérification, annulation, confirmation, arrêt, état précédent et reconnexion.
- Médias conservés dans les copies PWA et les échanges avec Linux/Windows,
  dans les plafonds du prototype. Sonde technique CHRS1–4, sans démonstration métier.
- Adoption candidate de pas-communs 0.9.0 après publication immuable de son wheel.

## CHRS4 — situation et parcours sociaux

- Logement, emploi/formation et ressources déclarées par bénéficiaire et date.
- Historique des valeurs, correction motivée, événements et bilans courts.
- Consultation datée et chronologie avec les prestations accessibles.
- Attribution cumulative explicite CHRS1–4 ; sauvegardes et migrations qualifiées.

## CHRS3 — hébergement et séjours effectifs

- Accords d’hébergement, admissions avec bénéficiaires explicites et lieux partenaires.
- Affectations successives, absences sans sortie et clôtures transactionnelles.
- Droits explicites, journal et contrôle des chevauchements au sein du séjour.
- Reprise des sauvegardes étendue à l’hébergement ; socle inchangé.

## CHRS2 — repas accordés et réalisation effective

- Accords avec bénéficiaires, service, période et prestataire facultatif.
- Distributions datées, total hors annulations et corrections motivées.
- Permissions explicites, journal et refus SQL des doublons actifs par accord.
- Reprise historique étendue aux accords et distributions, sans changer le socle.

## CHRS1 — ménages et accompagnements

- Ménages, appartenances datées et accompagnements sans hébergement.
- Bénéficiaires explicites, clôtures conditionnelles et journal des opérations.
- Droits attribués volontairement via autoriser_chrs1 ; aucune migration de droits.
- Reprise des copies historiques et nouvelles relations testées sur SQLite.

# Historique

## À venir

Aucune modification annoncée depuis 0.3.0.

## 0.3.0 — 2026-10-21

Évolution du prototype fictif Pas à Pas — Accompagnement : parcours CHRS
élargis, pilotage de l'activité et guide public réorganisé. Cette version
reste réservée aux **données fictives** : elle ne qualifie pas l'exploitation
de dossiers réels ni un déploiement en production.

- Hébergement : cycle admission, affectations successives, absences, retour
  et sortie ; navigation et vérifications de cohérence renforcées.
- Dossiers personne et ménage : rattachement à un ménage existant sans
  ressaisie de la personne, navigation et contrôles des permissions.
- Travail quotidien : transmissions, actions de relais et retours contextuels
  conservant la date consultée.
- Statistiques : indicateurs d'hébergement et de repas, périodes et comparaisons,
  exports CSV, rapports enregistrés et filtres plus lisibles.
- Guide Hugo : fiches cliquables, recherche par mots-clés, catégories croisées
  et suggestions de fiches apparentées.
- Qualification : recettes Django et Chromium élargies ; traitement des
  fichiers statiques et accès ORM des tests navigateur corrigés ; test de
  concurrence SQLite fiabilisé sans assouplir la règle de non-chevauchement.
- Socle partagé pas-communs 0.8.0 et publication des candidats sans promotion
  automatique de la PWA stable.

- #SOC : homogénéiser l’essai Les Passerelles avec Petits Pas : espace distinct
  persistant, aller-retour PWA/bureau, comptes publics et conservation des espaces
  créés avec le premier patch. Retirer le chargement du jeu dans le formulaire initial.

- Correction des codes de secours concurrents sous PostgreSQL : conserver
  le filtre de consommation sur la ligne mise à jour. Test avec deux écritures
  effectivement bloquées sur le même code et reset concurrent ; aucun changement
  de schéma, de clés, de codes existants ou de configuration de déploiement.

- Canal PWA habituel réservé aux tags sans suffixe ; préversions construites et
  testées, promotion refusée. Publication manuelle de main conservée.
- PostgreSQL 17 retenu pour le futur serveur CHRS : profil de tests explicite,
  matrice CI, concurrence et dump/restauration fictifs. Aucun profil de
  déploiement modifié ; la première CI verte doit confirmer la qualification.
- Compléments AUD : Python constructeur PWA >=3.12 affiché séparément du
  Python embarqué ; documentation des contrats actualisée.

- #AUD : adoption de pas-communs 0.8.0 publiée, chemins ZIP portables dans les
  deux sens, contrôles de promotion partagés et contrat Pyodide explicite.
  Aucun changement du runtime, des formats de données ou des déploiements.
- #AUD : compatibilité Django annoncée cohérente avec la matrice ; lock 5.2
  et profils explicites conservés. Cadrage CHRS1 fictif mono-espace documenté.

## 0.2.0 — 2026-10-19

Première qualification de la chaîne complète avec Pas communs 0.7.0 :
programmes Linux/Windows, setup, PWA et export PDF. Prototype réservé
aux données fictives ; cette publication ne qualifie pas un usage réel.

- Releases GitHub et publication PWA automatiques sur tag qualifié ; reprise
  manuelle conservée et déploiements serveur séparés.

- Installateur graphique Windows partagé avec Petits Pas via pas-communs 0.7.0,
  contrôlé en CI et publié avec le ZIP portable, sans supprimer les données.

- Publication PWA alignée sur Petits Pas : configuration sur main et préparateur
  pris au commit source, sans ré-épinglage manuel.

- Versionnement aligné sur Petits Pas : tag exact ou dev.<sha8>, version
  embarquée générée et notes du changelog vérifiées lors des publications.

- Export de fiche personne PDF, natif et navigateur hors ligne ; moteur natif partagé avec Petits Pas via Pas communs 0.6.0.

- Socle partagé 0.5.0 : sauvegardes, authentification, programme local et PWA.
- Profils de démonstration éphémère et d'espace fictif persistant.
- Qualification des démarrages et publication explicite des programmes/PWA.

Données fictives uniquement. Les ménages, accompagnements et prestations ne
sont pas encore implémentés. L'exploitation avec des dossiers réels n'est pas qualifiée.

## 0.1.0

Premier prototype : création et consultation d'une personne fictive.

- #SOC CHRS11 : exploration chronologique filtrable de l'accompagnement,
  par bénéficiaire et dates d'effet, sans score ni nouveau stockage social ;
  droits de lecture distincts selon les catégories de faits.
