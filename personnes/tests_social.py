from datetime import date
from io import StringIO
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError,PermissionDenied
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from .models import Personne,SituationSociale,EvenementSocial,BilanSocial,OperationSociale
from . import social,suivi


class SocialTests(TestCase):
    def setUp(self):
        self.u=get_user_model().objects.create_user('social-fictif')
        call_command('autoriser_chrs4',self.u.username,stdout=StringIO())
        self.u=get_user_model().objects.get(pk=self.u.pk)
        self.p=Personne.objects.create(designation='Personne fictive',cree_par=self.u)
        m=suivi.creer_menage(self.u,'Ménage fictif',[self.p],date(2026,1,1))
        self.a=suivi.ouvrir(self.u,m,[self.p],date(2026,1,1))

    def renseigner(self,valeur='sans_emploi',debut=date(2026,1,1),**kw):
        return social.renseigner(self.u,self.a,self.p,'emploi',valeur,debut,'Déclaration fictive',**kw)

    def test_etats_dates_et_evenement_independant(self):
        initial=self.renseigner()
        social.evenement(self.u,self.a,self.p,date(2026,2,1),'Début de contrat fictif','Déclaration fictive')
        self.assertEqual(social.etat_date(self.a,date(2026,2,2)).get().valeur,'sans_emploi')
        nouveau=self.renseigner('emploi',date(2026,2,1))
        initial.refresh_from_db()
        self.assertEqual(initial.fin,date(2026,2,1))
        self.assertEqual(social.etat_date(self.a,date(2026,1,31)).get(),initial)
        self.assertEqual(social.etat_date(self.a,date(2026,2,1)).get(),nouveau)
        social.bilan(self.u,self.a,date(2026,2,2),'Bilan fictif')
        self.assertEqual(BilanSocial.objects.count(),1)

    def test_correction_tracee_sans_changer_date(self):
        s=self.renseigner()
        social.corriger(self.u,s,'formation','Erreur de valeur')
        s.refresh_from_db()
        self.assertEqual(s.debut,date(2026,1,1))
        self.assertEqual(s.valeur,'formation')
        operation=OperationSociale.objects.get(action='Valeur corrigée')
        self.assertEqual(operation.ancienne_valeur,'sans_emploi')
        self.assertEqual(operation.nouvelle_valeur,'formation')
        with self.assertRaises(ValidationError):social.corriger(self.u,s,'emploi',' ')

    def test_refus_et_rollback(self):
        s=self.renseigner()
        for valeur,debut in [('emploi',date(2026,1,1)),('emploi',date(2025,12,1)),('logement_autonome',date(2026,2,1))]:
            with self.assertRaises(ValidationError):self.renseigner(valeur,debut)
        s.refresh_from_db();self.assertIsNone(s.fin)
        self.assertEqual(SituationSociale.objects.count(),1)
        autre=Personne.objects.create(designation='Autre fictif',cree_par=self.u)
        with self.assertRaises(ValidationError):social.evenement(self.u,self.a,autre,date(2026,1,2),'Texte fictif','Source fictive')
        self.assertFalse(EvenementSocial.objects.exists())
        from unittest.mock import patch
        with patch('personnes.social.timezone.localdate',return_value=date(2025,12,31)):
            with self.assertRaises(ValidationError):social.bilan(self.u,self.a,date(2026,1,2),'Bilan fictif')

    def test_cloture_ne_cache_pas_informations(self):
        self.renseigner('emploi',date(2026,2,1))
        with self.assertRaises(ValidationError):suivi.clore(self.u,self.a,date(2026,2,1))
        suivi.clore(self.u,self.a,date(2026,3,1))
        self.a.refresh_from_db()
        self.assertFalse(social.etat_date(self.a,date(2026,3,1)).exists())

    def test_parcours_http_et_droits(self):
        self.client.force_login(self.u)
        reponse=self.client.post(reverse('suivi:situation_sociale',args=[self.a.pk,'logement']),{
            'beneficiaire':self.p.pk,'valeur':'inconnu','debut':'2026-01-01','source':'Déclaration fictive','attendu':social.jeton_situations(self.a)})
        self.assertEqual(reponse.status_code,302)
        url=reverse('suivi:social',args=[self.a.pk])
        self.assertContains(self.client.get(url,{'date':'2026-01-02'}),'Non renseigné')
        self.assertContains(self.client.get(url,{'date':'invalide'}),'Saisissez une date valide')
        nu=get_user_model().objects.create_user('sans-social')
        self.client.force_login(nu)
        for cible in [url,reverse('suivi:situation_sociale',args=[self.a.pk,'emploi']),reverse('suivi:evenement_social',args=[self.a.pk]),reverse('suivi:bilan_social',args=[self.a.pk])]:
            self.assertEqual(self.client.get(cible).status_code,403)
        with self.assertRaises(PermissionDenied):social.bilan(nu,self.a,date(2026,1,2),'Texte fictif')

    def test_commande_cumulative_et_idempotente(self):
        avant=self.u.user_permissions.count()
        call_command('autoriser_chrs4',self.u.username,stdout=StringIO())
        self.assertEqual(self.u.user_permissions.count(),avant)
        self.assertTrue(self.u.has_perms(['personnes.add_accordrepas','personnes.add_sejour','personnes.add_situationsociale']))
        nu=get_user_model().objects.create_user('nouveau-sans-droit')
        self.assertFalse(nu.user_permissions.exists())

    def test_textes_echappes_et_visibilite(self):
        social.evenement(self.u,self.a,self.p,date(2026,1,2),'<script>fictif</script>','Source fictive')
        self.client.force_login(self.u)
        url=reverse('suivi:social',args=[self.a.pk])
        reponse=self.client.get(url)
        self.assertContains(reponse,'&lt;script&gt;fictif&lt;/script&gt;')
        self.assertNotContains(reponse,'<script>fictif</script>')
        self.u.user_permissions.remove(Permission.objects.get(content_type__app_label='personnes',codename='view_evenementsocial'))
        self.assertNotContains(self.client.get(url),'fictif&lt;/script&gt;')


