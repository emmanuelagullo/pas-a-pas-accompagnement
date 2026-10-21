# Pas à Pas — Accompagnement

Prototype **#SOC1–#SOC6c** pour préparer une application d'accueil et d'accompagnement
social, notamment en CHRS. **Données fictives uniquement ; développement local.**

Disponible : connexion, accueil, liste des personnes, création d'une identité
incomplète et consultation de sa fiche. Pas de modification ni suppression de
fiche à ce stade. Les comptes professionnels sont distincts des personnes suivies.

Non disponible : transports,
documents joints, invitations. Une PWA fictive est disponible sous #SOC5a ; voir ci-dessous. La date et l'auteur de création ne sont pas un journal
d'audit. Ce prototype n'est pas une installation de production.

## Démonstration métier

Le jeu fictif **Les Passerelles** est proposé sur le serveur jetable et,
dans un espace d’essai distinct de la PWA et des programmes Linux/Windows,
accessible même après la création de l’espace habituel.
Voir [le parcours et les accès](DEMONSTRATION.md).

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
synchronisation n'est présent. Les tentatives répétées sont limitées en base.
Le profil serveur peut proposer ou imposer le TOTP ; voir [AUTHENTIFICATION.md](AUTHENTIFICATION.md).

## Vérifications

```sh
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
git diff --check
```

La CI GitLab exécute ces contrôles sous Python 3.12 et 3.13, avec Django 5.2 et 6.1
et les dépendances TOTP. GitHub teste aussi le parcours serveur et les programmes. Elle nécessite un
runner Docker autorisé pour le futur projet. Les jobs de contrôle ne publient rien ; les jobs Pages et les promotions
de tags qualifiés ont leurs déclenchements propres (voir la section publication).
Les tests n'emploient que des identités fictives et une base de test temporaire.
La persistance réelle après redémarrage peut être exercée par le parcours ci-dessus.

`requirements.txt` décrit la plage de compatibilité ; `requirements.lock` fixe
l'environnement de ce jalon. Les mises à jour de dépendances sont explicites. La compatibilité déclarée
couvre Django 5.2 à <7 ; la matrice qualifie les branches 5.2 et 6.1 sous Python
3.12/3.13. Le lock conserve Django 5.2.18. Cela ne prétend pas tester chaque
version intermédiaire. Serveur, bureau, 2FA et PDF gardent leurs profils explicites.

La version pas-communs 0.8.0 est publiée et adoptée ; son wheel et son tag
restent immuables. Les mises à jour documentaires ne la republient pas. Les versions citées par les
sections #SOC ci-dessous sont celles d'introduction des mécanismes. La version
et l'empreinte effectives restent dans requirements-communs.txt. La recette
QUALIFICATION.md du socle s'utilise sans installation implicite, y compris
avec un environnement Guix ; elle vérifie les octets importés et les deux produits.

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
contiennent le programme à extraire entièrement. Le setup Windows
`PasAPasAccompagnement-Setup-<version>-x64.exe` propose aussi un assistant en
français, un raccourci et une désinstallation préservant les données.

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

## Parcours renforcé CHRS (#SOC4b)

Le profil serveur d’essai propose l’activation TOTP depuis **Sécurité du compte**,
la connexion en deux étapes, les codes de secours, le remplacement du téléphone
et le changement de mot de passe. Le déployeur peut imposer le 2FA à tous les
comptes de cet espace fictif ; aucun rôle CHRS n’est déduit des fonctions scolaires.

Lire [AUTHENTIFICATION.md](AUTHENTIFICATION.md) avant d’activer le profil :
dépendances facultatives, clé dédiée, récupération technique et révocation.
Le programme autonome reste sans activation TOTP. Un compte déjà protégé n’y
est jamais déprotégé silencieusement ; sa reprise exige la procédure explicite.

Cette étape ajoute une migration identites/0002, sans changer AUTH_USER_MODEL
ni les comptes ou fiches existants. Le lanceur protège la base avant migration.
Fermer le programme avant une maintenance ou une copie manuelle.

