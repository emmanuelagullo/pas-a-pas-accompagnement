"""Contrôles utiles : HTML effectif, propositions volontaires, dates et absence d'écriture."""
import copy
import importlib
import inspect
import pkgutil
import runpy
from contextlib import redirect_stderr
from datetime import date
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.template import Template, Context
from django.test import TestCase, SimpleTestCase
from django.urls import reverse
from . import bd6, coordonnees, propositions
from .champs_saisie import FormulaireMetier, adapter
from .models import PropositionSaisie, RevisionPropositionSaisie, Personne, CoordonneesPersonnelles


class CatalogueChampsTests(SimpleTestCase):
    def test_tous_les_formulaires_metier_declares_ont_des_controles_types(self):
        import personnes
        nombre=0
        for spec in pkgutil.iter_modules(personnes.__path__):
            if not spec.name.startswith(('forms','vues')):continue
            module=importlib.import_module('personnes.'+spec.name)
            for _,cls in inspect.getmembers(module,inspect.isclass):
                if cls.__module__!=module.__name__ or not issubclass(cls,forms.BaseForm):continue
                f=FormulaireMetier();f.fields=copy.deepcopy(cls.base_fields);adapter(f)
                for nom,champ in f.fields.items():
                    nombre+=1;w=champ.widget
                    if w.is_hidden:continue
                    if nom in ('telephone','fax'):self.assertEqual(w.input_type,'tel',(spec.name,nom))
                    if isinstance(champ,forms.EmailField):self.assertEqual(w.input_type,'email')
                    if isinstance(champ,forms.DateField):
                        self.assertEqual(w.input_type,'date',(spec.name,nom))
                        self.assertEqual(w.format,'%Y-%m-%d')
                    if isinstance(champ,forms.IntegerField):self.assertEqual(w.attrs.get('inputmode'),'numeric')
        self.assertGreater(nombre,150)

    def test_montant_francais_et_zero_inconnu_distincts(self):
        class Montant(FormulaireMetier):
            montant=forms.DecimalField(max_digits=9,decimal_places=2,min_value=0,required=False)
        self.assertTrue(Montant({'montant':'12,50'}).is_valid())
        self.assertTrue(Montant({'montant':'12.50'}).is_valid())
        self.assertIsNone(Montant({'montant':''}).fields['montant'].clean(''))
        self.assertFalse(Montant({'montant':'-1'}).is_valid())

    def test_qualification_pdf_signale_les_prerequis_avant_toute_base(self):
        script=runpy.run_path(str(Path(__file__).resolve().parent.parent/'scripts/qualifier-solenne-profils.py'))
        err=StringIO()
        with patch('sys.argv',['qualification']),patch('importlib.util.find_spec',return_value=None),patch('subprocess.run') as run,redirect_stderr(err):
            with self.assertRaises(SystemExit) as ctx:script['main']()
            self.assertEqual(ctx.exception.code,2);run.assert_not_called()
        self.assertIn('fpdf2',err.getvalue());self.assertIn('--sans-pdf',err.getvalue())
        with patch('sys.argv',['qualification','--sans-pdf']),patch('subprocess.run') as run:script['main']()
        self.assertEqual(run.call_count,3)
        self.assertTrue(all(c.kwargs['env']['SOLENNE_VERIFIER_PDF']=='non' for c in run.call_args_list))


