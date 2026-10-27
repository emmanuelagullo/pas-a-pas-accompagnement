"""Concurrence réelle et copie restaurée, avec habilitations fictives."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import timedelta
from io import StringIO
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Barrier

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connections, connection, OperationalError
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from . import tests as donnees, services as s
from .contexte import perimetre
from .models import *


class OperationsTests(TransactionTestCase):
    setUp=donnees.AccesTests.setUp
    compte=donnees.AccesTests.compte
    dossier=donnees.AccesTests.dossier

    def test_deux_relais_concurrents_une_operation_et_un_successeur(self):
        r=Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin,debut=timezone.now()-timedelta(days=1))
        attendu=s.jeton(self.da);_,proposition=s.proposition_relais(self.ua,self.da,self.da)
        barriere=Barrier(2)
        def confirmer(_):
            try:
                u=get_user_model().objects.get(pk=self.ua.pk)
                d=DossierService.objects.get(pk=self.da.pk)
                prof=type(self.pc)._base_manager.get(pk=self.pc.pk)
                barriere.wait(timeout=10)
                with perimetre(u):s.relayer(u,d,prof,attendu,proposition)
                return True
            except (ValidationError,OperationalError):return False
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:resultats=list(pool.map(confirmer,range(2)))
        self.assertEqual(sum(resultats),1)
        self.assertEqual(JournalAcces.objects.filter(action='relais').count(),1)
        self.assertEqual(Responsabilite.objects.filter(dossier=self.da,professionnel=self.pc,fin__isnull=True).count(),1)
        r.refresh_from_db();self.assertIsNotNone(r.fin)

    def test_deux_reprises_concurrentes_un_seul_suivi(self):
        self.da.en_attente=True;self.da.save()
        attendu=s.jeton(self.da);barriere=Barrier(2)
        def prendre(pk):
            try:
                u=get_user_model().objects.get(pk=pk);d=DossierService.objects.get(pk=self.da.pk)
                barriere.wait(timeout=10)
                with perimetre(u):s.commencer(u,d,attendu)
                return True
            except (ValidationError,OperationalError):return False
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:resultats=list(pool.map(prendre,[self.ua.pk,self.uc.pk]))
        self.assertEqual(sum(resultats),1)
        self.assertEqual(JournalAcces.objects.filter(action='commencer').count(),1)
        self.assertEqual(Responsabilite.objects.filter(dossier=self.da).count(),1)

    def test_copie_restauree_conserve_politiques_relais_revocation_et_portees(self):
        if connection.vendor!='sqlite':self.skipTest('Copie autonome SQLite ; PostgreSQL possède une procédure distincte.')
        self.sa.politique='individuel';self.sa.save()
        Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin,debut=timezone.now()-timedelta(days=1))
        _,proposition=s.proposition_relais(self.ua,self.da,self.da)
        s.relayer(self.ua,self.da,self.pc,s.jeton(self.da),proposition)
        h=Habilitation.objects.get(compte=self.uc)
        s.revoquer(self.admin,h,s.jeton(h))
        from pas_a_pas_accompagnement.paquets import PROFIL
        with TemporaryDirectory() as temporaire:
            racine=Path(temporaire);source=racine/'source';source.mkdir()
            (source/'secret-key').write_text('cle-strictement-fictive-operations')
            with closing(sqlite3.connect(source/PROFIL.base)) as db:connection.connection.backup(db)
            archive=racine/'copie.zip';destination=racine/'restauree'
            with override_settings(LOCAL_DIR=source):
                call_command('sauvegarder_paquet',str(archive),stdout=StringIO())
                call_command('restaurer_copie',str(archive),str(destination),stdout=StringIO())
            code='''import django;django.setup()
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from acteurs.contexte import perimetre
from acteurs.models import ConfigurationAcces,JournalAcces
from personnes.models import Accompagnement
assert ConfigurationAcces.objects.get(pk=1).active
assert Session.objects.count()==0
for nom,nombre in [('nadia-fictive',0),('collegue-fictif',0),('camille-fictive',1)]:
    with perimetre(get_user_model().objects.get(username=nom)):
        assert Accompagnement.objects.count()==nombre,nom
assert JournalAcces.objects.filter(action='relais').count()==1
assert JournalAcces.objects.filter(action='revocation').count()==1
'''
            env=dict(os.environ,ACCOMPAGNEMENT_DONNEES=str(destination),DJANGO_SETTINGS_MODULE='pas_a_pas_accompagnement.settings')
            r=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True,timeout=45)
            self.assertEqual(r.returncode,0,r.stderr)


class EssaiTests(TransactionTestCase):
    def test_essai_volontaire_visible_sans_creer_de_compte(self):
        from acteurs.essai import preparer
        from django.test import Client
        from personnes.models import Menage
        u=get_user_model().objects.create_user('essai-social-fictif')
        service=preparer(u)
        self.assertEqual(get_user_model().objects.count(),1)
        c=Client();c.force_login(u)
        r=c.get('/')
        self.assertEqual(r.status_code,200)
        self.assertContains(r,'En attente')
        self.assertContains(r,'Mes dossiers')
        self.assertNotContains(r,'Dossier réservé à un autre service')
        with perimetre(u,service):self.assertEqual(Menage.objects.count(),5)
        with self.assertRaises(ValidationError):preparer(u)
