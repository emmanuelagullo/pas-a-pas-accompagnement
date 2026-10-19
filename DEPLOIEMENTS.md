# Déployer et publier les essais fictifs — #SOC6c

## Ce qui est livré

| Canal | Construction / contrôle | Activation |
| --- | --- | --- |
| Démonstration serveur | start-render.sh, espace SQLite neuf, clé neuve, compte public essai et fiche fictive ; banc de redémarrage HTTP | Créer un service web ; hôte et HTTPS automatiques sur Render |
| Espace fictif persistant | start-persistent.sh, SQLite mono-processus, sauvegarde avant migration, aucun compte automatique ; banc de persistance/restauration | Dossier privé persistant, arrêt du service, variables et premier compte explicites |
| PWA | Même job GitLab : vrais Pyodide/Chromium, racine et préfixe, bundle normal puis manifeste | Projet Pages distinct et job publier-pwa manuel |
| Programmes | GitHub Windows/Linux, tests, construction, version embarquée et manifestes | Workflow manuel publier-programmes ou CLI gh depuis une construction du tag réussie |

Aucun hébergement, projet, secret, tag ou release n'est créé par cette livraison.
Aucun changement de pas-communs : la dépendance reste 0.5.0 et son empreinte
reste celle de SOC6b. Aucune modification de Petits Pas nécessaire. La structure
suit ses profils et promotions, avec les adaptateurs du produit CHRS.

## Ordre de mise en route

1. Appliquer SOC6c après SOC6b, SOC7a, le correctif des tags Inria et le
   correctif UTF-8 Windows. Pousser et attendre les CI.
2. Créer le service de démonstration si souhaité. Le tester publiquement sur
   des données fictives ; sa disponibilité n'est pas requise pour les CI.
3. Créer le projet Pages, épingler sa configuration et activer publier-pwa.
4. Choisir la prochaine version applicative disponible, indépendante du socle.
   Renommer la rubrique `## À venir` de CHANGELOG.md en `## X.Y.Z — AAAA-MM-JJ`,
   conserver ses notes et ajouter une nouvelle rubrique vide `## À venir`.
   Commiter puis attendre les CI de ce commit avant de le taguer.
5. Pousser le même tag applicatif sur les deux forges. Attendre les builds,
   publier les programmes et la PWA séparément. Ne pas déplacer un tag publié.

La version inscrite dans le binaire est embarquée dans l'archive et contrôlée
par la CI. --version la restitue aussi depuis les sources. Le bundle PWA porte
commit/tag/application_version et sa version de cache propre. Les empreintes
et manifestes ne constituent pas une signature cryptographique de provenance.

## Démonstration Render (ou autre hébergement compatible)

Créer un service web Python depuis le dépôt ou son miroir, branche main.
Les commandes suivantes supposent Python 3.12+ et Git, avec Gunicorn disponible :

- Construction hébergée : `python -m pip install -r requirements-serveur.txt`.
- Démarrage : `bash start-render.sh`.
- Contrôle de santé : `/health/`.
Sur Render, **aucune variable applicative HTTPS n'est nécessaire** : le script
reprend RENDER_EXTERNAL_HOSTNAME, fourni par la plateforme, pour l'hôte exact,
l'origine HTTPS et la confiance au proxy Render. Le domaine n'est pas inscrit
dans le code ; un renommage du service suit automatiquement cette valeur.

Pour un domaine personnalisé, les variables explicites restent prioritaires :
ACCOMPAGNEMENT_HOSTS (noms exacts séparés par des virgules),
ACCOMPAGNEMENT_CSRF_ORIGINS (origines HTTPS), ACCOMPAGNEMENT_PROXY_HTTPS
(oui/non). Sans origine explicite, le script déduit les origines HTTPS de la
liste effective des hôtes. Hors Render, sans RENDER_EXTERNAL_HOSTNAME, ces
choix restent explicites ; le profil serveur générique ne change pas.

