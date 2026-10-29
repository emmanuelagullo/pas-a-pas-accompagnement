from django.test import TestCase,Client
from django.urls import reverse
from django.http import QueryDict
from django.utils import timezone
from acteurs import tests as anciens,notifications as notifications
from acteurs.models import Notification,Habilitation,Responsabilite,Service
from acteurs.contexte import perimetre
from . import models as m,liaisons as s,mentions_liaisons as mentions,transmissions

class MentionsTests(TestCase):
    setUp=anciens.AccesTests.setUp
    compte=anciens.AccesTests.compte
    dossier=anciens.AccesTests.dossier
    def connexion(self,u=None):
        c=Client();c.force_login(u or self.ua);return c
    def url(self,nature='menage',pk=None,route='suivi:cahier'):
        return reverse(route)+'?'+s.urlencode({'lia_cible':nature,'lia_id':str(pk or self.ma.pk)})
    def proposition(self,nature='menage',pk=None):
        return self.connexion().get(self.url(nature,pk,'suivi:mentions')+'&q=collegue').json()['collegues'][0]
    def publier(self,nature='menage',pk=None,token=None,contenu=None):
        c=self.connexion();url=self.url(nature,pk);envoi=c.get(url).context['form']['lia_envoi'].value()
        candidat=self.proposition(nature,pk)
        data={'contenu':contenu or '@'+candidat['label']+' Merci de regarder.', 'lia_envoi':envoi,'lia_mentions':token or candidat['jeton']}
        return c,url,data
    def test_mention_notifie_une_fois_avec_lien_exact_et_signal_visible(self):
        c,url,data=self.publier();self.assertEqual(c.post(url,data).status_code,302);self.assertEqual(c.post(url,data).status_code,302)
        self.assertEqual(Notification.objects.filter(compte=self.uc,nature='mention').count(),1)
        with perimetre(self.uc):n=next(x for x in notifications.visibles(self.uc) if x.nature=='mention')
        self.assertIn('lia_focus=message-notepartagee-',n.url)
        cible=self.connexion(self.uc);r=cible.get(reverse('accueil'));self.assertContains(r,'aria-label="Notifications non lues"')
        self.assertEqual(cible.post(reverse('acteurs:notification_lue',args=[n.pk]),{'attendu':n.attendu}).status_code,302)
        self.assertNotContains(cible.get(reverse('accueil')),'aria-label="Notifications non lues"')
    def test_autre_service_et_coordination_jamais_proposes(self):
        self.assertEqual(self.connexion().get(self.url(route='suivi:mentions')+'&q=camille').json()['collegues'],[])
        self.compte('collegue-coordination',self.sa,tache='coordination',statistiques_service=True)
        noms=[x['label'] for x in self.connexion().get(self.url(route='suivi:mentions')+'&q=collegue').json()['collegues']]
        self.assertEqual(noms,[str(self.pc)])
        self.assertEqual(self.connexion().get(self.url(pk=self.mb.pk,route='suivi:mentions')+'&q=camille').status_code,404)
    def test_changement_politique_entre_proposition_et_publication(self):
        c,url,data=self.publier();Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin)
        Service.objects.filter(pk=self.sa.pk).update(politique='individuel')
        self.assertEqual(c.post(url,data).status_code,409)
        self.assertFalse(m.NotePartagee.objects.filter(contenu=data['contenu']).exists())
        self.assertFalse(Notification.objects.filter(nature='mention').exists())
    def test_mention_revoquee_ou_deplacee_et_texte_retire(self):
        c,url,data=self.publier();Habilitation.objects.filter(compte=self.uc).update(revoque_le=timezone.now())
        self.assertEqual(c.post(url,data).status_code,409)
        self.assertEqual(c.post(self.url('prise',self.a.pk),data).status_code,409)
        data['contenu']='Sans mention désormais';self.assertEqual(c.post(url,data).status_code,302)
        self.assertFalse(Notification.objects.filter(nature='mention').exists())
    def test_service_general_sans_dossier_et_annulation(self):
        c,url,data=self.publier('service',self.sa.pk);self.assertEqual(c.post(url,data).status_code,302)
        n=Notification.objects.get(nature='mention');self.assertIsNone(n.dossier_id)
        with perimetre(self.uc):self.assertEqual(len(notifications.visibles(self.uc)),1)
        message=m.Transmission.objects.get(contenu=data['contenu'])
        with perimetre(self.ua):transmissions.annuler(self.ua,message,transmissions.jeton(message),'Doublon')
        with perimetre(self.uc):self.assertEqual(notifications.visibles(self.uc),[])
    def test_les_mentions_ne_donnent_aucun_acces_apres_relais(self):
        c,url,data=self.publier();self.assertEqual(c.post(url,data).status_code,302)
        Service.objects.filter(pk=self.sa.pk).update(politique='individuel')
        with perimetre(self.uc):self.assertEqual(notifications.visibles(self.uc),[])
        self.assertNotContains(self.connexion(self.uc).get(reverse('acteurs:notifications')),'Merci de regarder')

    def test_mission_prestation_ne_donne_pas_les_messages_du_dossier(self):
        Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin)
        Responsabilite.objects.create(dossier=self.da,hebergement=self.h,professionnel=self.pc,cree_par=self.admin)
        Service.objects.filter(pk=self.sa.pk).update(politique='individuel')
        c=self.connexion()
        self.assertEqual(c.get(self.url(route='suivi:mentions')+'&q=collegue').json()['collegues'],[])
        self.assertEqual(len(c.get(self.url('hebergement',self.h.pk,'suivi:mentions')+'&q=collegue').json()['collegues']),1)
