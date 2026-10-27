# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os
import tempfile
import sys
from pas_communs.construction import assembler

racine = next((p for p in (Path(SPECPATH).resolve(), Path(SPECPATH).resolve().parent)
    if (p / "scripts/lancer-local.py").is_file()), None)
if racine is None:
    raise FileNotFoundError("Lanceur introuvable.")
sys.path.insert(0, str(racine / "scripts"))
from publication import identity, release_notes
identite_construction = identity()
# Fichier produit pour l'exécutable ; jamais une source manuelle de version.
(racine / "version-application.txt").write_bytes((identite_construction['application_version'] + "\n").encode('utf-8'))
release_notes(identite_construction['tag'])
donnees_construction = tempfile.TemporaryDirectory(prefix="pas-accompagnement-construction-")
os.environ["ACCOMPAGNEMENT_DONNEES"] = donnees_construction.name
collation = assembler(racine, globals(), nom="PasAPasAccompagnement",
    settings="pas_a_pas_accompagnement.settings_local",
    pango_variable="ACCOMPAGNEMENT_PANGO_BIN",
    ressources=[("templates", "templates"), ("static", "static"), ("LICENSE", "."), ("version-application.txt", ".")],
    paquets=["pas_a_pas_accompagnement", "identites", "personnes", "acteurs"],
    paquets_ressources=["django.forms"],
    imports=["pas_a_pas_accompagnement.settings_local", "pas_a_pas_accompagnement.urls",
             "whitenoise.middleware", "whitenoise.storage"],
    exclusions=["gunicorn", "psycopg", "storages", "boto3", "botocore", "suivi", "referentiel", "comptes",
                "django_otp", "cryptography", "qrcode"])

donnees_construction.cleanup()