Les tests serveur installent requirements-2fa.txt et exercent les parcours,
les consommations concurrentes et la migration depuis #SOC4a. Le banc
`python scripts/verifier-authentification.py` teste aussi un serveur HTTP réel
sur une base temporaire et une clé éphémère. Les CI n’y publient aucun service.
Le profil de déploiement réseau, HTTPS et l’exploitation restent #SOC6.
Le prototype reste réservé aux données fictives.

## Premier essai navigateur (#SOC5a)

Voir [pwa/README.md](pwa/README.md) pour construire et essayer le parcours
local hors connexion. Les mêmes vues Django utilisent les primitives PWA de
Pas communs 0.4.0. Identité et stockage sont propres au CHRS. Aucun compte ni
modèle scolaire n'est importé. #SOC5b ajoute sauvegarde, vérification, annulation,
restauration confirmée et export de l'état précédent ; le prototype reste
exclusivement fictif. La qualification du moteur PWA est automatisée sous
Chromium/Linux ; les autres navigateurs et appareils restent à qualifier.

### Développement Guix sans pip

Les dépendances peuvent venir de l'environnement Guix habituel. Fournir le
chemin des sources du socle dans le terminal courant, par exemple avec les
dépôts imbriqués :

```sh
export PYTHONPATH="$(realpath ../../pas-communs/pas-communs/src)${PYTHONPATH:+:$PYTHONPATH}"
python3 -c 'import pas_communs; print(pas_communs.__file__)'
```

Cela ne remplace pas le wheel épinglé pour une distribution. Pour les commandes
SOC2, choisir des chemins réels dont le dossier parent existe, hors données :
`mkdir -p "$HOME/sauvegardes-pas-a-pas"`. Le dossier de restauration doit être
nouveau ; ne pas le désigner comme espace courant avant `restaurer_copie`.

## Profil serveur volontaire (#SOC6a)

Voir [SERVEUR.md](SERVEUR.md). Pas communs 0.5.0 fournit le contrat HTTPS partagé
avec le profil volontaire Petits Pas. Le serveur d'essai reste fictif, avec
SQLite mono-processus, clé stable, statiques WhiteNoise, HTTPS et configuration
explicite. Le profil de développement, le bureau et la PWA restent inchangés.

## Recettes CI et candidats (#SOC6b)

La recette commune est utilisable sans pip avec le PYTHONPATH Guix habituel :

    python3 -m pas_communs.ci django --controle scripts/verifier-profil-serveur.py --controle scripts/verifier-authentification.py

Le banc serveur requiert Gunicorn (déjà présent dans le profil Guix décrit).
Les CI ajoutent explicitement --pip-check ; aucune installation n'est cachée
dans le lanceur. Les contrôles gardent leurs espaces fictifs temporaires.
Les artefacts de programmes et la PWA normale reçoivent un manifeste propre
au CHRS : lire CI-PUBLICATION.md. La publication suit désormais SOC6c : automatique sur tag qualifié,
avec reprise manuelle ; la publication PWA de main reste manuelle.


## Déployer et publier les essais (#SOC6c)

Lire [DEPLOIEMENTS.md](DEPLOIEMENTS.md) : démarrages jetable/persistant,
bancs réels de déploiement, programmes publiables depuis un tag et PWA vers
un projet Pages dédié. La page d'accès PWA contient les limites et le lien vers
les releases publiques. Les destinations doivent être créées/configurées avant
activation ; aucun déploiement distant n'est effectué par cette livraison.
Le tag Git définit la version applicative, indépendamment du socle ; les
branches portent `dev.<sha8>`. Voir DEPLOIEMENTS.md pour préparer le changelog
et promouvoir les artefacts validés sans reconstruction.

## Télécharger la fiche PDF (#SOC7b)

Depuis la fiche d'une personne : **Télécharger la fiche PDF**. Le document
reprend l'identité disponible, l'UUID et les dates, avec les mêmes droits de
lecture que la fiche. Il n'ajoute ni accompagnement ni information sociale.
Le téléchargement fonctionne aussi hors ligne dans la PWA.

