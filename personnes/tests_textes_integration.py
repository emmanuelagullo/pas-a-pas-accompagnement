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

from .tests_textes_riches import document, valeur


class ParcoursTests(TestCase):
    def setUp(self):
        from .tests_navigation import NavigationTests
        NavigationTests.setUp(self)
        call_command('autoriser_chrs7', self.u.username, stdout=StringIO())
        call_command('autoriser_bd6', self.u.username, stdout=StringIO())
        from django.contrib.auth.models import Permission
        self.u.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes', codename__in=['view_transmission', 'add_transmission', 'change_transmission', 'view_notepartagee', 'add_notepartagee', 'change_notepartagee']))
        self.u = type(self.u).objects.get(pk=self.u.pk)

    def test_commentaire_versions_formulaire_et_conflit(self):
        from . import bd6
        from .models import CommentaireDossier
        url = reverse('dossiers:commentaire', args=['personne', self.p.pk])
        token = bd6.jeton(self.p)
        response = self.client.post(url, {'attendu': token, 'texte': 'projection', 'texte_document': json.dumps(document()), 'motif': ''})
        self.assertEqual(response.status_code, 302)
        premier = CommentaireDossier.objects.get()
        self.assertEqual(premier.texte, 'Texte fictif'); self.assertIsNotNone(premier.texte_document)
        page = self.client.get(reverse('dossiers:detail', args=['personne', self.p.pk]))
        self.assertContains(page, '<strong>Texte fictif</strong>', html=True)
        self.assertContains(self.client.get(url), 'readonly')
        response = self.client.post(url, {'attendu': token, 'texte': 'à conserver', 'texte_document': json.dumps(document('Saisie conservée')), 'motif': 'Précision'})
        self.assertEqual(response.status_code, 409)
        self.assertContains(response, 'Saisie conservée', status_code=409)
        self.assertEqual(CommentaireDossier.objects.count(), 1)
        bd6.commenter(self.u, self.p, valeur(' ', None), 'Effacement fictif', bd6.jeton(self.p))
        self.assertContains(self.client.get(reverse('dossiers:detail', args=['personne', self.p.pk])), 'Commentaire effacé.')
        premier.refresh_from_db(); self.assertIsNotNone(premier.texte_document)

    def test_transmission_note_correction_formattage_seul_et_rollback(self):
        from . import transmissions as t
        from .models import RevisionContribution
        note = t.noter(self.u, valeur(), personne=self.p)
        token = t.jeton(note)
        t.rectifier(self.u, note, valeur(marque='italic'), 'Formulation lisible', etat_attendu=token)
        note.refresh_from_db()
        self.assertIn('<em>', tr.rendre(note.contenu, note.contenu_document))
        r = RevisionContribution.objects.get()
        self.assertEqual(r.ancien_texte, r.nouveau_texte)
        self.assertNotEqual(r.ancien_texte_document, r.nouveau_texte_document)
        with self.assertRaises(ValidationError): t.rectifier(self.u, note, valeur('Autre'), 'Périmé', etat_attendu=token)
        with patch.object(RevisionContribution.objects, 'create', side_effect=RuntimeError('fictif')):
            with self.assertRaises(RuntimeError): t.rectifier(self.u, note, valeur('Autre'), 'Fictif', etat_attendu=t.jeton(note))
        note.refresh_from_db(); self.assertEqual(note.contenu, 'Texte fictif')
        url = reverse('suivi:corriger_contribution', args=['note', note.pk])
        reponse = self.client.post(url, {'texte_attendu': note.contenu, 'etat_attendu': token,
            'contenu': 'à conserver', 'contenu_document': json.dumps(document('Saisie préservée')), 'motif': 'Fictif'})
        self.assertEqual(reponse.status_code, 409); self.assertContains(reponse, 'Saisie préservée', status_code=409)
        page = self.client.get(reverse('suivi:notes', args=['personne', self.p.pk]))
        self.assertContains(page, '<em>Texte fictif</em>', html=True)
        self.assertContains(page, '<strong>Texte fictif</strong>', html=True)
        t.transmettre(self.u, valeur('Relais fictif'))
        self.assertContains(self.client.get(reverse('suivi:cahier')), '<strong>Relais fictif</strong>', html=True)
        self.assertContains(self.client.get(reverse('suivi:jour')), '<strong>Relais fictif</strong>', html=True)

    def test_objectifs_versions_resume_imprimable_et_droits(self):
        from . import informations_suivi as service, bd6
        donnees = {champ: '' for champ in service.CHAMPS}
        donnees.update(objectifs_courts=valeur('Préparer le rendez-vous'), objectifs_longs=valeur('Projet fictif'))
        i = service.enregistrer(self.u, self.a, service.jeton(self.a, None), 'Projet fictif', **donnees)
        self.assertIsNotNone(i.objectifs_courts_document)
        url = reverse('suivi:informations', args=[self.a.pk])
        self.assertContains(self.client.get(url), 'readonly')
        bd6.commenter(self.u, self.a, valeur('Commentaire imprimé'), '', bd6.jeton(self.a))
        page = self.client.get(reverse('suivi:resume', args=[self.a.pk]))
        self.assertContains(page, '<strong>Préparer le rendez-vous</strong>', html=True)
        self.assertContains(page, '<strong>Commentaire imprimé</strong>', html=True)
        self.assertContains(page, 'textes-riches.css')
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(url).status_code, 403)
        with self.assertRaises(PermissionDenied): service.enregistrer(type(self.u).objects.get(pk=self.u.pk), self.a, '', 'Refus', **donnees)

    def test_bilan_correction_historique_trajectoire(self):
        from . import social, corrections
        from .models import RevisionTexteSocial
        b = social.bilan(self.u, self.a, date(2026, 2, 1), valeur('Bilan fictif'))
        token = corrections.jeton(b)
        corrections.texte(self.u, b, b.date_effet, valeur('Bilan fictif', 'italic'), 'Présentation', token)
        b.refresh_from_db()
        r = RevisionTexteSocial.objects.get(bilan=b)
        self.assertIsNotNone(r.ancien_texte_document); self.assertIsNotNone(r.nouveau_texte_document)
        with self.assertRaises(ValidationError): corrections.texte(self.u, b, b.date_effet, valeur('Autre'), 'Périmé', token)
        for nom in ('suivi:social', 'suivi:trajectoire', 'suivi:corrections'):
            self.assertContains(self.client.get(reverse(nom, args=[self.a.pk])), '<em>Bilan fictif</em>', html=True)

    def test_projet_vide_non_consigne_comme_modification(self):
        from . import informations_suivi as service
        with self.assertRaises(ValidationError):
            service.enregistrer(self.u, self.a, service.jeton(self.a, None), 'Sans changement', **{champ: '' for champ in service.CHAMPS})
        self.assertFalse(self.a.informations.exists())

    def test_post_objectifs_enrichis_et_bilan(self):
        from . import informations_suivi as service
        donnees = {champ: '' for champ in service.CHAMPS}
        donnees.update(attendu=service.jeton(self.a, None), motif='Projet fictif', objectifs_courts_document=json.dumps(document('Objectif enrichi')))
        self.assertEqual(self.client.post(reverse('suivi:informations', args=[self.a.pk]), donnees).status_code, 302)
        i = self.a.informations.first()
        self.assertEqual(i.objectifs_courts, 'Objectif enrichi'); self.assertIsNotNone(i.objectifs_courts_document)
        url = reverse('suivi:bilan_social', args=[self.a.pk])
        self.assertEqual(self.client.post(url, {'date_effet': '2026-02-01', 'texte': '', 'texte_document': json.dumps(document())}).status_code, 302)

    def test_refus_document_malveillant_sans_ecriture(self):
        from .models import Transmission
        d = document(); d['doc']['content'][0]['content'][0]['marks'] = [{'type': 'link', 'attrs': {'href': 'javascript:fictif'}}]
        response = self.client.post(reverse('suivi:cahier'), {'contenu': 'projection', 'contenu_document': json.dumps(d)})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transmission.objects.exists())
        self.assertContains(response, 'https://')


