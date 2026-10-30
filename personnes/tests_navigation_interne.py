"""Contrat HTML du sommaire commun et des destinations autorisées."""
from html.parser import HTMLParser
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Permission
from .tests_hebergement import Donnees
from . import tests_entree_bd as entree


class Ancres(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.liens, self.pile = set(), [], []

    def handle_starttag(self, tag, attributs):
        attributs = dict(attributs)
        if attributs.get('id'):
            self.ids.add(attributs['id'])
        cache = 'hidden' in attributs or any(x[1] for x in self.pile)
        navigation = 'condition-menu' in attributs.get('class', '').split() or 'condition-acces' in attributs.get('class', '').split() or any(x[2] for x in self.pile)
        if tag == 'a' and navigation and not cache and attributs.get('href', '').startswith('#'):
            self.liens.append(attributs['href'][1:])
        if tag not in ('input', 'br', 'hr', 'img', 'meta', 'link', 'path', 'wbr'):
            self.pile.append((tag, cache, navigation))

    def handle_endtag(self, tag):
        for i in range(len(self.pile)-1, -1, -1):
            if self.pile[i][0] == tag:
                del self.pile[i:]
                break


class NavigationInterneTests(Donnees, TestCase):
    setUp = entree.EntreeBDTests.setUp

    def test_destinations_presentes_et_sommaire_unique(self):
        for nature, pk in [('menage', self.m.pk), ('personne', self.p.pk)]:
            for prise in (False, True):
                url = reverse('dossiers:prise' if prise else 'dossiers:detail',
                    args=[nature, pk, self.a.pk] if prise else [nature, pk])
                page = self.client.get(url)
                self.assertContains(page, 'id="sommaire-dossier"', count=1)
                self.assertContains(page, 'aria-label="Fil d’Ariane"', count=1)
                self.assertContains(page, 'aria-label="Accès rapides dans cette page"', count=1)
                ancres = Ancres()
                ancres.feed(page.content.decode())
                self.assertTrue(ancres.liens)
                self.assertFalse(set(ancres.liens) - ancres.ids)
                self.assertIn('titre-prestations' if prise else 'prises', ancres.liens)

    def test_pas_de_destination_appels_sans_droit(self):
        self.u.user_permissions.remove(Permission.objects.get(
            content_type__app_label='personnes', codename='view_appel115'))
        page = self.client.get(self.url)
        self.assertNotContains(page, 'href="#appels-115"')