Le service utilise PORT si fourni, sinon 8000. Ne configurer ni
ACCOMPAGNEMENT_DONNEES, ni DATABASE_URL, ni ACCOMPAGNEMENT_STATIC_ROOT, ni clés
TOTP. Chaque démarrage choisit un dossier mktemp neuf ; aucun dossier existant
n'est supprimé. Le volume temporaire de l'hébergeur reste responsable de la
purge des anciens dossiers. Ne pas utiliser ce profil sur un volume durable
sans prévoir cette purge. Aucune commande ne réinitialise une base arbitraire.

La connexion affiche **essai / Demonstration-fictive-2026!** : ce sont des
identifiants publics donnant uniquement lecture/création de fiches fictives.
La démonstration est partagée, visible par les autres visiteurs et jetable.
Les écrans de modification du compte public sont bloqués côté serveur pour
qu’un visiteur ne change pas le mot de passe utilisé par les suivants.
Aucun compte de direction ou d'administration n'est créé. Pas d'inscription
libre ni d'envoi de courriel. La page rappelle de ne rien saisir de réel.

Après création, vérifier HTTPS, /health/, /connexion/, CSS, connexion publique,
création fictive, refus de /installer/ et disparition des essais après un
redémarrage. Qualifier les en-têtes du proxy et les limites d'authentification ;
la CI loopback ne qualifie pas le proxy ou certificat réel.

### Déclenchement manuel depuis GitLab

Optionnel : désactiver l'auto-déploiement de l'hébergeur si l'on souhaite que
seul le job manuel décide du moment. Configurer dans le projet source GitLab :

- DEMO_DEPLOY_HOOK : URL HTTPS secrète d'un hook acceptant POST, variable masquée
  et protégée ; ne jamais la mettre dans le dépôt, les logs ou une commande copiée.
- DEMO_HEALTH_URL : URL HTTPS publique exacte de /health/.

Le job deployer-demonstration n'apparaît que sur la branche principale avec ces
paramètres. Il déclenche le hook sans redirection et attend au plus dix minutes
le commit CI exact dans /health/. Le démarrage récupère la révision du checkout
Git réel. Si main a avancé entre-temps, le job peut refuser de confirmer le
nouveau service : contrôler le commit sur l'hébergeur, puis relancer le bon
pipeline. Le hook ne garantit pas un déploiement immuable du commit demandé.
Il ne fait ni retour arrière ni gestion de maintenance d'un service réel.

## Espace fictif persistant

Ce profil conserve le SQLite et la clé existants. Il reste mono-worker/thread.
Il ne fournit pas PostgreSQL/S3 : leur présence dans Petits Pas correspond à
ses besoins et n'est pas copiée sans décision du produit CHRS.

Dans l'environnement Guix habituel avec PYTHONPATH vers pas-communs, ou dans
un environnement installé par requirements-serveur.txt :

```sh
export ACCOMPAGNEMENT_DONNEES="$HOME/donnees-pas-a-pas-fictif"
export ACCOMPAGNEMENT_SAUVEGARDES="$HOME/sauvegardes-pas-a-pas-fictif"
export ACCOMPAGNEMENT_HOSTS="NOM_PUBLIC_A_CONFIGURER"
export ACCOMPAGNEMENT_CSRF_ORIGINS="https://NOM_PUBLIC_A_CONFIGURER"
# Après arrêt effectif de l'ancien service et uniquement derrière le proxy configuré :
export ACCOMPAGNEMENT_MAINTENANCE=oui
export ACCOMPAGNEMENT_PROXY_HTTPS=oui
bash start-persistent.sh
```

Les chemins sont absolus, canoniques, hors code ; les sauvegardes sont aussi
hors données. Aucun redémarrage automatique du service n'est installé. Le
marqueur MAINTENANCE est une déclaration de l'exploitant, pas un arrêt à distance.
Ne pas lancer deux serveurs sur le même dossier. La clé d'une base existante
ne doit pas être régénérée. Les copies avant démarrage sont privées mais non
chiffrées, conservées sans purge automatique ; prévoir surveillance et copie
hors hébergement. La sauvegarde d'un espace déjà arrêté précède les migrations.

