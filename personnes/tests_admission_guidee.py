from datetime import date
from unittest.mock import patch
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase
from django.urls import reverse
from . import tests_hebergement, admission, hebergement as h
from .models import Personne, AccordHebergement, Sejour, Affectation, OperationHebergement, RepasDistribue


class AdmissionGuideeTests(TestCase):
    def setUp(self):
        tests_hebergement.Donnees.preparer(self)
        self.enfant = Personne.objects.create(designation='Enfant fictif', cree_par=self.u)
        self.a.beneficiaires.add(self.enfant)
        self.client.force_login(self.u)

    def accueillir(self, **kw):
        self.a.refresh_from_db()
        valeurs = dict(beneficiaires=[self.p, self.enfant], debut=date(2026,2,1), fin=date(2026,3,1),
            admission=date(2026,2,3), attendu=admission.jeton(self.a), lieu=self.lieu)
        valeurs.update(kw)
        return admission.accueillir(self.u, self.a, **valeurs)

    def test_accord_admissions_individuelles_et_affectations_sans_repas(self):
        accord = self.accueillir()
        self.assertEqual(accord.debut, date(2026,2,1))
        self.assertEqual(accord.sejours.count(), 2)
        for s in accord.sejours.all():
            self.assertEqual(s.beneficiaires.count(), 1)
            self.assertEqual(s.debut, date(2026,2,3))
            self.assertEqual(s.affectations.get().lieu, self.lieu)
        self.assertFalse(RepasDistribue.objects.exists())
        self.assertFalse(self.a.accords_repas.exists())
        self.assertEqual(self.s.beneficiaires.count(), 1)
        self.assertIsNone(self.s.fin)

    def test_sans_lieu_et_sans_droit_affectation(self):
        self.u.user_permissions.remove(*self.u.user_permissions.filter(codename='add_affectation'))
        self.u = type(self.u).objects.get(pk=self.u.pk)
        accord = self.accueillir(lieu=None)
        self.assertFalse(Affectation.objects.filter(sejour__accord=accord).exists())
        self.assertEqual(accord.sejours.count(), 2)
        with self.assertRaises(PermissionDenied): self.accueillir()

    def test_mauvaise_date_et_echec_affectation_annulent_tout(self):
        avant = (AccordHebergement.objects.count(), Sejour.objects.count(), OperationHebergement.objects.count())
        with self.assertRaises(ValidationError): self.accueillir(admission=date(2026,3,1))
        ajouter = h.ajouter_periode
        appels = 0
        def affecter(*args, **kwargs):
            nonlocal appels
            appels += 1
            if appels == 2:
                raise ValidationError('Deuxième affectation indisponible')
            return ajouter(*args, **kwargs)
        with patch('personnes.admission.h.ajouter_periode', side_effect=affecter):
            with self.assertRaises(ValidationError): self.accueillir()
        self.assertEqual(appels, 2)
        self.assertFalse(Affectation.objects.exists())
        self.assertEqual((AccordHebergement.objects.count(), Sejour.objects.count(), OperationHebergement.objects.count()), avant)

    def test_rejeu_et_changement_beneficiaires_refuses(self):
        attendu = admission.jeton(self.a)
        self.accueillir(attendu=attendu)
        with self.assertRaises(ValidationError): self.accueillir(attendu=attendu)
        self.a.refresh_from_db()
        attendu = admission.jeton(self.a)
        self.a.beneficiaires.remove(self.enfant)
        with self.assertRaises(ValidationError): self.accueillir(attendu=attendu, beneficiaires=[self.p])
        self.assertEqual(AccordHebergement.objects.count(), 2)

    def test_http_erreurs_et_refus_direct_sans_droits(self):
        url = reverse('suivi:admission_guidee', args=[self.a.pk])
        self.assertContains(self.client.get(url), 'Enregistrer le séjour')
        valeurs = {'beneficiaires': [str(self.p.pk)], 'debut': '2026-02-01', 'fin': '2026-03-01',
            'admission': '2026-02-03', 'arrivee_effectuee': 'on', 'lieu': '', 'attendu': admission.jeton(self.a)}
        reponse = self.client.post(url, valeurs)
        self.assertEqual(reponse.status_code, 302)
        self.assertContains(self.client.post(url, valeurs), 'Aucun accord', status_code=409)
        self.u.user_permissions.clear()
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, valeurs).status_code, 403)


from django.test import TransactionTestCase


class ConcurrenceAdmissionGuidee(TransactionTestCase):
    def test_double_envoi_ne_cree_quun_accord_et_deux_sejours(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections, OperationalError
        AdmissionGuideeTests.setUp(self)
        attendu = admission.jeton(self.a)
        depart = Barrier(2)
        def envoyer(_):
            close_old_connections()
            try:
                acteur = type(self.u).objects.get(pk=self.u.pk)
                acteur.get_all_permissions()
                depart.wait(10)
                try:
                    admission.accueillir(acteur, self.a, [self.p, self.enfant], date(2026,2,1),
                        date(2026,3,1), date(2026,2,3), attendu, self.lieu)
                    return True
                except (ValidationError, OperationalError):
                    return False
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultats = list(pool.map(envoyer, range(2)))
        self.assertEqual(sum(resultats), 1)
        self.assertEqual(AccordHebergement.objects.count(), 2)
        self.assertEqual(Sejour.objects.count(), 3)
        self.assertEqual(Affectation.objects.count(), 2)
