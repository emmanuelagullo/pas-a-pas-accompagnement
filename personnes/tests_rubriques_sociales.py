"""NAV3 : les aperçus ne redéfinissent ni les états ni les données."""
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils.html import escape
from .condition_sociale import apercu_rubrique
from . import models as m
from . import tests_condition_sociale as ancien


class ApercusTests(SimpleTestCase):
    def test_absence_non_connu_et_non_renseigne_distincts(self):
        self.assertEqual(apercu_rubrique([], collection=True), 'Non renseigné à cette date.')
        for etat, attendu in [('aucun', 'Absence déclarée'), ('inconnu', 'Non connu déclaré')]:
            fiche = {'fait': m.RessourcePersonnelle(etat=etat), 'resume': []}
            self.assertEqual(apercu_rubrique([fiche], collection=True), attendu)

    def test_liste_dans_un_champ_reste_un_compteur(self):
        fiche = {'resume': [{'nom': 'nationalites', 'label': 'Nationalités',
                            'nombre': 80, 'valeur': 'Collection longue'}]}
        self.assertEqual(apercu_rubrique([fiche]), 'Nationalités : 80 éléments')

    def test_collections_bornees_sans_somme_ni_diagnostic(self):
        fiches = [{'fait': m.RessourcePersonnelle(etat='detail'), 'resume': []} for _ in range(80)]
        fiches.append({'fait': m.RessourcePersonnelle(etat='aucun'), 'resume': []})
        self.assertEqual(apercu_rubrique(fiches, collection=True),
            '81 éléments enregistrés · 1 absence déclarée')

    def test_resume_fidele_borne_et_administration_sans_identifiant(self):
        resume = [{'nom':'ville', 'label':'Ville', 'valeur':'Bordeaux'},
                  {'nom':'telephone', 'label':'Téléphone', 'valeur':'06 11 11 11 11'},
                  {'nom':'fax', 'label':'Fax', 'valeur':'f'*400}]
        self.assertEqual(apercu_rubrique([{'resume': resume}], code='coordonnees'),
            'Ville : Bordeaux · Téléphone : 06 11 11 11 11')
        resume = [{'nom':'numero_ss', 'label':'Numéro', 'valeur':'IDENTIFIANT FICTIF'}]
        self.assertEqual(apercu_rubrique([{'resume': resume}], code='administration'),
            '1 champ renseigné')
        self.assertLess(len(apercu_rubrique([{'resume':[{'nom':'x','label':'Texte','valeur':'x'*400}]}])), 100)


class RubriquesHTMLTests(TestCase):
    setUpTestData = classmethod(ancien.ConditionSocialeTests.setUpTestData.__func__)
    setUp = ancien.ConditionSocialeTests.setUp

    def test_titres_ouverts_actions_hors_declencheur_et_cles_stables(self):
        from html.parser import HTMLParser
        class Lire(HTMLParser):
            def __init__(self):
                super().__init__(); self.summary = False; self.interactifs = []
            def handle_starttag(self, tag, attrs):
                if tag == 'summary': self.summary = True
                if self.summary and tag in ('a','button','input','select','textarea'): self.interactifs.append(tag)
            def handle_endtag(self, tag):
                if tag == 'summary': self.summary = False
        pour_prise = self.client.get(self.url)
        pour_dossier = self.client.get(reverse('dossiers:detail', args=['menage', self.m.pk]))
        for page in (pour_prise, pour_dossier):
            self.assertContains(page, '<details open data-condition-volet')
            self.assertContains(page, 'aria-labelledby="condition-volet-titre"')
            self.assertContains(page, 'data-condition-tout="ouvrir"')
            self.assertContains(page, 'data-condition-tout="fermer"')
            self.assertContains(page, '<details open id="social-' + str(self.p.pk) + '-identite"')
            self.assertContains(page, 'data-condition-repli="social-' + str(self.p.pk) + '-coordonnees"')
            self.assertContains(page, 'data-condition-repli="projet-objectifs"')
            parser = Lire(); parser.feed(page.content.decode())
            self.assertEqual(parser.interactifs, [])
        self.assertContains(pour_prise, 'data-condition-repli="informations-prise-' + str(self.a.pk) + '"')

    def test_apercus_echappes_et_preuve_sans_requete_supplementaire(self):
        self.p.designation = '<script>Nom fictif</script>'
        self.p.save(update_fields=['designation'])
        page = self.client.get(self.url)
        self.assertContains(page, escape(self.p.designation))
        self.assertNotContains(page, '<script>Nom fictif</script>')
        groupe = page.context['condition_personnes'][0]['groupes'][0]
        with self.assertNumQueries(0):
            self.assertEqual(apercu_rubrique(groupe['fiches'], code='identite'), groupe['apercu'])
