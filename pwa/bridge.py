"""Adaptateur CHRS sur Django/WSGI et moteur OPFS partagé."""
from contextlib import closing
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import sqlite3
from urllib.parse import urlsplit
from pas_communs.navigateur.http import environnement, retenir_cookies

DATA=Path("/data")
BASE="accompagnement.sqlite3"
COOKIES={}
APPLICATION=None
ORIGINE=None
SCRIPT_NAME=None
REPONSE=b""
COPIE=Path("/.pwa-chrs-sqlite-copy")


def valide_nom(nom):
    return nom in {BASE,"secret-key"}


def restore_file(nom, contenu):
    if not valide_nom(nom):
        raise ValueError("Fichier étranger au prototype CHRS")
    DATA.mkdir(exist_ok=True)
    (DATA/nom).write_bytes(bytes(contenu))


def initialize(origine,base="/"):
    global APPLICATION,ORIGINE,SCRIPT_NAME
    from pas_communs.navigateur.crypto import configure
    configure()
    ORIGINE=origine
    SCRIPT_NAME=base.rstrip("/")+"/app"
    DATA.mkdir(exist_ok=True)
    if (DATA/BASE).exists() != (DATA/"secret-key").exists():
        raise ValueError("Espace incomplet : aucune base vide ne sera créée.")
    if not (DATA/"secret-key").exists():
        (DATA/"secret-key").write_text(secrets.token_urlsafe(48))
    os.environ.update(DJANGO_SETTINGS_MODULE="pwa.settings",ACCOMPAGNEMENT_DONNEES=str(DATA),
        ACCOMPAGNEMENT_2FA="desactive",PWA_BASE_PATH=base,PWA_HOST=urlsplit(origine).hostname,
        PWA_ORIGIN=origine,DJANGO_ALLOW_ASYNC_UNSAFE="true")
    from django.core.wsgi import get_wsgi_application
    from django.core.management import call_command
    from django.db.migrations.loader import MigrationLoader
    APPLICATION=get_wsgi_application()
    if (DATA/BASE).exists():
        with closing(sqlite3.connect(DATA/BASE)) as db:
            if db.execute("PRAGMA quick_check").fetchone()[0]!="ok" or db.execute("PRAGMA foreign_key_check").fetchone():
                raise ValueError("Base locale endommagée")
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='django_migrations'").fetchone():
                connues=set(MigrationLoader(None).disk_migrations)
                if set(db.execute("SELECT app,name FROM django_migrations"))-connues:
                    raise ValueError("Version de données plus récente : ouverture refusée.")
    call_command("migrate",interactive=False,verbosity=0)
    # Aucun cookie virtuel conservé entre les Workers ; pas de session réutilisée.
    from django.contrib.sessions.models import Session
    Session.objects.all().delete()


def inventory():
    with closing(sqlite3.connect(DATA/BASE)) as source,closing(sqlite3.connect(COPIE)) as cible:
        source.backup(cible)
    fichiers={}
    for nom in [BASE,"secret-key"]:
        contenu=(COPIE if nom==BASE else DATA/nom).read_bytes()
        fichiers[nom]={"hash":hashlib.sha256(contenu).hexdigest(),"size":len(contenu)}
    return json.dumps({"files":fichiers,"bytes":sum(v["size"] for v in fichiers.values())})


def file_bytes(nom):
    if not valide_nom(nom):raise ValueError("Fichier non autorisé")
    return (COPIE if nom==BASE else DATA/nom).read_bytes()


def handle(encoded,corps):
    global REPONSE
    requete=json.loads(encoded)
    entree=io.BytesIO(bytes(corps))
    contexte=environnement(requete,SCRIPT_NAME,COOKIES,entree,len(entree.getbuffer()),origine=ORIGINE)
    resultat={}
    def debut(statut,entetes,exc_info=None):
        resultat.update(status=int(statut.split()[0]),headers=entetes)
    iterable=APPLICATION(contexte,debut)
    try:REPONSE=b"".join(iterable)
    finally:
        entree.close()
        if hasattr(iterable,"close"):iterable.close()
    resultat["headers"]=retenir_cookies(resultat["headers"],COOKIES)
    return json.dumps(resultat)


def response_bytes():
    global REPONSE
    corps,REPONSE=REPONSE,b""
    return corps