class SaisieTests(TestCase):
    def setUp(self):
        self.u=get_user_model().objects.create_user('saisie-fictive')
        call_command('autoriser_solenne',self.u.username,stdout=StringIO())
        self.u.user_permissions.add(Permission.objects.get(codename='view_personne'))
        self.u=get_user_model().objects.get(pk=self.u.pk);self.client.force_login(self.u)
        self.p=Personne.objects.create(designation='Personne fictive',cree_par=self.u)

    def coord(self,ville,debut):
        return coordonnees.renseigner(self.u,self.p,debut,'Entretien fictif',bd6.jeton(self.p),rue='Rue fictive',code_postal='00100',ville=ville,pays='Pays fictif',telephone='+00 (000) 000 000',courriel='personne@example.invalid',fax='')

    def test_html_coordonnees_types_codes_et_liens(self):
        self.coord('Ville fictive',date(2026,1,1))
        url=reverse('dossiers:coordonnees_nouvelles',args=[self.p.pk])
        page=self.client.get(url)
        self.assertContains(page,'type="tel"');self.assertContains(page,'type="email"');self.assertContains(page,'inputmode="tel"')
        self.assertContains(page,'<textarea name="rue"');self.assertContains(page,'value="00100"')
        self.assertContains(page,'autocomplete="off"');self.assertContains(page,'Partir de champs vides')
        page=self.client.get(reverse('dossiers:coordonnees',args=[self.p.pk]))
        self.assertContains(page,'href="tel:+00000000000"');self.assertContains(page,'mailto:personne@example.invalid')
        t=Template('{% load saisie %}{{ valeur|telephone_lien }}')
        self.assertEqual(t.render(Context({'valeur':'01 23 45 67 89 / 02 34 56 78 90'})),'')

    def test_prefill_a_date_et_champs_vides_sans_ecriture(self):
        self.coord('Ancienne ville fictive',date(2026,1,1));self.coord('Nouvelle ville fictive',date(2026,3,1))
        url=reverse('dossiers:coordonnees_nouvelles',args=[self.p.pk])
        page=self.client.get(url,{'date':'2026-02-01','depuis_nature':'personne','depuis_pk':self.p.pk})
        self.assertEqual(page.context['form'].initial['ville'],'Ancienne ville fictive')
        self.assertEqual(page.context['form'].initial['source'],'')
        self.assertEqual(page.context['form'].initial['debut'],date(2026,2,1))
        page=self.client.get(url,{'date':'2026-02-01','vierge':'1'})
        self.assertNotIn('ville',page.context['form'].initial)
        self.assertEqual(CoordonneesPersonnelles.objects.count(),2)

    def test_propositions_pas_de_collecte_implicite_et_historique(self):
        self.coord('Ville privée fictive',date(2026,1,1))
        self.assertFalse(PropositionSaisie.objects.exists())
        x=propositions.enregistrer(self.u,'ville','Ville proposée fictive',True,'Choix fictif')
        url=reverse('dossiers:coordonnees_nouvelles',args=[self.p.pk])
        self.assertContains(self.client.get(url),'<option value="Ville proposée fictive">',html=False)
        token=propositions.jeton(x)
        propositions.enregistrer(self.u,'ville',x.valeur,False,'Retrait fictif',objet=x,attendu=token)
        self.assertNotContains(self.client.get(url),'<option value="Ville proposée fictive">')
        with self.assertRaises(ValidationError):propositions.enregistrer(self.u,'ville','Autre',True,'Fictif',objet=x,attendu=token)
        self.assertEqual(RevisionPropositionSaisie.objects.count(),2)
        self.assertEqual(self.p.coordonnees.first().ville,'Ville privée fictive')

    def test_proposition_html_echappee_texte_libre_et_droits(self):
        x=propositions.enregistrer(self.u,'ville','<script>fictif</script>',True,'Essai fictif')
        page=self.client.get(reverse('dossiers:coordonnees_nouvelles',args=[self.p.pk]))
        self.assertContains(page,'&lt;script&gt;fictif&lt;/script&gt;');self.assertNotContains(page,'<script>fictif</script>')
        self.u.user_permissions.remove(Permission.objects.get(codename='view_propositionsaisie'))
        self.assertNotContains(self.client.get(reverse('dossiers:coordonnees_nouvelles',args=[self.p.pk])),'<datalist')
        self.assertEqual(self.client.get(reverse('dossiers:propositions')).status_code,403)
        with self.assertRaises(ValidationError):propositions.enregistrer(self.u,'telephone','Numéro privé fictif',True,'Refus')


from django.test import TransactionTestCase


class ConcurrencePropositionsTests(TransactionTestCase):
    def test_deux_modifications_un_seul_journal_et_pas_de_perte(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections, OperationalError
        u=get_user_model().objects.create_user('propositions-concurrentes')
        call_command('autoriser_solenne',u.username,stdout=StringIO())
        u=get_user_model().objects.get(pk=u.pk)
        x=propositions.enregistrer(u,'ville','Ville initiale fictive',True,'Création fictive')
        attendu=propositions.jeton(x);depart=Barrier(2)
        def ecrire(numero):
            close_old_connections()
            try:
                acteur=get_user_model().objects.get(pk=u.pk);acteur.get_all_permissions()
                objet=PropositionSaisie.objects.get(pk=x.pk);depart.wait(timeout=10)
                try:
                    propositions.enregistrer(acteur,'ville','Ville fictive '+str(numero),True,'Modification fictive',objet=objet,attendu=attendu)
                    return True
                except (ValidationError,OperationalError):return False
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:resultats=list(pool.map(ecrire,range(2)))
        self.assertEqual(sum(resultats),1,resultats)
        self.assertEqual(RevisionPropositionSaisie.objects.count(),2)
