## À venir — copies locales communes

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
