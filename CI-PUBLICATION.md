# Recettes et candidats fictifs — #SOC6b

## Vérification commune, contrôles produit

La recette du wheel 0.5.0 effectue check, absence de migration et tests, puis
les contrôles explicitement demandés. Les profils/matrices Python/Django,
dépendances et artefacts restent dans chaque forge. --migrer et --pip-check
sont explicites ; en local Guix, omettre --pip-check. Le lanceur ne fait
aucune installation automatique. Les erreurs arrêtent la recette.

Le banc serveur utilise son propre dossier fictif, migre et collecte les
statiques, puis teste WSGI et un vrai Gunicorn loopback Unix. Le banc
d'authentification conserve ses scénarios TOTP propres au CHRS.
La confiance HTTPS ne décide pas de l'adresse IP cliente.

## Décrire les candidats

Le workflow des programmes produit publication-programme.json à côté de
l'archive, avec format pas-a-pas-accompagnement-publication, schema 1, identité
déclarée de la construction, cible, taille et SHA-256. Il vérifie le manifeste
avant l'upload temporaire. Il décrit aussi notes-version.md, extrait du
changelog de la version construite. Un lien symbolique, nom dupliqué, format étranger,
cible attendue différente ou fichier altéré est refusé.

Pour la PWA, seul un bundle normal marqué testMode=false, à version/application,
fichiers et empreintes valides, est archivé par manifeste-publication.py.
Le ZIP exact, notes-version.md et publication-pwa.json sont conservés comme artefact fictif
normal, distinct du bundle de tests. Un bundle --test ou ancien non marqué
est refusé. Les manifestes sont placés hors bundle pour ne pas modifier les
statiques validés.

Exemple, après construction et vérification du bundle normal :

    python3 scripts/manifeste-publication.py --mode navigateur --target chromium-statique --bundle dist/pwa-production --destination dist/publication-pwa.json
    python3 scripts/manifeste-publication.py --verifier dist/publication-pwa.json --mode navigateur --target chromium-statique

Une archive de candidat existante n'est pas remplacée ; choisir une sortie
neuve. Les contenus restent des prototypes sans données de développeur.
Le manifeste n'est pas une signature, une preuve de tests réussis ni un audit
du contenu de toute archive. Il ne prouve pas à lui seul la version interne
d'un binaire. La chaîne CI doit lier construction, tests et octets avant toute
future promotion. Aucun jeton ni paramètre privé de déploiement n'est écrit.

## Publication (#SOC6c)

Les promotions sont décrites dans [DEPLOIEMENTS.md](DEPLOIEMENTS.md).
Les programmes d'un tag validé sont publiables via le workflow GitHub automatique sur tag (reprise manuelle conservée) ;
la PWA depuis le même pipeline GitLab que ses contrôles réussis, vers un projet
Pages dédié. Aucun dossier réel, site ou secret d'hébergement n'est configuré
par le dépôt. Les artefacts temporaires restent distincts des releases.

À cette étape historique, le socle était 0.5.0. SOC6b couvrait profils, recettes et candidats ; SOC6c ajoute
les scripts de démarrage, leurs intégrations et les promotions des produits.
Les plateformes Windows et navigateurs restent qualifiées par leurs CI/bancs
dédiés. Certificats, proxy réel, exploitation et SMTP restent à configurer.

## Déclenchement GitHub harmonisé

Sur main, les workflows authentification, programmes et PWA filtrent les
fichiers modifiés : code applicatif, templates, statiques, dépendances, scripts,
notes et leur propre fichier de workflow. La PWA surveille aussi pwa/. Une
modification de documentation générale ou du seul workflow de publication
ne relance donc pas les trois constructions. Les filtres restent prudents :
tout changement de script ou de dépendance réexerce les parcours concernés.

Comme pour Petits Pas, les pushes de tags numériques ne sont pas filtrés par
les chemins : tous les workflows de qualification se lancent. Le déclenchement
manuel et les contrôles sur pull request restent disponibles. Les jobs GitLab,
les publications et les déploiements serveur ne changent pas.


## AUD — adoption et contrôles partagés

Les petits contrôles des exécutions, événements, tags et artefacts plats viennent
de pas_communs.promotion (candidat 0.8.0). Les appels de forge, destinations,
formats, notes, noms d'artefacts et décisions de publication restent ici.
QUALIFICATION.md du socle vérifie les deux produits et les octets importés,
sans installer ni publier. Ne pas confondre cette recette locale avec les bancs
Windows, PWA et déploiement ; ils restent obligatoires dans leurs CI.