Le serveur et le programme emploient WeasyPrint/Pango via pas-communs 0.6.0 ;
voir requirements-pdf.txt. Dans l'environnement Guix habituel, conserver
weasyprint (et ses bibliothèques) ; aucune installation pip locale imposée.
Le programme Windows embarque les DLL Pango sélectionnées par le .spec.
La PWA emploie un PDF texte avec police DejaVu Sans intégrée ; la présentation
peut différer du rendu natif. Un caractère absent de la police est signalé,
jamais remplacé silencieusement. Tous les éléments nécessaires sont embarqués,
sans appel à un serveur de conversion. Voir PDF.md pour les contrats et essais.

## Site public et projets Pages

Le site Hugo est dans site/ ; lire [site/README.md](site/README.md). Sa publication
GitLab Pages est indépendante de la PWA : le projet à la racine du domaine ne
contient qu'une redirection vers le site du dépôt applicatif. Les trois projets
emploient les mêmes runners Inria et l'arborescence de Petits Pas. Les jobs
Pages automatiques publient le site ; publier-pwa est automatique sur tag
numérique et reste manuel sur main. Les releases GitHub suivent automatiquement
les constructions de tag réussies ; les déploiements serveur restent séparés.

## Installateur Windows partagé (#SOC3b)

Après construction Windows, installer Inno Setup puis lancer :

```powershell
python -m pas_communs.installateur_windows --configuration scripts/installateur-windows.json
```

La CI Windows construit le setup et teste installation, contrôle du programme,
réinstallation et désinstallation. Les données sont séparées du programme et
conservées ; WebView2 reste nécessaire pour la fenêtre. Le ZIP portable reste
disponible. L’essai interactif du setup reste à faire sur les postes cibles.
Cette adoption nécessite la publication préalable de pas-communs 0.7.0.


## Base cible du serveur d'équipe

SQLite reste le backend des profils livrés. [BASE-CIBLE.md](BASE-CIBLE.md)
retient PostgreSQL pour le futur serveur, avec une matrice CI avant toute
règle métier dépendant de ses contraintes ou de sa concurrence. Ce choix
est cadré ; aucun déploiement ni profil d'exploitation n'est modifié.
Les sauvegardes PostgreSQL ne sont pas les paquets SQLite du bureau/PWA.

## CHRS1 — ménages et accompagnements fictifs

Disponible : ménage seul ou composé, appartenances datées, accompagnement sans
hébergement avec bénéficiaires explicites, clôtures et journal des opérations.
Un seul espace et un service d’essai ; tous les comptes autorisés voient les mêmes
objets. Aucun cloisonnement entre établissements n’est revendiqué.

Après migration, attribuer volontairement les droits du parcours à un compte existant :

```sh
python manage.py autoriser_chrs1 nom-utilisateur
```

Cette commande technique ajoute les droits CHRS1 sans superutilisateur. Aucun
compte existant ne reçoit de droit par migration ; le premier compte local garde
son profil de création/lecture des personnes. L’attribution reste hors interface
web dans cette tranche. Ouvrir « Ménages et accompagnements », créer un ménage
avec une personne existante, puis ouvrir et clôturer un accompagnement.

Les périodes ont un début inclus et une fin exclue. Les bénéficiaires enregistrés
ne changent pas lorsque les appartenances sont closes. Plusieurs ménages ou
accompagnements simultanés sont possibles. Les bénéficiaires peuvent être choisis
explicitement parmi les personnes de l’espace, indépendamment des appartenances.
Pas de suppression ni réouverture ; CHRS7 ajoute des corrections datées avec historique.
Le journal conserve les opérations et leur acteur, sans recopier les identités.

Vérification de reprise historique et aller-retour des relations CHRS1 :

```sh
python scripts/verifier-chrs1-reprise.py
```

## CHRS2 — repas accordés et distribués

Après migration, l’attribution reste explicite :

```sh
python manage.py autoriser_chrs2 nom-utilisateur
```

