# Pas à Pas — Accompagnement

Prototype **#SOC1** pour préparer une application d'accueil et d'accompagnement
social, notamment en CHRS. **Données fictives uniquement ; développement local.**

Disponible : connexion, accueil, liste des personnes, création d'une identité
incomplète et consultation de sa fiche. Pas de modification ni suppression de
fiche à ce stade. Les comptes professionnels sont distincts des personnes suivies.

Non disponible : ménages, accompagnements, prestations, séjour, situation sociale,
historique des modifications, documents, invitations, TOTP, sauvegardes,
programme autonome et PWA. La date et l'auteur de création ne sont pas un journal
d'audit. Ce prototype n'est pas une installation de production.

## Essayer depuis les sources

Python 3.12 ou 3.13 recommandé. Aucun PostgreSQL, Node ou module Petits Pas requis.
Depuis ce dépôt :

```sh
python3 -m venv .venv
# Linux :
. .venv/bin/activate
# Windows PowerShell, à la place : .venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
python manage.py migrate
python manage.py creer_compte_essai essai
python manage.py runserver 127.0.0.1:8000
```

Choisir un mot de passe d'au moins 12 caractères lorsque la commande le demande.
Il n'est ni passé en argument ni affiché. Le compte créé est ordinaire, sans
superpouvoir ni accès à une console d'administration : ses seules permissions
sont consultation et création des personnes fictives. Une nouvelle exécution
sur le même identifiant est refusée et ne modifie pas le compte existant.

Ouvrir <http://127.0.0.1:8000/>, se connecter, puis **Consulter les personnes →
Créer une personne**. Par exemple, nom d'usage `Personne fictive A`, prénom vide.
Enregistrer, consulter la fiche, revenir à la liste, arrêter puis relancer la
commande `runserver` : la fiche est toujours présente. Deux personnes peuvent
avoir la même désignation ; leurs UUID sont distincts et stables.

Les données SQLite et la clé de session sont dans `.local/`, ignoré par Git.
Ne pas supprimer ce dossier pour mettre à jour le code. Ce jalon ne comporte
pas encore de procédure de sauvegarde/restauration. Ne pas exposer le serveur
de développement sur un réseau ou y saisir des informations réelles.

Le contrôle <http://127.0.0.1:8000/health/> vérifie le processus et une requête
SQL, sans révéler les données. Il ne certifie ni les migrations ni les sauvegardes.

## Droits et limites

La connexion seule ne donne aucun accès aux personnes. Les vues contrôlent les
permissions Django `personnes.view_personne` et `personnes.add_personne` ; la
création exige aussi la lecture pour pouvoir consulter la fiche résultante.
Les écritures utilisent POST et CSRF ; la déconnexion utilise POST.

Un espace fictif unique, sans organisations ni équipes : tous les comptes ayant
le droit de consultation y voient toutes les fiches. Les rôles CHRS et l'isolation
entre structures sont à décider avant leur implémentation. Aucun mécanisme de
synchronisation n'est présent. La protection contre les tentatives répétées et
le second facteur de Petits Pas ne sont pas encore portés dans ce prototype.

## Vérifications

```sh
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
git diff --check
```

La CI GitLab exécute ces contrôles sous Python 3.12 et 3.13. Elle nécessite un
runner Docker autorisé pour le futur projet. Le fichier CI ne publie rien.
Les tests n'emploient que des identités fictives et une base de test temporaire.
La persistance réelle après redémarrage peut être exercée par le parcours ci-dessus.

`requirements.txt` décrit la plage de compatibilité ; `requirements.lock` fixe
l'environnement de ce jalon. Les mises à jour de dépendances sont explicites.

## Socle commun avec Petits Pas

Voir [ARCHITECTURE.md](ARCHITECTURE.md). Pour #SOC1, ce projet est indépendant et
n'importe encore aucun paquet du futur socle. La première extraction sera le
moteur des paquets/sauvegardes (#SOC2), avec adoption par les deux applications.

Nom public : **Pas à Pas — Accompagnement**. Dépôt : `pas-a-pas-accompagnement`.
Configuration Django : `pas_a_pas_accompagnement`. Aucune URL distante n'est
supposée ; les dépôts de forge ne sont pas encore créés.

Code et documentation de ce nouveau projet : AGPL-3.0-or-later, voir LICENSE.
