# Déployer et publier les essais fictifs — état courant et historique SOC6c

## Ce qui est livré

| Canal | Construction / contrôle | Activation |
| --- | --- | --- |
| Démonstration serveur | start-render.sh, espace SQLite neuf, clé neuve, comptes publics et jeu Les Passerelles (voir DEMONSTRATION.md) ; banc de redémarrage HTTP | Créer un service web ; hôte et HTTPS automatiques sur Render |
| Espace fictif persistant | start-persistent.sh, SQLite mono-processus, sauvegarde avant migration, aucun compte automatique ; banc de persistance/restauration | Dossier privé persistant, arrêt du service, variables et premier compte explicites |
| PWA | Même job GitLab : vrais Pyodide/Chromium, racine et préfixe, bundle normal puis manifeste | Projet Pages distinct ; automatique sur tag, manuel sur main |
| Programmes | GitHub Windows/Linux, tests, construction, version embarquée et manifestes | Automatique après construction de tag réussie ; reprise manuelle publier-programmes ou CLI gh |

Aucun hébergement, projet, secret, tag ou release n'est créé par cette livraison.
La version adoptée est fixée par requirements-communs.txt (0.8.0 publiée au
20 octobre 2026). Les numéros SOC6b/SOC6c ci-dessous décrivent l'historique. La structure
suit ses profils et promotions, avec les adaptateurs du produit CHRS.

## Ordre de mise en route

1. Appliquer SOC6c après SOC6b, SOC7a, le correctif des tags Inria et le
   correctif UTF-8 Windows. Pousser et attendre les CI.
2. Créer le service de démonstration si souhaité. Le tester publiquement sur
   des données fictives ; sa disponibilité n'est pas requise pour les CI.
3. Configurer le projet Pages dédié et activer publier-pwa.
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
identifiants publics donnant les droits explicites CHRS1–4 et création de fiches fictives.
Les comptes nadia, remi et camille proposent les mêmes droits ; voir [DEMONSTRATION.md](DEMONSTRATION.md).
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

Projet cible : pas-a-pas-accompagnement/pas-a-pas-accompagnement-pwa.
La chaîne reprend celle de Petits Pas : configuration incluse depuis main,
préparateur et requirements téléchargés au commit exact du pipeline source.

1. Sur main du projet cible, copier pwa/publication/gitlab-ci.yml comme
   .gitlab-ci.yml. Son include utilise ref: main ; aucun SHA à remplacer.
2. Autoriser les runners Inria ci.inria.fr/small et le déclenchement interprojets
   depuis le projet source. Garder une branche main protégée et des droits de
   modification réservés aux personnes responsables de la publication.
3. Garder les sources, API de pipeline et artefacts accessibles au préparateur
   des dépôts publics ; aucun jeton personnel n'est requis. Le compte lançant
   la publication doit pouvoir déclencher le pipeline du projet cible.
4. Si un premier setup avait défini PWA_PUBLICATION_COMMIT dans le projet cible
   ou PWA_PUBLICATION_PROJECT dans le projet source, supprimer ces variables :
   elles ne sont plus utilisées. Aucun autre paramètre ne les remplace.
5. Lancer un nouveau pipeline main du projet source, attendre les tests et les
   deux intégrations de déploiement ainsi que pwa-prototype, puis cliquer sur
   publier-pwa sur main. Sur tag numérique, la publication démarre automatiquement. Le job pages du projet cible effectue la publication.

Le commit du .gitlab-ci.yml cible ne publie rien par lui-même. Ne pas lancer
manuellement un pipeline web dans ce projet : seuls les déclenchements depuis
le projet source sont acceptés. Le job source transmet explicitement les
PWA_SOURCE_* ; aucune autre variable du pipeline source n'est forwardée.

Le préparateur et la dépendance viennent de PWA_SOURCE_SHA, pas du dernier
artefact de main. Le préparateur vérifie projet, pipeline, branche/tag, jobs
Django, deux déploiements et pwa-prototype réussis pour ce commit. Sur tag,
les deux forges doivent désigner le même commit. Le candidat du job précis est
vérifié (manifeste, empreintes, identité et testMode=false), puis ses statiques
sont copiés sans reconstruction. Les tags numériques sont publiés automatiquement après les contrôles ; main
reste manuel. Un échec de publication du tag fait échouer le pipeline.

L'adresse est celle de Deploy → Pages / CI_PAGES_URL dans le projet cible.
Choisir le domaine et son éventuel sous-chemin avant les premiers essais, puis
les conserver : le stockage navigateur dépend de l'origine et du chemin. Le
bundle fonctionne à la racine et sous un préfixe. Les sous-projets d'une même
origine ne constituent pas une isolation de sécurité. La page telecharger.html
fournit l'accès minimal aux programmes et rappelle le périmètre fictif.

Une évolution du préparateur suit désormais le code source, sans mise à jour
de SHA dans le projet cible. Le wheel reste épinglé par URL et empreinte dans
les requirements du commit source, comme pour les autres distributions.

## Programmes Linux/Windows

Les builds main/MR servent à vérifier ; seuls les builds d'un tag numérique
avec une rubrique correspondante non vide dans CHANGELOG.md sont publiables.
Le workflow publier-programmes démarre automatiquement après la réussite du
workflow des programmes sur tag. Il charge le code de publication depuis main
et promeut les artefacts du run terminé, sans reconstruction. Le workflow doit
être présent sur main avant le tag. Pour reprendre, utiliser Run workflow
depuis main en donnant le numéro du run réussi et son tag.

L'environnement GitHub publication-programmes est conservé. Si des reviewers
y sont requis, GitHub attendra encore leur approbation ; pour une publication
entièrement automatique, retirer cette exigence dans les réglages de cet
environnement. Les permissions d'écriture restent limitées au job de publication.

Le script vérifie la provenance, les tags des deux forges, la version du commit,
la tentative du run, les cibles, inventaires et SHA-256. Il crée un brouillon de
préversion GitHub sans remplacer de release existante, retélécharge les assets
et compare les octets avant de publier. Les archives sont celles des jobs
validés, accompagnées des deux manifestes, de notes-version.md et de SHA256SUMS.

Alternative depuis un environnement Guix avec gh connecté au dépôt et le socle
sur PYTHONPATH : `python3 scripts/publier-paquets.py NUMERO_DU_RUN TAG`.
L'exécution de cette commande est une action de publication, pas un essai.
Un brouillon peut rester après erreur ; l'examiner avant de recommencer. L’installateur
Windows doit être essayé sur les appareils cibles avant de le recommander.

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

## Setup Windows (#SOC3b)

Le candidat Windows contient aussi PasAPasAccompagnement-Setup-<version>-x64.exe,
construit avec Inno Setup via pas-communs 0.7.0. Son empreinte est au manifeste
Windows et sa présence est obligatoire lors de la promotion. La release publie
exactement le setup vérifié par la CI, sans reconstruction. Le ZIP portable
reste disponible. Aucun changement des commandes Render ou profils serveur.


## Décision : canal PWA habituel réservé aux versions stables

Les tags avec suffixe (dont `-rc`) construisent et qualifient la PWA mais ne
remplacent plus automatiquement sa publication habituelle. Le préparateur refuse
aussi leur promotion manuelle vers ce canal. Les artefacts CI permettent leurs
essais ; aucun nouveau site de préversions n’est créé. La publication de `main`
reste une action manuelle explicite sur la même adresse. Cette règle ne change
ni les releases des programmes, ni les déploiements serveur.
