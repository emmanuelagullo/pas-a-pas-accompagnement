from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from . import models as m, social, repas
from .demonstration import generer, preparer_jeu_public


class DemonstrationTests(TestCase):
    def test_cas_limites_et_composition_sans_benefice_implicite(self):
        from . import interventions
        u=get_user_model().objects.create_user('recette-etendue')
        suivis=generer(u);jour=timezone.localdate()
        self.assertEqual(m.Accompagnement.objects.count(),51)
        self.assertEqual(m.Personne.objects.filter(designation='Robin (fictif)').count(),2)
        noe=m.Personne.objects.get(designation='Noé (fictif)')
        self.assertTrue(suivis['Cam'].beneficiaires.filter(pk=noe.pk).exists())
        self.assertFalse(suivis['Aïcha'].beneficiaires.filter(pk=noe.pk).exists())
        self.assertTrue(suivis['Aïcha'].menage.appartenances.filter(personne=noe,debut=jour-timedelta(days=3)).exists())
        self.assertEqual(suivis['Louise'].beneficiaires.count(),5)
        self.assertEqual(suivis['Louise'].menage.appartenances.count(),6)
        ines=m.Personne.objects.get(designation='Inès (fictif)')
        self.assertFalse(ines.appartenances.exists());self.assertFalse(ines.accompagnements.exists())
        self.assertEqual(ines.precision_naissance,'')
        self.assertEqual(m.TypeAide.objects.count(),8)
        retrait=m.AnnulationArrivee.objects.get()
        self.assertTrue(retrait.origine.accord.annule_le)
        self.assertTrue(retrait.origine.annule_le)
        self.assertTrue(retrait.origine.affectations.exists())
        self.assertTrue(m.RemiseAide.objects.filter(annule_le__isnull=False).exists())
        self.assertTrue(m.UsageAide.objects.filter(quantite=0).exists())
        self.assertTrue(m.AccordRepas.objects.filter(jours_semaine=[2,4]).exists())
        self.assertEqual(m.Intervenant.objects.count(),3)
        self.assertEqual(m.DemandeAccueil.objects.count(),10)
        self.assertEqual(m.DemandeAccueil.objects.filter(accompagnement__isnull=False).count(),5)
        self.assertEqual(m.OrientationParcours.objects.count(),3)
        self.assertEqual(m.ObjectifParcours.objects.filter(annule_le__isnull=False).count(),1)
        objectif=m.ObjectifParcours.objects.get(versions__titre='Trouver un logement autonome — Maïa (fictif)',versions__fin__isnull=True)
        self.assertEqual(list(objectif.versions.order_by('debut').values_list('etat',flat=True)),['encours','suspendu','encours','atteint'])
        self.assertTrue(m.RevisionDemande.objects.filter(action='correction').exists())
        self.assertTrue(m.ObjectifParcours.objects.filter(accompagnement__fin__isnull=False,versions__etat='encours',versions__fin__isnull=True).exists())
        for nom in ('Noor','Samira','Thomas','Robin A','Robin B','Léo'):
            self.assertEqual(suivis[nom].menage.accompagnements.count(),5)
        for a in suivis['Noor'].menage.accompagnements.filter(debut__lt=jour-timedelta(days=200)):
            self.assertTrue(a.accords_hebergement.exists())
            self.assertEqual(a.accords_repas.count(),2)
        self.assertFalse(interventions.a_date(suivis['Alex'],jour).exists())
        self.assertEqual(suivis['Alex'].interventions.filter(annule_le__isnull=False).count(),1)

    def test_coherence_et_operation_laissee_libre(self):
        u = get_user_model().objects.create_user('essai-prive')
        jour = timezone.localdate()
        suivis = generer(u)
        self.assertEqual(m.Personne.objects.count(), 36)
        self.assertEqual(m.Menage.objects.count(), 18)
        self.assertEqual(m.Accompagnement.objects.filter(fin__isnull=True).count(), 12)
        alex = suivis['Alex']
        self.assertFalse(alex.accords_hebergement.exists())
        accord = alex.accords_repas.get()
        self.assertEqual(accord.realisations.count(), 2)
        u = get_user_model().objects.get(pk=u.pk)
        repas.distribuer(u, accord, alex.beneficiaires.get(), jour, 1)
        famille = suivis['Samira']
        sejour = famille.accords_hebergement.get().sejours.get()
        self.assertEqual(sejour.beneficiaires.count(), 3)
        self.assertIsNone(sejour.fin)
        affectations = list(sejour.affectations.order_by('debut'))
        self.assertEqual(affectations[0].fin, affectations[1].debut)
        self.assertTrue(affectations[1].lieu.partenaire)
        self.assertEqual(sejour.absences.get().fin, jour - timedelta(days=5))
        self.assertEqual(famille.accords_repas.get().realisations.count(), 3)
        thomas = suivis['Thomas']
        self.assertIsNotNone(thomas.accords_hebergement.get().sejours.get().fin)
        self.assertIsNone(thomas.fin)
        self.assertEqual(social.etat_date(thomas, jour).get(dimension='logement').valeur, 'logement_autonome')
        self.assertEqual(social.etat_date(thomas, jour-timedelta(days=11)).get(dimension='logement').valeur, 'hebergement')
        self.assertEqual(thomas.bilans_sociaux.count(), 1)
        with self.assertRaises(ValidationError):
            generer(u)
        self.assertEqual(m.Personne.objects.count(), 36)

    @override_settings(DEMONSTRATION_PUBLIQUE=True)
    def test_comptes_publics_droits_explicites_et_refus_de_reset(self):
        call_command('preparer_demonstration', stdout=StringIO())
        comptes = list(get_user_model().objects.all())
        self.assertEqual(len(comptes), 4)
        droits = comptes[0].get_all_permissions()
        self.assertIn('personnes.add_situationsociale', droits)
        self.assertNotIn('personnes.delete_personne', droits)
        for u in comptes:
            self.assertFalse(u.is_superuser or u.is_staff)
            self.assertEqual(u.get_all_permissions(), droits)
        self.assertTrue(m.OperationRepas.objects.filter(auteur__username='camille').exists())
        self.assertTrue(m.OperationHebergement.objects.filter(auteur__username='remi').exists())
        self.assertTrue(m.OperationSociale.objects.filter(auteur__username='nadia').exists())
        with self.assertRaises(CommandError):
            call_command('preparer_demonstration', stdout=StringIO())
        self.assertEqual(get_user_model().objects.count(), 4)

    def test_commande_absente_du_profil_ordinaire(self):
        with self.assertRaises(CommandError):
            call_command('preparer_demonstration', stdout=StringIO())
        self.assertFalse(get_user_model().objects.exists())

    @override_settings(MODE_LOCAL=True)
    def test_ancien_champ_ignore_et_espace_du_premier_patch_conserve(self):
        self.assertEqual(self.client.get(reverse('decouverte')).status_code, 302)
        reponse = self.client.post(reverse('installation_locale'), {'username': 'visiteur',
            'password1': 'Un-essai-prive-solide-2026!', 'password2': 'Un-essai-prive-solide-2026!', 'demonstration': 'on'})
        self.assertRedirects(reponse, reverse('personnes:liste'))
        self.assertEqual(get_user_model().objects.count(), 1)
        u = get_user_model().objects.get()
        self.assertFalse(u.is_superuser or u.is_staff)
        self.assertFalse(u.has_perm('personnes.add_repasdistribue'))
        self.assertEqual(m.Personne.objects.count(), 0)
        # État du premier patch : le jeu dans l’espace habituel reste utilisable.
        generer(u)
        self.assertEqual(m.Personne.objects.count(), 36)
        self.assertContains(self.client.get(reverse('decouverte')), 'Les Passerelles')
        self.assertEqual(self.client.post(reverse('installation_locale'), {}).status_code, 404)
        sans_droit = get_user_model().objects.create_user('sans-droit')
        self.client.force_login(sans_droit)
        self.assertEqual(self.client.get(reverse('decouverte')).status_code, 403)
        self.assertEqual(self.client.get(reverse('suivi:liste')).status_code, 403)
        accord = m.AccordRepas.objects.first()
        self.assertEqual(self.client.post(reverse('suivi:distribuer_repas', args=[accord.pk]), {}).status_code, 403)

    def test_echec_generation_annule_aussi_les_comptes_publics(self):
        with patch('personnes.demonstration.generer', side_effect=RuntimeError('échec simulé')):
            with self.assertRaises(RuntimeError):
                preparer_jeu_public()
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(m.Personne.objects.exists())

    @override_settings(OUTILS_COPIES_BUREAU=True, ESPACE_ESSAI=True)
    def test_selecteur_bureau_avant_connexion_et_bandeau(self):
        r = self.client.get(reverse('choisir_espace_local'))
        self.assertContains(r, 'Revenir à mon espace habituel')
        self.assertContains(r, 'data-espace="habituel"')
        self.assertContains(r, 'Comptes du jeu de départ')
        with override_settings(ESPACE_ESSAI=False):
            self.assertContains(self.client.get(reverse('choisir_espace_local')), 'data-espace="essai"')
        with override_settings(MODE_PWA=True):
            self.assertEqual(self.client.get(reverse('choisir_espace_local')).status_code, 404)
        with override_settings(OUTILS_COPIES_BUREAU=False):
            self.assertEqual(self.client.get(reverse('choisir_espace_local')).status_code, 404)