Cette commande ajoute CHRS1 et CHRS2 au compte désigné ; aucune migration ne
modifie les droits. Depuis un accompagnement, choisir « Accorder des repas » :
bénéficiaires parmi ceux du suivi, service (petit déjeuner, déjeuner, dîner),
période début inclus / fin exclue et prestataire facultatif, y compris extérieur.
L’accord couvre chaque jour de la période ; CHRS7 ajoute des corrections de dates motivées.
Pas de plafond global ni de calendrier hebdomadaire dans cette V0.

Ouvrir l’accord pour enregistrer les repas effectivement distribués : personne,
date et quantité entière positive. Une distribution future, hors accord ou hors
accompagnement est refusée. Une seule ligne active par accord/personne/jour ;
la contrainte SQL protège aussi les insertions concurrentes. Des accords distincts
peuvent se chevaucher : pas de dédoublonnage entre accords dans cette tranche.
Le total exclut les lignes annulées. Une correction consiste à annuler avec motif
puis saisir une nouvelle ligne ; rien n’est effacé. Le journal distingue date
d’effet et enregistrement, avec auteur. Aucun repas n’est généré depuis l’accord.

L’orientation 115/SIAO reste à porter par un futur objet dédié au suivi ; aucun
champ dupliqué sur les repas ni synchronisation externe n’est ajouté ici.
Clôturer un accompagnement ne modifie pas l’accord historique, mais interdit les
réalisations après sa fin. La clôture est refusée si elle exclut des distributions
actives déjà saisies. Les corrections rétrospectives restent possibles.

## CHRS3 — hébergement accordé, séjours et affectations

```sh
python manage.py migrate
python manage.py autoriser_chrs3 nom-utilisateur
```

L’attribution ajoute CHRS1 et CHRS3 uniquement, sans retirer les droits CHRS2
éventuels. Aucun droit n’est attribué à la migration. Depuis un accompagnement,
accorder un hébergement à des bénéficiaires explicites ; ouvrir l’accord puis
saisir l’admission effective. Créer un lieu (chambre, appartement, hôtel, etc.),
avec opérateur extérieur facultatif, puis ajouter une affectation au séjour.
Le lien « Changer de lieu » ferme l’affectation ouverte et ouvre la suivante
à la même date dans une transaction unique. Un conflit ou formulaire périmé
ne laisse pas de clôture partielle. La période du séjour reste inchangée.

Les périodes utilisent des dates civiles, début inclus et fin exclue : une
période du 3 au 5 correspond aux nuits débutant les 3 et 4. La présence réelle
n’est pas déduite de cette seule période : les absences sont enregistrées à
part. Pas d’heures ni d’accueil entrée/sortie le même jour dans cette tranche.
Affectations et absences concernent tous les bénéficiaires du séjour. Pour des
parcours individuels distincts, créer des séjours distincts avec les personnes
concernées. Les bénéficiaires ne sont pas recalculés depuis le ménage courant.

Une absence laisse le séjour et l’affectation ouverts. La sortie clôture les
périodes ouvertes à sa date, dans la même transaction et avec audit ; une
période déjà enregistrée au-delà entraîne un refus, sans modification partielle.
La clôture de l’accompagnement exige d’abord la clôture des séjours. Admission
et périodes effectives ne peuvent commencer dans le futur ; une fin effective
ne peut être future ni dépasser le séjour ou l’accompagnement. Les mouvements
et la sortie d’un séjour déjà admis peuvent dépasser la fin de l’accord ;
un avertissement signale ce dépassement sans modifier l’autorisation.
L’admission reste comprise dans l’accord, y compris lors d’une correction.
Un séjour ouvert sous accord borné ne constitue pas une prolongation de droit.

Les affectations d’un même séjour ne peuvent se chevaucher ; même règle pour
ses absences. Les écritures sont sérialisées par séjour sur SQLite/PostgreSQL ;
un conflit de stockage web est refusé, avec demande de recharger avant réessai.
Absence et affectation peuvent se chevaucher : la place reste attribuée.
Pas de contrôle global des capacités ni des doubles occupations entre séjours,
pas de réservation, tarification ou calcul automatique des nuitées facturables.
CHRS7 permet de corriger les dates des séjours avec motif et historique.
Aucune suppression ni réouverture silencieuse n’est proposée.