from django.test import TransactionTestCase


class ConcurrenceSociale(TransactionTestCase):
    def test_deux_valeurs_a_la_meme_date(self):
        SocialTests.setUp(self)
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections,connections,OperationalError
        depart=Barrier(2)
        def ecrire(valeur):
            close_old_connections()
            try:
                u=get_user_model().objects.get(pk=self.u.pk)
                u.get_all_permissions()
                depart.wait(10)
                try:
                    social.renseigner(u,self.a,self.p,'emploi',valeur,date(2026,1,1),'Source fictive')
                    return True
                except (ValidationError,OperationalError):return False
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:resultats=list(pool.map(ecrire,['emploi','formation']))
        self.assertEqual(sum(resultats),1)
        self.assertEqual(SituationSociale.objects.count(),1)
        self.assertEqual(OperationSociale.objects.count(),1)

class TrajectoireTests(TestCase):
    setUp = SocialTests.setUp
    renseigner = SocialTests.renseigner
    """La trajectoire respecte le périmètre d'un suivi et les droits de lecture."""

    def test_filtrage_et_separation_des_dates(self):
        self.renseigner('sans_emploi', date(2026, 1, 1))
        social.evenement(self.u, self.a, self.p, date(2026, 2, 1), 'Événement fictif', 'Source fictive')
        social.bilan(self.u, self.a, date(2026, 2, 2), 'Bilan collectif fictif')
        self.client.force_login(self.u)
        url = reverse('suivi:trajectoire', args=[self.a.pk])
        self.assertContains(self.client.get(url), 'Bilan collectif fictif')
        reponse = self.client.get(url, {'beneficiaire': str(self.p.pk), 'debut': '2026-02-01', 'fin': '2026-02-01'})
        self.assertContains(reponse, 'Événement fictif')
        self.assertNotContains(reponse, 'Bilan collectif fictif')
        # Le filtre porte sur les événements datés ; la comparaison affiche
        # séparément la situation encore en vigueur à cette date.
        self.assertContains(reponse, 'Sans emploi')
        self.assertFalse(any('Sans emploi' in ligne['texte']
                             for ligne in reponse.context['lignes']))
        self.assertContains(self.client.get(url, {'fin': '2026-01-01', 'debut': '2026-02-01'}), 'La fin ne peut pas précéder')
        self.assertContains(self.client.get(url, {'beneficiaire': 'inconnu'}), 'Sélectionnez un choix valide')

    def test_droits_sur_la_trajectoire(self):
        social.evenement(self.u, self.a, self.p, date(2026, 2, 1), 'Événement réservé', 'Source fictive')
        self.client.force_login(self.u)
        url = reverse('suivi:trajectoire', args=[self.a.pk])
        self.assertContains(self.client.get(url), 'Événement réservé')
        permission = Permission.objects.get(content_type__app_label='personnes', codename='view_evenementsocial')
        self.u.user_permissions.remove(permission)
        self.u = get_user_model().objects.get(pk=self.u.pk)
        self.client.force_login(self.u)
        self.assertNotContains(self.client.get(url), 'Événement réservé')
        nu = get_user_model().objects.create_user('sans-trajectoire')
        self.client.force_login(nu)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_comparaison_datee_sans_inference(self):
        self.renseigner('sans_emploi', date(2026, 1, 1))
        self.renseigner('formation', date(2026, 2, 1))
        self.client.force_login(self.u)
        url = reverse('suivi:trajectoire', args=[self.a.pk])
        reponse = self.client.get(url, {'debut': '2026-01-15', 'fin': '2026-02-02'})
        self.assertContains(reponse, 'Sans emploi')
        self.assertContains(reponse, 'En formation')
        self.assertContains(reponse, 'Non renseigné')
        reponse = self.client.get(url, {'debut': '2026-01-15', 'fin': '2026-01-20'})
        self.assertNotContains(reponse, 'En formation')
