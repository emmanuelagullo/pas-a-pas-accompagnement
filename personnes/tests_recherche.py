from django.contrib import messages
from django.test import TestCase
from django.urls import reverse

from .models import Personne, Menage, Transmission
from .tests_navigation import NavigationTests


class RechercheTests(TestCase):
    def setUp(self):
        NavigationTests.setUp(self)

    def test_personnes_termes_repartis_et_aucun_resultat(self):
        self.p.prenom = 'Camille'
        self.p.save(update_fields=['prenom'])
        url = reverse('personnes:liste')
        page = self.client.get(url, {'q': 'camille Navigation'})
        self.assertEqual(list(page.context['page_obj']), [self.p])
        self.assertContains(self.client.get(url, {'q': 'absent'}), 'Aucun résultat')

    def test_pagination_conserve_recherche(self):
        Personne.objects.bulk_create([Personne(designation=f'Recherche {i:02}', cree_par=self.u) for i in range(26)])
        page = self.client.get(reverse('personnes:liste'), {'q': 'Recherche'})
        self.assertContains(page, '?q=Recherche&amp;page=2')
        self.assertEqual(len(page.context['page_obj']), 25)

    def test_menages_par_membre_sans_doublon_et_rattachement_conserve(self):
        autre = Personne.objects.create(designation='Navigation autre', cree_par=self.u)
        from . import suivi
        suivi.ajouter_appartenance(self.u, self.m, autre, self.a.debut)
        page = self.client.get(reverse('suivi:liste'), {'q': 'Navigation', 'personne': str(autre.pk)})
        self.assertEqual(list(page.context['menages']), [self.m])
        self.assertContains(page, 'name="personne" value="'+str(autre.pk)+'"')
        self.assertContains(page, 'Rattacher à ce ménage')
        Menage.objects.bulk_create([Menage(libelle=f'Pagination {i:02}', cree_par=self.u) for i in range(26)])
        page = self.client.get(reverse('suivi:liste'), {'q': 'Pagination', 'personne': str(autre.pk)})
        self.assertContains(page, '?q=Pagination&amp;personne='+str(autre.pk)+'&amp;page=2')

    def test_recherche_naccorde_aucun_droit(self):
        self.u.user_permissions.clear()
        for route in ('personnes:liste', 'suivi:liste'):
            self.assertEqual(self.client.get(reverse(route), {'q': 'Navigation'}).status_code, 403)
