"""NAV6 : les liens de consultation signent leur propre sélection."""
from urllib.parse import urlsplit, parse_qs
from django.core import signing
from django.test import TestCase
from django.urls import reverse
from . import dossier, tests_form2 as precedent, models as m


class PrestationsNavigationTests(TestCase):
    setUp = precedent.Form2Tests.setUp
    preparer = precedent.Form2Tests.preparer

    def test_consultation_et_retour_de_la_prestation_exacte(self):
        from datetime import date
        r = m.AccordRepas.objects.create(accompagnement=self.a, debut=date(2026, 2, 1), service='diner', cree_par=self.u)
        r.beneficiaires.add(self.p)
        page = self.client.get(self.detail, {'q':'Fictif', 'page':'3', 'vue_sociale':'today', 'presentation_sociale':'synthese'})
        for objet, cle in [(page.context['sejours_dossier'][0], 'sejour'), (page.context['accords_repas'][0], 'repas')]:
            token = parse_qs(urlsplit(objet.consultation_url).query)['contexte_dossier'][0]
            valeurs = signing.loads(token, salt=dossier.SEL)
            self.assertEqual(valeurs[cle], str(objet.pk))
            self.assertEqual(valeurs['vue'][cle], str(objet.pk))
            fiche = self.client.get(objet.consultation_url)
            self.assertEqual(fiche.status_code, 200)
            retour = self.client.get(fiche.context['retour_dossier'])
            self.assertEqual(str(retour.context['selection_sejour' if cle == 'sejour' else 'selection_repas'].pk), str(objet.pk))
            self.assertEqual(retour.context['page_recherche'], '3')
            self.assertEqual(retour.context['condition_integrale'], False)
        self.assertContains(page, 'name="presentation_sociale" value="synthese"', count=2)

    def test_selection_sans_javascript_conserve_les_autres_parametres(self):
        from datetime import date
        r = m.AccordRepas.objects.create(accompagnement=self.a, debut=date(2026, 2, 1), service='diner', cree_par=self.u)
        r.beneficiaires.add(self.p)
        page = self.client.get(self.detail, {'sejour':str(self.s.pk), 'repas':str(r.pk), 'vue_sociale':'today', 'presentation_sociale':'synthese'})
        self.assertContains(page, 'data-prestation-selection', count=4)  # Deux formulaires et leurs deux boutons de repli.
        self.assertContains(page, 'name="sejour"')
        self.assertContains(page, 'name="repas"')
        self.assertNotContains(page, 'data-dossier-selection')