## CHRS4 — situation et parcours sociaux

Pour appliquer ensemble les quatre patches CHRS dans leur ordre : exécuter les
migrations une seule fois, puis attribuer volontairement tous les droits du
parcours fictif au compte voulu :

```sh
python manage.py migrate
python manage.py autoriser_chrs4 nom-utilisateur
```

Il n’est pas nécessaire d’appeler autoriser_chrs1, autoriser_chrs2 et
autoriser_chrs3 auparavant. Cette attribution est cumulative et idempotente,
sans droit de suppression ni superutilisateur. Les comptes existants ne
reçoivent toujours aucun droit automatiquement à la migration.

Depuis un accompagnement, ouvrir « Situation et parcours sociaux ». Trois
dimensions simples : logement, emploi/formation et ressources déclarées, sans
montants ni dossier médical. Les valeurs sont propres à un bénéficiaire et à
cet accompagnement ; pas de dossier social partagé entre services. Une valeur
« Non renseigné » reste distincte de « sans emploi » ou « sans ressources ».
Une absence de ligne ne signifie pas que la personne n’a aucune difficulté.

Renseigner une dimension avec sa date d’effet et la source de l’information.
Une nouvelle valeur ferme la précédente à sa date d’effet (fin exclue). Les
ajouts sont chronologiques par personne/dimension ; la consultation sélectionne
les valeurs valables à la date demandée. On ne rejoue pas les événements.
Pour une erreur de valeur, « Corriger » conserve dates et source, mais enregistre
ancienne/nouvelle valeur, motif, auteur et horodatage dans le journal. CHRS7 ajoute la correction des dates et sources ; le bénéficiaire ne change pas.

Événements significatifs par personne (500 caractères maximum) et bilans du
suivi (2 000 caractères maximum) sont saisis séparément, sans modifier les
valeurs sociales. CHRS7 ajoute leur correction tracée, sans suppression. Leur chronologie utilise les dates d’effet ; date de saisie et auteur
restent visibles. Les repas et séjours apparaissent si les droits le permettent.
La consultation datée présente la situation telle que corrigée aujourd’hui,
pas une reconstitution de ce que l’équipe savait dans le passé.

Dates d’effet non futures et comprises dans l’accompagnement, fin exclue. Une
clôture qui exclurait une information sociale datée est refusée. La dernière
valeur reste la dernière information connue ; hors période d’accompagnement,
aucune situation courante n’est affirmée. Les bilans et événements de fin de
suivi doivent être datés du dernier jour inclus, pas de la borne de fin exclue.
Les écritures sociales et la clôture sont sérialisées par accompagnement ; un
conflit de stockage web est refusé et demande de recharger avant réessai.

## Copies du programme et échanges PWA/Linux/Windows (#SOC)

Avec le nouveau programme, ouvrir **Copies et restauration sur cet appareil**,
y compris avant de créer un premier compte. Comme les outils de la coque PWA
et les commandes de maintenance, cette page technique est réservée au propriétaire
de l'appareil fictif ; elle ne crée pas de rôle professionnel ni de droit web
serveur. Elle n'est exposée ni en serveur ni dans les vues Django PWA.

Télécharger une sauvegarde, puis conserver le ZIP privé hors appareil. Pour
restaurer : choisir le ZIP du même produit, vérifier date et nombre de médias,
puis annuler ou confirmer. Après confirmation, les écritures sont bloquées.
**Appliquer la restauration et redémarrer** ferme le serveur et ses connexions
avant remplacement ; sinon fermer le programme puis le relancer. Le dossier
précédent est conservé et son chemin apparaît à la réouverture. En mode
`--sans-fenetre`, arrêter avec Ctrl+C après confirmation puis relancer.
Une préparation non confirmée est supprimée à la fermeture sans remplacement.

