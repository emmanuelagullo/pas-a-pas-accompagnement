from datetime import date
from django.test import TestCase,Client
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import PermissionDenied,ValidationError
from acteurs import tests as anciens,notifications
from acteurs.models import Responsabilite,Service,Notification,Habilitation
from acteurs.contexte import perimetre
from . import models as m,liaisons as s,transmissions,fils_liaisons as fils
from . import tests_liaisons as anciennes_liaisons

class FilsTests(TestCase):
    setUp=anciens.AccesTests.setUp
    compte=anciens.AccesTests.compte
    dossier=anciens.AccesTests.dossier
    creer=anciennes_liaisons.CahierTests.creer
    donnees=anciennes_liaisons.CahierTests.donnees
    lire=anciennes_liaisons.CahierTests.lire
    def connexion(self,u=None):
        c=Client();c.force_login(u or self.ua);return c
    def cle(self,note):return 'message-notepartagee-'+str(note.pk)
    def url(self,cle,nature='menage',pk=None):
        return reverse('suivi:cahier')+'?'+s.urlencode({'lia_cible':nature,'lia_id':str(pk or self.ma.pk),'lia_periode':'toutes','lia_repondre':cle})
    def repondre(self,note=None,texte='Réponse partagée',jetons=None):
        note=note or self.note_dossier;c=self.connexion();url=self.url(self.cle(note));r=c.get(url)
        self.assertEqual(r.status_code,200)
        token=r.context['form']['lia_envoi'].value()
        data={'contenu':texte,'lia_envoi':token,'lia_mentions':jetons or []}
        self.assertEqual(c.post(url,data).status_code,302)
        return m.NotePartagee.objects.get(contenu=texte),c,url,data
    def test_reponses_sous_racine_sans_double_entree_et_sans_notifications_automatiques(self):
        self.creer();Responsabilite.objects.create(dossier=self.da,professionnel=self.pc,cree_par=self.admin);Notification.objects.all().delete()
        r,c,url,data=self.repondre();self.assertEqual(r.fil_cle,self.cle(self.note_dossier))
        self.assertEqual(c.post(url,data).status_code,302)
        self.assertEqual(m.NotePartagee.objects.filter(fil_cle=r.fil_cle).count(),1)
        self.assertFalse(Notification.objects.exists())
        lignes=self.lire('menage',self.ma)
        ligne=next(x for x in lignes if x['cle']==r.fil_cle)
        self.assertEqual(len(ligne['reponses']),1);self.assertEqual(len(lignes),3)
        self.assertContains(c.get(reverse('suivi:cahier'),{'lia_cible':'menage','lia_id':str(self.ma.pk)}),'1 réponse')
    def test_recherche_dans_reponse_et_activite_recente_sur_message_ancien(self):
        self.creer();m.NotePartagee.objects.filter(pk=self.note_dossier.pk).update(date_fait=date(2020,1,1));self.note_dossier.refresh_from_db()
        r,*_=self.repondre(texte='Confirmation du rendez-vous jeudi')
        d=self.donnees();d['lia_q']='rendez-vous'
        with perimetre(self.ua):rows=s.selection(s.Point(self.ua,'menage',self.ma.pk),d)
        self.assertEqual(len(rows),1);self.assertTrue(rows[0]['fil_ouvert']);self.assertEqual(rows[0]['date'],date(2020,1,1))
        self.assertEqual(rows[0]['activite'],timezone.localdate())
    def test_racine_cachee_et_niveaux_superieurs_ne_fuient_pas(self):
        self.creer();self.repondre(texte='CONTENU DU DOSSIER')
        self.assertNotIn('CONTENU DU DOSSIER',str(self.lire('prise',self.a)))
        c=self.connexion(self.ub);self.assertIn(c.get(self.url(self.cle(self.note_dossier))).status_code,(403,404))
        Service.objects.filter(pk=self.sa.pk).update(politique='individuel')
        self.assertIn(self.connexion(self.uc).get(self.url(self.cle(self.note_dossier))).status_code,(403,404))
    def test_pas_de_sous_fil_ni_de_reponse_sur_message_annule(self):
        self.creer();r,*_=self.repondre()
        self.assertEqual(self.connexion().get(self.url(self.cle(r))).status_code,403)
        with perimetre(self.ua):transmissions.annuler(self.ua,self.note_dossier,transmissions.jeton(self.note_dossier),'Saisi par erreur')
        self.assertEqual(self.connexion().get(self.url(self.cle(self.note_dossier))).status_code,403)
    def test_aucun_deplacement_de_portee_par_service_python(self):
        self.creer()
        with perimetre(self.ua,self.sa):
            with self.assertRaises(PermissionDenied):transmissions.noter(self.ua,'INTERDIT',accompagnement=self.a,fil_cle=self.cle(self.note_dossier))
            with self.assertRaises(PermissionDenied):transmissions.noter(self.ua,'INTERDIT',menage=self.ma,fil_cle=self.cle(self.autre))
        self.assertFalse(m.NotePartagee.objects.filter(contenu='INTERDIT').exists())
    def test_repondre_aux_evenements_d_attribution(self):
        self.creer();r=Responsabilite.objects.create(dossier=self.da,professionnel=self.pc,cree_par=self.ua)
        url=self.url('attribution-'+str(r.pk));c=self.connexion();token=c.get(url).context['form']['lia_envoi'].value()
        self.assertEqual(c.post(url,{'contenu':'Relais effectué','lia_envoi':token}).status_code,302)
        self.assertTrue(m.NotePartagee.objects.filter(fil_cle='attribution-'+str(r.pk),menage=self.ma).exists())
    def test_mention_reponse_ouvre_le_fil_et_la_reponse_exacte(self):
        self.creer();c=self.connexion();q=c.get(reverse('suivi:mentions'),{'lia_cible':'menage','lia_id':str(self.ma.pk),'q':'collegue'}).json()['collegues'][0]
        r,*_=self.repondre(texte='@'+q['label']+' Merci',jetons=[q['jeton']])
        with perimetre(self.uc):n=next(x for x in notifications.visibles(self.uc) if x.nature=='mention')
        self.assertIn('lia_fil='+self.cle(self.note_dossier),n.url);self.assertIn('lia_focus=reponse-notepartagee-',n.url)
        Habilitation.objects.filter(compte=self.uc).update(revoque_le=timezone.now())
        with perimetre(self.uc):self.assertEqual(notifications.visibles(self.uc),[])
    def test_correction_et_annulation_conservent_fil_et_histoire(self):
        self.creer();r,*_=self.repondre()
        with perimetre(self.ua):
            transmissions.rectifier(self.ua,r,'Réponse corrigée','Précision',etat_attendu=transmissions.jeton(r));r.refresh_from_db()
            transmissions.annuler(self.ua,r,transmissions.jeton(r),'Erreur')
        rows=self.lire('menage',self.ma);x=next(x for x in rows if x['cle']==r.fil_cle);self.assertEqual(x['reponses'],[])
        d=self.donnees();d['lia_annules']=True
        with perimetre(self.ua):x=next(x for x in s.selection(s.Point(self.ua,'menage',self.ma.pk),d) if x['cle']==r.fil_cle)
        self.assertEqual(len(x['reponses']),1);self.assertTrue(m.RevisionContribution.objects.filter(note=r).exists())

    def test_reponse_de_service_sans_dossier(self):
        self.creer();cle='message-transmission-'+str(self.general.pk)
        c=self.connexion();url=self.url(cle,'service',self.sa.pk);token=c.get(url).context['form']['lia_envoi'].value()
        self.assertEqual(c.post(url,{'contenu':'Réponse du service','lia_envoi':token}).status_code,302)
        r=m.Transmission.objects.get(contenu='Réponse du service');self.assertEqual(r.fil_cle,cle)
        self.assertIsNone(s.origine(r).dossier_id)

    def test_action_terminee_conserve_sa_discussion(self):
        from . import releve
        with perimetre(self.ua,self.sa):action=releve.creer_action(self.ua,'Rendez-vous',None)
        cle='action-'+str(action.pk);c=self.connexion();url=self.url(cle,'service',self.sa.pk);token=c.get(url).context['form']['lia_envoi'].value()
        self.assertEqual(c.post(url,{'contenu':'Rendez-vous confirmé','lia_envoi':token}).status_code,302)
        m.ActionRelais.objects.filter(pk=action.pk).update(terminee_le=timezone.now())
        with perimetre(self.ua,self.sa):rows=s.selection(s.Point(self.ua,'service',self.sa.pk),self.donnees('actions'))
        x=next(x for x in rows if x['cle']==cle);self.assertIn('Action terminée',x['titre']);self.assertEqual(len(x['reponses']),1)