class DemonstrationStatistiquesTests(TestCase):
    """Contrat métier chiffré de la démonstration, indépendant des UUID."""

    def test_bilan_fictif_sur_60_jours(self):
        from .statistiques import bilan, evolution_mensuelle, ventilation_repas
        jour = timezone.localdate()
        compte = get_user_model().objects.create_user('essai-statistiques')
        generer(compte, reference=jour)
        debut, fin = jour - timedelta(days=60), jour + timedelta(days=1)
        chiffres = bilan(debut, fin)
        # Ajouts : 2 × 28 = 56 nuitées ; trois petits déjeuners.
        for cle, attendu in {
            'menages_accompagnes': 18, 'accompagnements': 18,
            'personnes_avec_sejour': 6, 'sejours': 3,
            'admissions': 3, 'sorties': 2,
            'nuitees_theoriques': 215, 'nuits_distinctes': 215,
            'nuits_hors_absences_declarees': 209, 'repas_distribues': 8,
        }.items():
            with self.subTest(indicateur=cle):
                self.assertEqual(chiffres[cle], attendu)
        self.assertEqual(ventilation_repas(debut, fin)['dejeuner'], 2)
        self.assertEqual(ventilation_repas(debut, fin)['diner'], 3)
        lignes = evolution_mensuelle(debut, fin)
        for cle in ('admissions', 'sorties', 'nuitees_theoriques', 'repas_distribues'):
            self.assertEqual(sum(l[cle] for l in lignes), chiffres[cle])

    def test_navigation_et_export_de_la_demonstration(self):
        import csv
        from io import StringIO
        jour = timezone.localdate()
        compte = get_user_model().objects.create_user('essai-statistiques')
        generer(compte, reference=jour)
        self.client.force_login(compte)
        params = {'debut': (jour - timedelta(days=60)).isoformat(),
                  'fin': (jour + timedelta(days=1)).isoformat()}
        page = self.client.get(reverse('statistiques'), params)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, '215')
        self.assertContains(self.client.get(reverse('personnes:liste')), 'Statistiques')
        export = self.client.get(reverse('statistiques'), {**params, 'format': 'csv'})
        self.assertEqual(export.status_code, 200)
        lignes = list(csv.reader(StringIO(export.content.decode('utf-8'))))
        self.assertIn(['nuitees_theoriques', '215'], [ligne[-2:] for ligne in lignes])
        compte.user_permissions.clear()
        compte = get_user_model().objects.get(pk=compte.pk)
        self.client.force_login(compte)
        self.assertEqual(self.client.get(reverse('statistiques'), params).status_code, 403)
        self.assertEqual(self.client.get(reverse('statistiques'), {**params, 'format': 'csv'}).status_code, 403)

    def test_explorations_fictives_et_csv_par_categorie(self):
        import csv
        from io import StringIO
        from .statistiques import exploration_repas, exploration_affectations, regrouper_exploration
        jour = timezone.localdate()
        compte = get_user_model().objects.create_user('essai-exploration')
        generer(compte, reference=jour)
        debut, fin = jour - timedelta(days=60), jour + timedelta(days=1)
        repas = regrouper_exploration(exploration_repas(debut, fin),
                                      regroupement='categorie', categorie='service', mesure='quantite')
        self.assertEqual({ligne['service']: ligne['quantite'] for ligne in repas},
                         {'petit_dejeuner': 3, 'dejeuner': 2, 'diner': 3})
        affectations = regrouper_exploration(exploration_affectations(debut, fin),
                                            regroupement='categorie', categorie='lieu', mesure='nuitees')
        self.assertEqual(sum(ligne['nuitees'] for ligne in affectations), 215)
        self.assertEqual(len(affectations), 3)
        self.client.force_login(compte)
        params = {'debut': debut.isoformat(), 'fin': fin.isoformat(),
                  'regroupement': 'categorie'}
        for rapport, colonne, attendu in (
            ('exploration_repas', 'quantite_distribuee', 8),
            ('exploration_hebergement', 'nuitees_affectation_theoriques', 215),
        ):
            with self.subTest(rapport=rapport):
                page = self.client.get(reverse('statistiques'), {**params, 'rapport': rapport})
                self.assertEqual(page.status_code, 200)
                export = self.client.get(reverse('statistiques'),
                                         {**params, 'rapport': rapport, 'format': 'csv'})
                self.assertEqual(export.status_code, 200)
                lignes = list(csv.DictReader(StringIO(export.content.decode('utf-8'))))
                self.assertEqual(sum(int(ligne[colonne]) for ligne in lignes), attendu)
                self.assertNotIn('personne', export.content.decode('utf-8').lower())
        compte.user_permissions.clear()
        compte = get_user_model().objects.get(pk=compte.pk)
        self.client.force_login(compte)
        self.assertEqual(self.client.get(reverse('statistiques'),
                                         {**params, 'rapport': 'exploration_repas', 'format': 'csv'}).status_code, 403)