Après première initialisation vide, arrêter le processus, garder les variables
et créer un compte au terminal :

```sh
export DJANGO_SETTINGS_MODULE=pas_a_pas_accompagnement.settings_serveur
python3 manage.py creer_compte_essai essai-prive
```

Relancer le script : le compte et les fiches restent présents. Pour restaurer,
arrêter le service, utiliser les commandes SOC2 vers un **nouveau** dossier,
contrôler la copie puis changer explicitement ACCOMPAGNEMENT_DONNEES. Il n'y a
pas de bascule automatique ou de retour arrière de migrations. Voir SERVEUR.md
et AUTHENTIFICATION.md pour le TOTP et les limites. Aucun dossier réel autorisé.

## Projet GitLab Pages dédié

Créer un nouveau projet public dans le groupe Pas à Pas (nom libre ; par exemple
pas-a-pas-pwa). Ne pas réutiliser le projet du site Petits Pas. Dans ce projet :

1. Copier pwa/publication/gitlab-ci.yml comme .gitlab-ci.yml et remplacer la ref
   par le **SHA du commit SOC6c appliqué** au dépôt source. Pas de main flottant.
2. Définir PWA_PUBLICATION_COMMIT au même SHA comme variable protégée. Protéger
   la branche main du projet cible et réserver la modification de sa CI/variable
   aux personnes responsables de la publication.
3. Autoriser les runners Inria ci.inria.fr/small et le déclenchement interprojets
   depuis le projet source. Régler la visibilité des artefacts/API nécessaires
   aux dépôts publics ; aucun jeton personnel n'est requis par le préparateur.
4. Dans le projet source, définir PWA_PUBLICATION_PROJECT au chemin réel du
   nouveau projet. Le job publier-pwa manuel apparaît sur main et les tags.

Le préparateur est téléchargé au SHA de confiance épinglé, pas depuis la valeur
forwardée PWA_SOURCE_SHA. Il vérifie ensuite le projet source, le pipeline,
sa branche/tag, les jobs Django, les deux déploiements et pwa-prototype réussis
pour le même commit. Sur tag, les deux forges doivent désigner le même commit.
Il télécharge l'artefact de ce job précis (jamais « dernier main »), vérifie
manifeste, empreintes, identité embarquée et testMode=false, puis copie les
statiques sans reconstruction. Un artefact expiré doit être reconstruit et
requalifié dans un nouveau pipeline, pas remplacé à la main.

L'adresse est celle donnée par CI_PAGES_URL dans le projet cible. Ne pas la
deviner ni changer son chemin après ouverture des premiers essais sans prévenir :
les données navigateur sont propres à l'origine et au chemin. Le fonctionnement
à la racine et sous un préfixe est testé ; les sous-projets d'une même origine
ne constituent pas une isolation de sécurité. La page telecharger.html fournit
un accès minimal à la PWA et aux releases publiques, sans annoncer une release
inexistante ni un service de démonstration encore non configuré.

Lors d'une évolution du préparateur, mettre à jour explicitement les deux SHA
épinglés dans le projet cible après validation de la nouvelle version.

## Programmes Linux/Windows

Les builds main/MR servent à vérifier ; seuls les builds d'un tag numérique
avec une rubrique correspondante non vide dans CHANGELOG.md sont publiables.
Le workflow publier-programmes se lance manuellement **depuis main**, avec le numéro du run paquets-locaux réussi
et le tag. Un environnement GitHub publication-programmes peut ajouter une
approbation et restreindre la branche ; le configurer dans les réglages GitHub.
Le jeton intégré reste en lecture dans les builds ; l'écriture est limitée au
job de publication.

Le script vérifie la provenance, les tags des deux forges, la version du commit,
la tentative du run, les cibles, inventaires et SHA-256. Il crée un brouillon de
préversion GitHub sans remplacer de release existante, retélécharge les assets
et compare les octets avant de publier. Les archives sont celles des jobs
validés, accompagnées des deux manifestes, de notes-version.md et de SHA256SUMS.

