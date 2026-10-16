$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
python -m pip install -r requirements-bureau.txt
if ($LASTEXITCODE -ne 0) { throw 'Installation des dépendances impossible.' }
python -m pas_communs.construire_bureau --spec scripts/PasAPasAccompagnement.spec --nom PasAPasAccompagnement
if ($LASTEXITCODE -ne 0) { throw 'Construction ou vérification du programme impossible.' }
