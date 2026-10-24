from datetime import date
from django import forms
from django.test import SimpleTestCase, TestCase
from .champs_saisie import FormulaireMetier
from .tests_hebergement import Donnees


class PeriodeExemple(FormulaireMetier):
    saisie_periode=('debut','fin')
    debut=forms.DateField()
    fin=forms.DateField(required=False)


class PeriodesSaisieTests(SimpleTestCase):
    def test_duree_bissextile_et_valeurs_transmises_au_metier(self):
        f=PeriodeExemple({'debut':'2024-02-28','fin':'','duree':'2','calcul_periode':'duree'})
        self.assertTrue(f.is_valid(),f.errors)
        self.assertEqual(f.cleaned_data,{'debut':date(2024,2,28),'fin':date(2024,3,1)})

    def test_dates_directes_et_inconnu_ne_devient_pas_zero(self):
        f=PeriodeExemple({'debut':'2026-03-29','fin':'2026-04-01','calcul_periode':'dates'})
        self.assertTrue(f.is_valid());self.assertEqual(f.cleaned_data['fin'],date(2026,4,1))
        f=PeriodeExemple({'debut':'2026-03-29','fin':'','calcul_periode':'dates'})
        self.assertTrue(f.is_valid());self.assertIsNone(f.cleaned_data['fin'])
        f=PeriodeExemple({'debut':'2026-03-29','fin':'','duree':'0','calcul_periode':'duree'})
        self.assertFalse(f.is_valid());self.assertIn('duree',f.errors)

    def test_depassement_dates_possible_et_choix_invalide(self):
        for d in [dict(debut='9999-12-31',fin='',duree='2',calcul_periode='duree'),
                  dict(debut='2026-01-01',fin='',duree='2',calcul_periode='inconnu')]:
            f=PeriodeExemple(d);self.assertFalse(f.is_valid())

    def test_initialisation_et_fin_obligatoire(self):
        f=PeriodeExemple(initial={'debut':date(2026,1,1),'fin':date(2026,1,8)})
        self.assertEqual(f.initial['duree'],7)
        class Obligation(PeriodeExemple):fin=forms.DateField()
        f=Obligation({'debut':'2026-01-01','fin':'','duree':'','calcul_periode':'duree'})
        self.assertFalse(f.is_valid())


class PeriodesIntegrationTests(Donnees,TestCase):
    def test_accord_repas_et_prise_sans_javascript(self):
        from .forms_repas import AccordForm
        from .forms_suivi import AccompagnementForm
        from . import repas, suivi
        self.preparer()
        from django.core.management import call_command
        from django.contrib.auth import get_user_model
        from io import StringIO
        call_command("autoriser_chrs7", self.u.username, stdout=StringIO())
        self.u=get_user_model().objects.get(pk=self.u.pk)
        f=AccordForm({'debut':'2026-01-01','fin':'','duree':'7','calcul_periode':'duree',
            'beneficiaires':[self.p.pk],'service':'dejeuner','prestataire':''},accompagnement=self.a)
        self.assertTrue(f.is_valid(),f.errors)
        accord=repas.accorder(self.u,self.a,**f.cleaned_data)
        self.assertEqual(accord.fin,date(2026,1,8));self.assertFalse(accord.realisations.exists())
        f=AccompagnementForm({'debut':'2026-02-01','fin_prevue':'','duree':'14','calcul_periode':'duree','beneficiaires':[self.p.pk]})
        self.assertTrue(f.is_valid(),f.errors)
        a=suivi.ouvrir(self.u,self.m,**f.cleaned_data)
        self.assertEqual(a.fin_prevue,date(2026,2,15));self.assertIsNone(a.fin)
