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
avant l'upload temporaire. Un lien symbolique, nom dupliqué, format étranger,
cible attendue différente ou fichier altéré est refusé.

Pour la PWA, seul un bundle normal marqué testMode=false, à version/application,
fichiers et empreintes valides, est archivé par manifeste-publication.py.
Le ZIP exact et publication-pwa.json sont conservés comme artefact fictif
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

## Publication

Aucun tag, release CHRS, envoi à un registre ou site public automatique n'est
ajouté. Les artefacts CI expirent et ne sont pas un canal stable de distribution.
La publication du wheel Pas communs 0.5.0 est distincte : attendre ses tests,
publier son premier tag et vérifier ses octets, puis pousser les consommateurs.

#SOC6 est clos pour le socle des profils volontaires, recettes et candidats.
Le CHRS demeure fictif ; habilitations multi-structures et dossiers sociaux
réels ne sont pas validés. Les plateformes Windows et navigateurs restent
qualifiés par leurs CI/bancs dédiés, pas par le seul manifeste. Les certificats,
proxy réel, sauvegardes hébergeur et SMTP ne sont pas configurés ici.