Les mêmes ZIP conservent les comptes, UUID, relations et médias entre PWA,
Linux et Windows. Les sessions et compteurs sont supprimés de la copie restaurée,
les facteurs TOTP restent bloquants en local et les clés TOTP serveur externes
ne sont jamais ajoutées au ZIP. Les commandes conservent leur contrat de nouveau
dossier seulement. Les limites PWA restent plus basses que celles des programmes :
ZIP et contenu décompressé 64 Mio, 5 000 entrées, clé 64 Kio. Pas de chiffrement
ni synchronisation. Un ZIP privé complet n'est pas un jeu public de démonstration.
Cette adoption de pas-communs 0.9.0 doit attendre sa publication immuable.

## CHRS5 — navigation contextuelle

La fiche personne donne accès à ses ménages et accompagnements selon les droits.
La fiche d’accompagnement regroupe bénéficiaires, accords de repas, hébergement
et suivi social. Après une saisie, le retour reste dans la rubrique concernée.
Les anciens liens et routes restent disponibles ; aucune migration ni nouveau
droit n’est nécessaire.

## CHRS6 — travail du jour

Le menu Travail du jour regroupe les séjours, lieux et absences enregistrés à la
date choisie, selon les droits. Les accords expirés avec séjour ouvert sont
signalés sans déduire une présence physique. Les repas actifs peuvent être saisis
par lot (500 lignes maximum) : renseigner seulement les distributions réalisées.
Case vide : aucune écriture ; doublon, ligne invalide ou conflit : lot refusé.
Aucune date future n’est acceptée pour une distribution. Les corrections restent
accessibles depuis l’accord. Aucun nouveau droit ni migration pour cette tranche.

## CHRS7 — corrections tracées

```sh
python manage.py migrate
python manage.py autoriser_chrs7 nom-utilisateur
```

Cette commande attribue explicitement CHRS1–7, sans administration ou suppression.
Aucun compte existant ne reçoit ces nouveaux droits à la migration ; les jeux
fictifs nouvellement générés les attribuent. Les jeux existants ne sont pas reset.

Les liens Corriger permettent de rectifier les dates d’un accompagnement, d’une
appartenance, d’un accord, d’un séjour, d’une affectation ou d’une absence. Une
situation sociale permet aussi de corriger sa date/source, entre ses voisines,
sans réordonner la série ; la borne de la valeur précédente suit la date corrigée.
Les événements et bilans autorisent une correction du texte et de sa date/source.
Un motif est requis. Les dates, sources et textes avant/après restent dans deux
journaux typés avec auteur et horodatage. Un formulaire périmé ou dont la cible
a été modifiée entre-temps est refusé. Les opérations initiales restent intactes.

La validation refuse les réalisations exclues, les chevauchements et dates
incompatibles. Aucun déplacement automatique des repas ou périodes dépendantes.
La correction ne rouvre ni ne clôture une période ; utiliser les clôtures dédiées.
Les bénéficiaires, identités, liens familiaux et lieux attribués ne sont pas
modifiés par ce formulaire. Pour les repas distribués, annuler puis ressaisir.
Les mécanismes restent applicatifs ; ni socle ni profils de déploiement modifiés.

Le banc navigateur scripts/verifier-pwa.cjs exerce aussi la fiche d’accompagnement,
une correction avec avant/après et une distribution du jour via le vrai Worker
Pyodide (scripts/verifier-parcours-metier.cjs). Sa réussite reste à confirmer
dans la CI du candidat ; elle ne se déduit pas des tests Django.

## CHRS26 — recherche et continuité de navigation

Les listes permettent de rechercher les personnes par nom, prénom ou désignation,
et les ménages par libellé ou par nom d’un membre actuel ou ancien. Les mots
saisis sont tous recherchés, sans distinction de casse ; les accents restent
ceux de la base utilisée. Les pages de 25 résultats conservent recherche et
contexte de rattachement. Depuis le travail du jour, affectation, absence et
sortie reviennent à la date consultée ; aucune URL de retour libre n’est acceptée.
Le retour d’absence utilise la clôture existante, avec les mêmes règles de dates.
