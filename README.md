# Pas à Pas — Accompagnement

Prototype **#SOC1–#SOC3** pour préparer une application d'accueil et d'accompagnement
social, notamment en CHRS. **Données fictives uniquement ; développement local.**

Disponible : connexion, accueil, liste des personnes, création d'une identité
incomplète et consultation de sa fiche. Pas de modification ni suppression de
fiche à ce stade. Les comptes professionnels sont distincts des personnes suivies.

Non disponible : ménages, accompagnements, prestations, séjour, situation sociale,
historique des modifications, documents, invitations, TOTP,
PWA et installateur graphique Windows. La date et l'auteur de création ne sont pas un journal
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
Ne pas supprimer ce dossier pour mettre à jour le code. Les commandes de
sauvegarde et copie indépendante sont décrites ci-dessous. Ne pas exposer le serveur
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

Voir [ARCHITECTURE.md](ARCHITECTURE.md). Depuis #SOC2, ce projet
utilise `pas-communs` pour les sauvegardes ZIP/SQLite (#SOC2).
La version et l’empreinte sont fixées dans `requirements-communs.txt`.
Publier d’abord le wheel du socle avant de déployer cette dépendance.

Nom public : **Pas à Pas — Accompagnement**. Dépôt : `pas-a-pas-accompagnement`.
Configuration Django : `pas_a_pas_accompagnement`.
Référence : <https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement>.
Miroir : <https://github.com/emmanuelagullo/pas-a-pas-accompagnement>.

Code et documentation de ce nouveau projet : AGPL-3.0-or-later, voir LICENSE.

## Sauvegarder et vérifier une copie (#SOC2)

Ces commandes s'adressent à la personne qui exploite l'espace fictif local,
avec accès aux fichiers ; ce ne sont pas des permissions web supplémentaires.
Le ZIP contient toute la base, les comptes, la clé et les médias non chiffrés.
Choisir une destination privée hors du dossier de données. Pour le moment,
arrêter le serveur pendant ces opérations afin de garder les fichiers stables.

```sh
python manage.py sauvegarder_paquet /chemin/prive/copie.zip
python manage.py verifier_sauvegarde /chemin/prive/copie.zip
python manage.py restaurer_copie /chemin/prive/copie.zip /chemin/prive/copie-restauree
```

Les parents doivent exister. Aucun ZIP ni dossier existant n'est remplacé.
La restauration crée une copie indépendante ; l'espace courant reste intact.
Pour l'essayer après arrêt du serveur (Linux/bash) :

```sh
ACCOMPAGNEMENT_DONNEES=/chemin/prive/copie-restauree python manage.py migrate
ACCOMPAGNEMENT_DONNEES=/chemin/prive/copie-restauree python manage.py runserver 127.0.0.1:8001
```

Sous PowerShell, définir d'abord `$env:ACCOMPAGNEMENT_DONNEES` vers ce dossier,
puis lancer les commandes `migrate` et `runserver` ; retirer la variable avec
`Remove-Item Env:ACCOMPAGNEMENT_DONNEES` pour revenir à l'espace habituel.
La copie conserve les comptes et mots de passe ; les sessions ont été retirées
pour imposer une reconnexion. La compatibilité des migrations est vérifiée
avant installation de la copie. Une archive Petits Pas est refusée.

Ces procédures ne constituent pas une validation du produit pour des données
réelles ni un remplacement du futur lanceur et des habilitations métier.


## Programme local (#SOC3)

Installer les dépendances de `requirements-bureau.txt` dans un environnement
Python qui dispose du moteur graphique. Sous Windows : WebView2 doit être
présent. Sous Linux : PyGObject, GTK et WebKitGTK 4.1 ; un venv créé avec
`--system-site-packages` peut voir les paquets du système ou du shell Guix.

```sh
python -m pip install -r requirements-bureau.txt
python scripts/lancer-local.py
```

Le premier démarrage propose **Préparer mon espace d’essai** : choisir son nom
d'utilisateur et un mot de passe, sans compte prédéfini. Le compte créé est
ordinaire et peut lire/créer les personnes fictives. Les ouvertures suivantes
retrouvent les comptes existants et ne proposent plus cette installation.

Le programme utilise un dossier séparé du code et de Petits Pas :

- Linux : `${XDG_DATA_HOME:-~/.local/share}/pas-a-pas-accompagnement/paquet-autonome` ;
- Windows : `%LOCALAPPDATA%\pas-a-pas-accompagnement\paquet-autonome`.

`--paquet CHEMIN` ou `ACCOMPAGNEMENT_DONNEES` sélectionne un autre dossier.
Si l'ancien espace `.local` de #SOC1 est détecté et que le nouvel emplacement
est vide, le lanceur refuse de créer silencieusement un espace neuf. Fermer
le serveur de développement puis choisir explicitement cet ancien espace :

```sh
python scripts/lancer-local.py --paquet .local
# Ou copier vers un nouveau dossier extérieur au dépôt et à .local :
python scripts/lancer-local.py --paquet .local --copier-paquet /chemin/prive/paquet-autonome
```

La copie conserve la source ; elle n'est pas une synchronisation. Pour ouvrir
la copie, passer son chemin à `--paquet`. Ne pas travailler alternativement sur
deux copies en pensant qu'elles se mettent à jour ensemble.

Un verrou interdit deux programmes sur le même dossier. La commande de
sauvegarde CLI prend le même verrou : fermer le programme avant de la lancer,
puis définir `ACCOMPAGNEMENT_DONNEES` vers son dossier. Le serveur de développement
`manage.py runserver` n'utilise pas ce lanceur : ne pas l'ouvrir simultanément
sur le même dossier. Les copies avant migration sont techniques et ne remplacent
pas les ZIP complets conservés hors appareil.

Depuis les sources (ou l’exécutable Linux), `--sans-fenetre` affiche une adresse locale dans
le terminal ; l'ouvrir dans son navigateur, puis Ctrl+C pour fermer. Le port
est choisi automatiquement, sans collision avec le serveur Petits Pas sur 8000.
Ce mode vérifie le parcours HTTP, pas le moteur graphique.

## Construire Linux/Windows

Construire sur le système visé, avec les dépendances graphiques disponibles :

```sh
# Linux, dans le venv lié à GTK/WebKit :
bash scripts/construire-paquet-linux.sh
# Windows PowerShell :
powershell -ExecutionPolicy Bypass -File scripts/construire-paquet-windows.ps1
```

Les scripts emploient l'assembleur de Pas communs, puis l'exécutable construit
avec `--verifier-distribution`, avant d'archiver `dist/PasAPasAccompagnement/`.
Les données du premier compte et les bases d'essai ne sont pas embarquées.
Les artefacts `PasAPasAccompagnement-linux.tar.gz` ou `PasAPasAccompagnement-windows.zip`
contiennent le programme à extraire entièrement. Il n'y a pas encore de setup
Windows ni d'installation automatique dans le menu Démarrer.

Le workflow GitHub **Programmes locaux Pas à Pas** teste et construit sur
Ubuntu 24.04 et Windows ; il fournit des artefacts temporaires, sans créer
une release. Le programme lui-même ne nécessite pas Python sur le poste cible.
La version Linux dépend encore de GTK/WebKit du système ; elle n'est pas un
AppImage universel. Les limites fictives du prototype restent inchangées.

## Première adoption de l’authentification commune (#SOC4a)

Pas communs 0.3.0 fournit le plafond des mots de passe (1 024 caractères),
contrôlé avant le hachage à la connexion et par les validateurs de création.
Le backend Django standard et les sessions existantes sont conservés.
Les cookies de session et CSRF portent des noms propres au produit, y compris
avec runserver. Une session source utilisant l’ancien nom de cookie doit se
reconnecter une fois ; les comptes et mots de passe ne changent pas.
Les sessions du programme #SOC3 conservent leurs noms de cookie.

Pour fermer les sessions Django en base d’un compte fictif depuis le terminal :

```sh
python manage.py fermer_sessions_compte nom-utilisateur
```

Cette commande technique ne modifie aucun droit et ne réinitialise pas le mot
de passe. Elle ferme les sessions authentifiées existantes du seul compte choisi.
Les deux produits ne partagent ni compte, ni clé, ni cookie, ni base de sessions.
Les durées restent propres aux profils et aucun SSO n’est ajouté.

**Le parcours TOTP CHRS n’est pas encore disponible.** #SOC4b doit intégrer
l’inscription, le second facteur, les secours, la récupération et la limitation
des tentatives. #SOC4a ne rend pas ce prototype utilisable avec des dossiers réels.
