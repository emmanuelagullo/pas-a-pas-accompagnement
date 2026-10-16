#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Le Python courant doit voir PyGObject/WebKitGTK (venv --system-site-packages).
python3 -c 'import gi; gi.require_version("WebKit2", "4.1")'
python3 -m pip install -r requirements-bureau.txt
python3 -m pas_communs.construire_bureau --spec scripts/PasAPasAccompagnement.spec --nom PasAPasAccompagnement
