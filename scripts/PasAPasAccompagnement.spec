# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os
import tempfile
from pas_communs.construction import assembler

racine = next((p for p in (Path(SPECPATH).resolve(), Path(SPECPATH).resolve().parent)
    if (p / "scripts/lancer-local.py").is_file()), None)
if racine is None:
    raise FileNotFoundError("Lanceur introuvable.")
donnees_construction = tempfile.TemporaryDirectory(prefix="pas-accompagnement-construction-")
os.environ["ACCOMPAGNEMENT_DONNEES"] = donnees_construction.name
collation = assembler(racine, globals(), nom="PasAPasAccompagnement",
    settings="pas_a_pas_accompagnement.settings_local",
    ressources=[("templates", "templates"), ("static", "static"), ("LICENSE", ".")],
    paquets=["pas_a_pas_accompagnement", "identites", "personnes"],
    paquets_ressources=["django.forms"],
    imports=["pas_a_pas_accompagnement.settings_local", "pas_a_pas_accompagnement.urls",
             "whitenoise.middleware", "whitenoise.storage"],
    exclusions=["gunicorn", "psycopg", "storages", "boto3", "botocore", "weasyprint", "suivi", "referentiel", "comptes"])

donnees_construction.cleanup()
