#!/usr/bin/env python3
"""Parcours HTTP réel, base et clé éphémères ; aucun dossier utilisateur lu."""
import base64
from html.parser import HTMLParser
import http.cookiejar
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from cryptography.fernet import Fernet
from django_otp.oath import TOTP

ROOT=Path(__file__).resolve().parent.parent
MOT="Phrase fictive pour le parcours-834"


class Codes(HTMLParser):
    def __init__(self,texte):
        super().__init__();self.dans_code=False;self.codes=[];self.feed(texte)
    def handle_starttag(self,tag,attrs):
        if tag=="code":self.dans_code=True
    def handle_endtag(self,tag):
        if tag=="code":self.dans_code=False
    def handle_data(self,texte):
        if self.dans_code:self.codes.append(texte.strip())


with tempfile.TemporaryDirectory(prefix="accompagnement-auth-fictif-") as dossier:
    env={**os.environ,"ACCOMPAGNEMENT_DONNEES":dossier,
         "DJANGO_SETTINGS_MODULE":"pas_a_pas_accompagnement.settings",
         "ACCOMPAGNEMENT_2FA":"obligatoire","ACCOMPAGNEMENT_2FA_CLES":Fernet.generate_key().decode(),
         "PYTHONUNBUFFERED":"1","PYTHONUTF8":"1"}
    # Fixtures uniquement. Le script n’accepte pas de chemin de base réelle.
    subprocess.run([sys.executable,"manage.py","migrate","--noinput"],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
    creer='''from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
u=get_user_model().objects.create_user('essai-http',password='Phrase fictive pour le parcours-834')
u.user_permissions.add(Permission.objects.get(content_type__app_label='personnes',codename='view_personne'))
'''
    subprocess.run([sys.executable,"manage.py","shell","-c",creer],cwd=ROOT,env=env,check=True,stdout=subprocess.DEVNULL)
    serveur='''import django,time
from pas_communs.local import ServeurBureau
from django.core.wsgi import get_wsgi_application
django.setup()
with ServeurBureau(get_wsgi_application()) as serveur:
 print(serveur.url,flush=True)
 while True: time.sleep(.25)
'''
    journal=Path(dossier)/"serveur.log"
    with journal.open("w+") as log:
        p=subprocess.Popen([sys.executable,"-c",serveur],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=log,text=True)
        try:
            # readline dans un thread : compatible Linux et Windows, délai borné.
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as pool:
                attente=pool.submit(p.stdout.readline)
                try:base=attente.result(timeout=20).strip()
                except TimeoutError:
                    p.terminate();raise
            if not base.startswith("http://127.0.0.1:"):
                raise RuntimeError("Démarrage HTTP fictif impossible.")
            cookies=http.cookiejar.CookieJar()
            client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
            def get(chemin):
                return client.open(base+chemin,timeout=5)
            def post(chemin,donnees):
                jeton=next(c.value for c in cookies if c.name=="pas_accompagnement_csrftoken")
                return client.open(base+chemin,urllib.parse.urlencode({**donnees,"csrfmiddlewaretoken":jeton}).encode(),timeout=5)
            get("connexion/").close()
            with post("connexion/",{"username":"essai-http","password":MOT}) as r:
                assert r.url.endswith("mon-compte/securite/")
            with get("personnes/") as r:
                assert r.url.endswith("mon-compte/securite/")
            with post("mon-compte/securite/",{"action":"commencer","mot_de_passe":MOT}) as r:
                cle=Codes(r.read().decode()).codes[0]
            secret=base64.b32decode(cle+"="*((8-len(cle)%8)%8))
            t=TOTP(secret)
            with post("mon-compte/securite/",{"action":"confirmer","mot_de_passe":MOT,"code":f"{t.token():06d}"}) as r:
                assert "no-store" in r.headers["Cache-Control"]
                secours=Codes(r.read().decode()).codes
                assert len(secours)==10
            post("deconnexion/",{}).close()
            with post("connexion/",{"username":"essai-http","password":MOT}) as r:
                assert r.url.endswith("connexion/verification/")
            with get("personnes/") as r:
                assert "connexion/" in r.url
            # GET /connexion/ annule l’attente : rétablir le premier facteur.
            post("connexion/",{"username":"essai-http","password":MOT}).close()
            post("connexion/verification/",{"code":secours[0]}).close()
            with get("personnes/") as r:assert r.url.endswith("personnes/")
            post("deconnexion/",{}).close()
            post("connexion/",{"username":"essai-http","password":MOT}).close()
            with post("connexion/verification/",{"code":secours[0]}) as r:
                assert "Code incorrect" in r.read().decode()
            print("HTTP CHRS : obligation → activation → secours → connexion → refus du rejeu : OK")
        finally:
            p.terminate()
            try:p.wait(timeout=10)
            except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
            if p.stdout:p.stdout.close()
