#!/usr/bin/env bash
# Démonstration fictive jetable : aucun dossier existant n'est réutilisé.
set -euo pipefail
umask 077
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ -n "${ACCOMPAGNEMENT_DONNEES:-}" || -n "${DATABASE_URL:-}" || -n "${ACCOMPAGNEMENT_STATIC_ROOT:-}" || -n "${ACCOMPAGNEMENT_2FA_CLES:-}" || "${ACCOMPAGNEMENT_2FA:-desactive}" != desactive ]]; then
    echo 'Refus : le profil jetable ne réutilise aucune donnée, clé 2FA ou base distante.' >&2
    exit 1
fi
# Render fournit son nom public : configuration automatique limitée à ce profil.
# Les valeurs explicites gardent la priorité, notamment pour un domaine personnalisé.
if [[ -n "${RENDER_EXTERNAL_HOSTNAME:-}" ]]; then
    export ACCOMPAGNEMENT_HOSTS="${ACCOMPAGNEMENT_HOSTS:-$RENDER_EXTERNAL_HOSTNAME}"
    if [[ -z "${ACCOMPAGNEMENT_CSRF_ORIGINS:-}" ]]; then
        ACCOMPAGNEMENT_CSRF_ORIGINS="$(python3 -c 'import os; print(",".join("https://" + h.strip() for h in os.environ["ACCOMPAGNEMENT_HOSTS"].split(",")))')"
        export ACCOMPAGNEMENT_CSRF_ORIGINS
    fi
    export ACCOMPAGNEMENT_PROXY_HTTPS="${ACCOMPAGNEMENT_PROXY_HTTPS:-oui}"
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
case "${ACCOMPAGNEMENT_SCENARIO_DEMO:-acteurs}" in
    acteurs) python3 manage.py preparer_demonstration --acteurs ;;
    complet) python3 manage.py preparer_demonstration ;;
    *) echo 'Scénario inconnu : choisir acteurs ou complet.' >&2; exit 1 ;;
esac
python3 manage.py collectstatic --noinput
exec gunicorn --workers 1 --threads 1 --forwarded-allow-ips="" \
    --bind "${ACCOMPAGNEMENT_BIND:-0.0.0.0}:${PORT:-8000}" pas_a_pas_accompagnement.wsgi:application
