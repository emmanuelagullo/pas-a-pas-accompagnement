# Serveur HTTPS fictif — contrat actuel

Profil volontaire : `pas_a_pas_accompagnement.settings_serveur`. Le démarrage
habituel garde son profil local et ne bascule pas sur ce profil automatiquement.
Aucun déploiement ni usage de dossiers réels n'est validé par sa présence.
Il n'y a toujours qu'un espace fictif, sans isolation de plusieurs structures.

## Préparer

Les dépendances sont dans requirements-serveur.txt ; le TOTP conserve son
installation facultative décrite dans AUTHENTIFICATION.md. Sous Guix, les
modules Python et Gunicorn/WhiteNoise peuvent venir du profil habituel et le
socle de PYTHONPATH ; aucune installation pip locale n'est imposée.

Choisir un dossier persistant absolu et un nom HTTPS réel. Exemple à adapter :

```sh
export DJANGO_SETTINGS_MODULE=pas_a_pas_accompagnement.settings_serveur
export ACCOMPAGNEMENT_DONNEES="$HOME/donnees-pas-a-pas-essai"
export ACCOMPAGNEMENT_HOSTS="accompagnement.exemple.org"
export ACCOMPAGNEMENT_CSRF_ORIGINS="https://accompagnement.exemple.org"
python3 manage.py migrate
python3 manage.py collectstatic --noinput
python3 manage.py check --deploy
python3 manage.py creer_compte_essai essai
```

Ces noms et chemins sont des exemples. La clé reste dans `secret-key` du
répertoire de données, créée une seule fois si absente : garder ce fichier
avec la base, comme sous SOC2. Aucun secret ni compte n'est embarqué.
Le premier compte web `/installer/` n'est pas accessible en mode serveur ;
la commande interactive attribue seulement lecture/création de personnes
fictives. Les politiques TOTP et les permissions ne sont pas modifiées.

## Backend et proxy

Exemple Linux, derrière un reverse-proxy HTTPS que l'exploitant configure :

```sh
# Seulement si ce proxy remplace X-Forwarded-Proto et protège l'accès backend :
export ACCOMPAGNEMENT_PROXY_HTTPS=oui
gunicorn --workers 1 --threads 1 --forwarded-allow-ips="" --bind 127.0.0.1:8001 pas_a_pas_accompagnement.wsgi:application
```

Le profil refuse HTTP et les hôtes/origines génériques. Le proxy doit fournir
le Host attendu. Sans activation explicite, X-Forwarded-Proto est ignoré.
La variable ne configure ni certificat ni pare-feu. Ne pas exposer directement
le backend. Contrôler HTTPS, /health/, CSRF et les cookies depuis l'adresse
publique avant de proposer un essai à d'autres personnes.

SQLite reste le stockage de ce prototype, avec un seul worker/thread ; aucun
service PostgreSQL ou conteneur n'est ajouté. Le profil n'autorise pas plusieurs
processus sur le même espace par analogie au bureau. Arrêter le service avant
une copie, restauration ou maintenance SOC2, en gardant les mêmes variables.
La clé, SQLite et les données restent hors du code ; les statiques sont
collectés par défaut sous le dossier de données (surcharge possible avec
ACCOMPAGNEMENT_STATIC_ROOT) et servis par WhiteNoise. Les médias ne deviennent
pas un répertoire public.

Le client REMOTE_ADDR peut être celui du proxy : la confiance HTTPS n'adopte
pas X-Forwarded-For. Le plafond par compte reste actif ; qualifier l'adresse
cliente et les limites avant tout essai collectif. Aucune confiance automatique
à un en-tête envoyé par un navigateur.

HSTS vaut une heure sans sous-domaines/preload ; ACCOMPAGNEMENT_HSTS_SECONDES
permet une durée de 0 à 31536000. Examiner les avertissements check --deploy ;
ils ne sont pas masqués. Les mails d'invitation et les rôles sociaux ne sont
pas ajoutés. Ne pas annoncer ce profil comme un déploiement CHRS de production.

## Vérifier sans héberger

`python3 scripts/verifier-profil-serveur.py` utilise uniquement un dossier
fictif temporaire. Le banc crée la base, collecte les statiques et exerce WSGI,
HTTPS simulé, refus de Host, CSRF, cookies et confiance proxy explicite.
Les CI exécutent ce contrôle avec la version épinglée dans
requirements-communs.txt. Pour la cible PostgreSQL proposée et sa qualification
préalable, lire [BASE-CIBLE.md](BASE-CIBLE.md) ; le présent profil reste SQLite.