Alternative depuis un environnement Guix avec gh connecté au dépôt et le socle
sur PYTHONPATH : `python3 scripts/publier-paquets.py NUMERO_DU_RUN TAG`.
L'exécution de cette commande est une action de publication, pas un essai.
Un brouillon peut rester après erreur ; l'examiner avant de recommencer. Aucun
installateur Windows graphique n'est ajouté ; vérifier les programmes sur les
appareils cibles avant de les recommander.

## Qualification locale et limites

```sh
bash -n start-render.sh start-persistent.sh
python3 scripts/exercer-deploiement.py ephemere
python3 scripts/exercer-deploiement.py persistant
python3 -m unittest discover -s scripts -p 'test_publication*.py'
```

Les bancs utilisent des dossiers fictifs isolés, les vrais scripts, les contrôles
HTTP et arrêtent les groupes de processus même en cas d'échec. Le banc persistant
vérifie clé/fiche conservées et prépare une restauration de la sauvegarde.
Les tests de promotion sont simulés et n'effectuent aucune publication distante.
Les pipelines distants, Windows, les permissions interprojets et les déploiements
hébergés restent à valider après configuration. Voir le LIRE-MOI de livraison
pour les essais effectivement exécutés ; ne pas confondre recette et résultat.

## Complément PDF (#SOC7b)

requirements-serveur.txt et requirements-bureau.txt incluent désormais
requirements-pdf.txt. L'hébergement natif doit aussi fournir Pango, Fontconfig
et des polices : installer un wheel Python ne fournit pas ces bibliothèques.
Vérifier leur disponibilité chez l'hébergeur avant d'activer l'export natif ;
la CI Debian installe libpango-1.0-0 et libpangoft2-1.0-0. Si l'offre ne permet
pas ces dépendances, choisir un environnement adapté avant de proposer le PDF.
Le contrôle /health/ seul ne qualifie pas le rendu : télécharger effectivement
une fiche fictive après déploiement. La PWA ne dépend pas de Pango.

### Délai des bancs d'intégration

Le banc attend au plus 180 secondes par démarrage, migrations et collecte des
statiques comprises. Le temps est mesuré par horloge monotone ; une sortie du
processus est immédiatement signalée avec son code et son journal. Sur un
runner particulièrement lent, --delai-demarrage SECONDES permet une borne
explicite jusqu'à 900 secondes. Un délai expiré reste un échec ; les processus
sont arrêtés par le nettoyage habituel. Les avertissements HSTS ne sont ni
masqués ni transformés en erreurs.

## Version du code et notes de publication

Comme pour Petits Pas, le tag Git numérique exact (`0.2.0`, par exemple)
est la source de vérité. Une branche CI utilise `dev.<sha8>`, même si le
commit porte aussi un tag. En local, seul un tag pointant exactement sur HEAD
nomme une release ; un ancêtre tagué ne suffit pas. Plusieurs versions sur le
même commit sont refusées. Sans révision Git disponible, la version est `dev`.
Sur Render, les tags publics du miroir sont consultés pour RENDER_GIT_COMMIT ;
une consultation indisponible donne une version de développement.

`version-application.txt` est désormais généré à la construction et ignoré par
Git : il est embarqué dans le programme et le ZIP applicatif PWA. Il ne faut
plus le modifier ni le commiter. Le serveur calcule la même version au
chargement des réglages ; le pied de page l’affiche dans tous les profils.
Les commandes Render et les profils de dépendances restent identiques.

Les candidats contiennent `notes-version.md`, extrait de la rubrique exacte
du tag ou de `À venir` pour une branche ; son empreinte figure au manifeste.
La promotion des programmes compare aussi ces notes au changelog du commit
construit. Les notes, programmes et statiques sont promus sans reconstruction.
Après ce correctif, produire de nouveaux candidats : les anciens artefacts
sans notes sont refusés. Ne pas déplacer un tag ni remplacer une release
existante ; choisir le prochain numéro disponible. Aucun nouveau wheel
pas-communs n’est requis.
