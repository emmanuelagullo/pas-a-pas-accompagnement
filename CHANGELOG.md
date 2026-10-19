# Historique

## À venir

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
