#!/usr/bin/env bash
# Espace fictif persistant : arrêt préalable, sauvegarde privée avant migration.
set -euo pipefail
umask 077
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ "${ACCOMPAGNEMENT_MAINTENANCE:-}" != oui || "${ACCOMPAGNEMENT_DEMONSTRATION:-non}" != non || -n "${DATABASE_URL:-}" ]]; then
    echo 'Refus : exiger ACCOMPAGNEMENT_MAINTENANCE=oui, arrêter le service et ne pas utiliser le profil démonstration ou DATABASE_URL.' >&2
    exit 1
fi
: "${ACCOMPAGNEMENT_DONNEES:?Dossier persistant absolu requis}"
export ACCOMPAGNEMENT_REVISION="$(git rev-parse HEAD)"
export DJANGO_SETTINGS_MODULE=pas_a_pas_accompagnement.settings_serveur
python3 scripts/preparer-persistant.py
python3 manage.py check --deploy --fail-level ERROR
python3 manage.py migrate --noinput
python3 manage.py collectstatic --noinput
exec gunicorn --workers 1 --threads 1 --forwarded-allow-ips="" \
    --bind "${ACCOMPAGNEMENT_BIND:-127.0.0.1}:${PORT:-8000}" pas_a_pas_accompagnement.wsgi:application
