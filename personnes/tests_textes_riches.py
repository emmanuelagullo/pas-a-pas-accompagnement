"""Contrat v1, sécurité et parcours : données exclusivement fictives."""
import copy
import json
from datetime import date
from io import StringIO
from unittest.mock import patch
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from . import textes_riches as tr


def document(texte='Texte fictif', marque='bold'):
    n = {'type': 'text', 'text': texte}
    if marque:
        n['marks'] = [{'type': marque}]
    return {'version': 1, 'doc': {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [n]}]}}


def valeur(texte='Texte fictif', marque='bold'):
    return tr.preparer(tr.ValeurTexte('', document(texte, marque)))


class FormatTests(SimpleTestCase):
    def test_ancien_texte_literal_et_document_explicite(self):
        texte = '**gras** <script>fictif</script>\n[exemple](https://example.org)'
        self.assertIsNone(tr.preparer(texte).document)
        rendu = str(tr.rendre(texte))
        self.assertIn('**gras**', rendu)
        self.assertIn('&lt;script&gt;', rendu)
        self.assertNotIn('<a ', rendu)
        self.assertIn('<strong>Texte fictif</strong>', tr.rendre('', document()))

    def test_rejeter_noeuds_attributs_et_versions_inconnus(self):
        mauvais = [None, [], {}, {'version': 2, 'doc': {}}, {'version': True, 'doc': {}},
                   {'version': 1, 'doc': {'type': 'doc', 'content': [{'type': 'image', 'attrs': {'src': 'https://example.org'}}]}}]
        for mutation in ('attrs', 'marks', 'content'):
            d = document()
            d['doc']['content'][0]['content'][0][mutation] = {'onerror': 'fictif'}
            mauvais.append(d)
        d = document(); d['doc']['content'][0]['content'][0]['marks'] = [{'type': 'html'}]; mauvais.append(d)
        for d in mauvais:
            with self.subTest(d=d), self.assertRaises(ValidationError): tr.valider(d)

    def test_liens_et_html_echappes(self):
        for url in ['javascript:alert(1)', 'data:text/html,fictif', '/gestion/', '//example.org', 'file:///tmp/a', 'https://user:pass@example.org', 'https://example.org/\nx', 'https://example.org:zzz', 'https://example.org\\x']:
            d = document('<img src=x onerror=x>', None)
            d['doc']['content'][0]['content'][0]['marks'] = [{'type': 'link', 'attrs': {'href': url}}]
            with self.subTest(url=url), self.assertRaises(ValidationError): tr.valider(d)
        d = document('<img src=x>', None)
        d['doc']['content'][0]['content'][0]['marks'] = [{'type': 'link', 'attrs': {'href': 'https://example.org/?a=1&b=2'}}]
        html = tr.rendre('', d)
        self.assertIn('&lt;img', html); self.assertIn('a=1&amp;b=2', html)
        self.assertIn('noopener noreferrer', html); self.assertNotIn('<img', html)

    def test_limites_structurelles_et_longueur_visible(self):
        with self.assertRaises(ValidationError): tr.preparer(valeur('abc'), max_length=2)
        self.assertEqual(tr.preparer(valeur('é🙂'), max_length=2), 'é🙂')
        with self.assertRaises(ValidationError): tr.preparer(valeur('  ', None), required=True)
        d = document('x' * 70000)
        with self.assertRaises(ValidationError): tr.valider(d)
        d = document()
        for _ in range(15): d['doc']['content'] = [{'type': 'bulletList', 'content': [{'type': 'listItem', 'content': [{'type': 'paragraph'}, *d['doc']['content']]}]}]
        with self.assertRaises(ValidationError): tr.valider(d)
        d = {'version': 1, 'doc': {'type': 'doc', 'content': [{'type': 'bulletList', 'content': [{'type': 'listItem', 'content': [123]}]}]}}
        with self.assertRaises(ValidationError): tr.valider(d)

    def test_paragraphes_listes_retours_et_numerotation(self):
        d = {'version': 1, 'doc': {'type': 'doc', 'content': [
            {'type': 'paragraph', 'content': [{'type': 'text', 'text': 'A'}, {'type': 'hardBreak'}, {'type': 'text', 'text': 'B'}]},
            {'type': 'orderedList', 'attrs': {'start': 3}, 'content': [{'type': 'listItem', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'C'}]}]}]}]}}
        self.assertEqual(tr.texte_simple(tr.valider(d)), 'A\nB\nC')
        self.assertIn('<ol start="3"><li>', tr.rendre('', d))

    def test_formulaire_autorite_du_document_et_erreur_conservee(self):
        champ = tr.ChampTexte(max_length=20)
        v = champ.clean(('projection falsifiée', json.dumps(document())))
        self.assertEqual(v, 'Texte fictif')
        self.assertIsNotNone(v.document)
        with self.assertRaises(ValidationError): champ.clean(('conservé', '{'))
        html = str(champ.widget.render('texte', ('conservé', '{'), {'id': 'id_texte'}))
        self.assertIn('conservé', html)
        html = str(champ.widget.render('texte', valeur('<fictif>'), {'id': 'id_texte'}))
        self.assertIn('readonly', html); self.assertNotIn('<fictif>', html)
