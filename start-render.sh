#!/usr/bin/env bash
# Démonstration fictive jetable : aucun dossier existant n'est réutilisé.
set -euo pipefail
umask 077
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ -n "${ACCOMPAGNEMENT_DONNEES:-}" || -n "${DATABASE_URL:-}" || -n "${ACCOMPAGNEMENT_STATIC_ROOT:-}" || -n "${ACCOMPAGNEMENT_2FA_CLES:-}" || "${ACCOMPAGNEMENT_2FA:-desactive}" != desactive ]]; then
    echo 'Refus : le profil jetable ne réutilise aucune donnée, clé 2FA ou base distante.' >&2
    exit 1
fi
export ACCOMPAGNEMENT_DONNEES
ACCOMPAGNEMENT_DONNEES="$(mktemp -d "${TMPDIR:-/tmp}/pas-a-pas-demo-XXXXXXXX")"
export ACCOMPAGNEMENT_DEMONSTRATION=oui
export ACCOMPAGNEMENT_REVISION="$(git rev-parse HEAD)"
export DJANGO_SETTINGS_MODULE=pas_a_pas_accompagnement.settings_demo
# Le runtime/volume temporaire de l'hébergeur reste responsable de sa purge.
# Pas de suppression récursive automatique au redémarrage.
python3 manage.py check --deploy --fail-level ERROR
python3 manage.py migrate --noinput
python3 manage.py preparer_demonstration
python3 manage.py collectstatic --noinput
exec gunicorn --workers 1 --threads 1 --forwarded-allow-ips="" \
    --bind "${ACCOMPAGNEMENT_BIND:-0.0.0.0}:${PORT:-8000}" pas_a_pas_accompagnement.wsgi:application