from django.test import TransactionTestCase


class ConcurrenceContributionsTests(TransactionTestCase):
    def test_deux_corrections_de_format_un_seul_succes(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections, OperationalError
        from .tests_transmissions import TransmissionsTests
        from . import transmissions as t
        from .models import RevisionContribution
        TransmissionsTests.setUp(self)
        note = t.noter(self.u, valeur(), personne=self.p)
        token = t.jeton(note)
        barriere = Barrier(2)
        def corriger(nouveau):
            close_old_connections()
            try:
                u = type(self.u).objects.get(pk=self.u.pk)
                u.get_all_permissions()
                barriere.wait(10)
                try:
                    t.rectifier(u, note, nouveau, 'Correction concurrente fictive', etat_attendu=token)
                    return True
                except (ValidationError, OperationalError):
                    return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultats = list(pool.map(corriger, [valeur(marque='italic'), valeur(marque=None)]))
        self.assertLessEqual(sum(resultats), 1)
        self.assertEqual(RevisionContribution.objects.filter(note=note).count(), sum(resultats))
        # SQLite partagé en mémoire peut refuser les deux promotions de verrou.
        # Après refus explicites, un réessai volontaire reste possible, sans
        # journal partiel ni double correction issue du même état.
        if not any(resultats):
            note.refresh_from_db()
            self.assertEqual(note.contenu_document, valeur().document)
            t.rectifier(self.u, note, valeur(marque='italic'), 'Réessai volontaire fictif', etat_attendu=token)
        with self.assertRaises(ValidationError):
            t.rectifier(self.u, note, valeur('Écrasement'), 'Périmé', etat_attendu=token)
        self.assertEqual(RevisionContribution.objects.filter(note=note).count(), 1)
