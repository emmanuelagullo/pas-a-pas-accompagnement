from unittest.mock import patch
from uuid import uuid4
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import Personne


class FichePdfTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.compte=get_user_model().objects.create_user('pdf-fictif')
        cls.personne=Personne.objects.create(designation='Identité fictive <script>école</script>',
                                            prenom='Élodie',cree_par=cls.compte)

    def url(self,pk=None):return reverse('personnes:fiche_pdf',args=[pk or self.personne.pk])

    def autoriser(self):
        self.compte.user_permissions.set(Permission.objects.filter(content_type__app_label='personnes',codename='view_personne'))
        self.client.force_login(self.compte)

    def test_refus_avant_generation_et_methodes(self):
        with patch('personnes.pdf.produire') as produire:
            self.assertEqual(self.client.get(self.url()).status_code,302)
            self.client.force_login(self.compte)
            self.assertEqual(self.client.get(self.url()).status_code,403)
            self.assertEqual(self.client.post(self.url()).status_code,405)
            produire.assert_not_called()
        self.autoriser()
        self.assertEqual(self.client.get(self.url(uuid4())).status_code,404)

    def test_fiche_native_est_un_pdf_prive(self):
        self.autoriser()
        response=self.client.get(self.url())
        self.assertEqual(response.status_code,200)
        self.assertEqual(response['Content-Type'],'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertIn(str(self.personne.pk),response['Content-Disposition'])
        self.assertNotIn(self.personne.designation,response['Content-Disposition'])
        self.assertIn('no-store',response['Cache-Control'])

    def test_html_metier_echappe_et_ne_charge_aucune_ressource(self):
        self.autoriser()
        with patch('pas_communs.pdf.rendre_html',return_value=b'%PDF-fictif') as rendu:
            self.client.get(self.url())
        self.assertIn('&lt;script&gt;',rendu.call_args.args[0])
        with self.assertRaises(ValueError):rendu.call_args.kwargs['recuperer']('https://externe.invalid')

    @override_settings(MODE_PWA=True)
    def test_choix_backend_navigateur_sans_weasyprint(self):
        self.autoriser()
        with patch('pas_communs.pdf.fiche_texte',return_value=b'%PDF-fictif') as texte,patch('pas_communs.pdf.rendre_html') as natif:
            self.assertEqual(self.client.get(self.url()).content,b'%PDF-fictif')
        natif.assert_not_called();texte.assert_called_once()

    @override_settings(MODE_PWA=True)
    def test_caractere_non_representable_erreur_privee(self):
        self.autoriser()
        with patch('pas_communs.pdf.fiche_texte',side_effect=ValueError('diagnostic interne')):
            response=self.client.get(self.url())
        self.assertEqual(response.status_code,422)
        self.assertNotIn(b'diagnostic',response.content)
        self.assertIn('no-store',response['Cache-Control'])
