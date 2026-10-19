# Base serveur CHRS : proposition et qualification préalable

## État actuel et décision proposée

Le prototype, le bureau et la PWA utilisent SQLite. Les profils serveur livrés
restent SQLite mono-processus ; ce document n'active ni PostgreSQL, ni variable,
ni dépendance, ni migration, ni déploiement supplémentaire.

**Recommandation à valider : PostgreSQL pour le futur serveur d'équipe**, SQLite
pour les programmes et PWA autonomes. Avant un modèle dépendant d'un comportement
concurrent particulier ou d'une contrainte propre à PostgreSQL, qualifier les
deux bases en CI. Les premières tables métier simples peuvent rester portables ;
ne pas écrire une règle dont l'unique garantie suppose déjà un backend non testé.
Le cadrage fictif mono-espace de V0-METIER.md ne choisit pas le backend serveur.

## Petite matrice CI proposée avant adoption

| Contrôle | SQLite maintenue | PostgreSQL proposé |
| --- | --- | --- |
| Environnement | Profils et lock actuels ; SQLite fichier pour la concurrence | Service jetable postgres:16-alpine, Python 3.12/3.13, Django 5.2 et 6.1 |
| Dépendances | Profils serveur, PDF et 2FA explicites | Ajouter un profil **CI PostgreSQL distinct**, avec psycopg épinglé ; aucune inclusion bureau/PWA |
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

Ordre : décider du backend → ajouter le profil/dépendances CI et la matrice →
qualifier comptes, migrations et concurrence → seulement ensuite les garanties
métier concernées. L'installation d'un serveur et ses sauvegardes opérationnelles
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