from django.test import TransactionTestCase
class CopieFilsTests(TransactionTestCase):
    setUp=anciens.AccesTests.setUp
    compte=anciens.AccesTests.compte
    dossier=anciens.AccesTests.dossier
    def test_copie_sqlite_reouverte_conserve_fil_et_revalide_habilitation(self):
        from django.db import connection
        if connection.vendor!='sqlite':self.skipTest('Copie SQLite.')
        import sqlite3,tempfile,subprocess,sys
        from pathlib import Path
        from contextlib import closing
        with perimetre(self.ua,self.sa):
            note=transmissions.noter(self.ua,'Racine de copie',menage=self.ma)
            cle='message-notepartagee-'+str(note.pk)
            reponse=transmissions.noter(self.ua,'Réponse de copie',menage=self.ma,fil_cle=cle)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'copie.sqlite3'
            with closing(sqlite3.connect(path)) as db:connection.connection.backup(db)
            code='''
import sys,django
from django.conf import settings
settings.DATABASES['default']['NAME']=sys.argv[1]
django.setup()
from django.contrib.auth import get_user_model
from django.utils import timezone
from acteurs.contexte import perimetre
from acteurs.models import Habilitation
from personnes import liaisons as s,fils_liaisons as fils
u=get_user_model().objects.get(pk=sys.argv[2])
with perimetre(u):
    rows=s.selection(s.Point(u,'menage',sys.argv[3]),fils.donnees())
    fil=next(x for x in rows if x['cle']==sys.argv[4]);assert len(fil['reponses'])==1
Habilitation.objects.filter(compte=u).update(revoque_le=timezone.now())
with perimetre(u):
    from personnes.models import Menage
    assert not Menage.objects.filter(pk=sys.argv[3]).exists()
'''
            subprocess.run([sys.executable,'-c',code,str(path),str(self.uc.pk),str(self.ma.pk),cle],check=True,capture_output=True,text=True)
