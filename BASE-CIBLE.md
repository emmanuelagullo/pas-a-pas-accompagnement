# Base serveur CHRS : cible retenue et qualification préalable

## État actuel et décision

Le prototype, le bureau et la PWA utilisent SQLite. Les profils serveur livrés
restent SQLite mono-processus ; le profil PostgreSQL ajouté est exclusivement réservé aux tests. Aucun réglage
ni dépendance d’un déploiement existant ne change.

**Cible retenue : PostgreSQL pour le futur serveur d'équipe**, SQLite
pour les programmes et PWA autonomes. Avant un modèle dépendant d'un comportement
concurrent particulier ou d'une contrainte propre à PostgreSQL, qualifier les
deux bases en CI. Les premières tables métier simples peuvent rester portables ;
ne pas écrire une règle dont l'unique garantie suppose déjà un backend non testé.
Le cadrage fictif mono-espace de V0-METIER.md ne choisit pas le backend serveur.

## Matrice de qualification livrée

| Contrôle | SQLite maintenue | PostgreSQL 17 |
| --- | --- | --- |
| Environnement | Profils et lock actuels ; SQLite fichier pour la concurrence | Service jetable postgres:17-alpine, Python 3.12/3.13, Django 5.2 et 6.1 |
| Dépendances | Profils serveur, PDF et 2FA explicites | Profil **requirements-tests-postgresql.txt distinct**, avec psycopg 3.3.6 épinglé ; aucune inclusion bureau/PWA |
| Réglages | Pas de changement du profil livré | Module de settings de tests uniquement, DB/host/port explicites, credentials fictifs CI et refus d'une base non CI |
| Migrations | Prototype existant et anciennes copies | Base vide puis migrations ; contrôle makemigrations ; scénarios de données fictives |
| Concurrence | Connexions distinctes, verrouillage occupé et refus propre | TransactionTestCase et connexions distinctes ; consommation TOTP/secours, reset concurrent, limites et transactions |
| Invariants métier futurs | Cas identiques, notamment dates et bénéficiaires | Mêmes cas ; insertions concurrentes sur unicité/chevauchement, contraintes et rollback réellement exercés |
| Sauvegarde | ZIP SQLite du produit, aller-retour et refus croisé | pg_dump puis pg_restore dans une seconde base jetable, intégrité, UUID, comptes et contraintes vérifiés |

Le job PostgreSQL doit bloquer l'adoption de modèles qui reposent sur ces
comportements. Une réussite SQLite ne qualifie pas select_for_update ; une
réussite PostgreSQL ne qualifie pas les modes locaux. Ne pas masquer une erreur
concurrente comme une validation réussie. Examiner les erreurs attendues et les
bornes de réessai dans les services du produit, sans déplacer les modèles dans
pas-communs. Le service PostgreSQL de Petits Pas est une recette à comparer,
non un résultat de qualification du CHRS.

Ordre : réussir la matrice PostgreSQL livrée → qualifier les garanties métier
futures dans les deux bases → adopter les modèles concernés. L'installation d'un serveur et ses sauvegardes opérationnelles
feront l'objet d'un cadrage d'exploitation distinct, annoncé avant tout réglage.

## Sauvegardes distinctes

- `pas_communs.paquets` et les commandes SOC2 manipulent un paquet **SQLite**,
  sa clé locale et ses médias. Ne pas les appeler sur un serveur PostgreSQL,
  ni remplacer un nom de base par une URL en supposant une conversion.
- Le futur serveur PostgreSQL devra sauvegarder sa base par pg_dump (format
  custom), puis restaurer dans une autre base par pg_restore avec arrêt sur
  erreur. Qualifier aussi la disponibilité des clés serveur et la cohérence
  des médias ; un dump SQL seul ne suffit pas à l'exploitation.
- Le paquet autonome et le dump PostgreSQL ne sont pas interchangeables.
  Un export futur serveur → local est une **projection applicative** avec choix
  des données, droits et secrets, pas une restauration automatique du moteur ZIP.
- Les bases, dumps et ZIP des essais restent fictifs et temporaires. Les
  sauvegardes réelles éventuelles restent privées et hors des artefacts publics.

## Exécuter la qualification

Le job `qualification-postgresql` utilise PostgreSQL 17 et le client 17 de
Debian trixie, pour conserver la même version majeure pour dump et restauration.
Il bloque la publication PWA avec les autres contrôles. Le script
`scripts/qualifier-postgresql.py` crée deux bases aux noms aléatoires, migre,
exécute les tests, compare les données après restauration et détruit uniquement
les bases qu’il a créées. Aucun dump n’est conservé comme artefact.

Pour un essai local facultatif, préparer un **service PostgreSQL 17 jetable**,
un rôle autorisé à créer des bases et pg_dump/pg_restore 17. Sous Guix, fournir
Python, Django, psycopg, PostgreSQL et les dépendances des profils explicites
avec l’environnement Guix habituel ; aucune installation pip n’est exécutée par
la recette. Les requirements décrivent les versions de la CI.

```sh
export ACCOMPAGNEMENT_PG_QUALIFICATION=oui
export PGHOST=127.0.0.1 PGPORT=5432 PGUSER=qualification
# Définir PGPASSWORD pour ce service fictif, hors historique de commandes.
python scripts/qualifier-postgresql.py
```

Les réglages `settings_tests_postgresql` refusent une activation implicite et
une base sans nom jetable conforme. Ils ne constituent pas un profil serveur.
La suite couvre les migrations historiques, les droits, TOTP/secours, un reset
concurrent, le plafond concurrent et l’unicité des comptes. Les futures règles
CHRS nécessiteront leurs propres tests ; cette matrice ne les anticipe pas.
Le dump de test ne qualifie ni les médias ni la gestion des clés d’un futur
serveur en exploitation. La qualification PostgreSQL doit être confirmée par
la première matrice CI verte avant de revendiquer ce support comme acquis.
