from datetime import date,timedelta
from django.test import TestCase,Client
from django.urls import reverse
from django.http import QueryDict
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from acteurs import tests as acteurs_tests,services as a,politique as p
from acteurs.models import Responsabilite,Service,Habilitation,PorteeObjet
from acteurs.contexte import perimetre
from . import models as m,transmissions,liaisons as s

class CahierTests(TestCase):
    setUp=acteurs_tests.AccesTests.setUp
    compte=acteurs_tests.AccesTests.compte
    dossier=acteurs_tests.AccesTests.dossier
    def donnees(self,types='messages',sous='1'):
        q=QueryDict('',mutable=True);jour=timezone.localdate();q.update({'lia_debut':(jour-timedelta(days=7)).isoformat(),'lia_fin':(jour+timedelta(days=1)).isoformat(),'lia_sous':sous,'lia_filtres':'1'});q.setlist('lia_types',types.split(','))
        f=s.filtres(q);self.assertTrue(f.is_valid(),f.errors);return f.cleaned_data
    def creer(self):
        with perimetre(self.ua,self.sa):
            self.note_dossier=transmissions.noter(self.ua,'Message du dossier',menage=self.ma)
            self.note_prise=transmissions.noter(self.ua,'Message de la prise',accompagnement=self.a)
            self.note_prestation=transmissions.noter(self.ua,'Message de la prestation',accord_hebergement=self.h)
            self.general=transmissions.transmettre(self.ua,'Message du service')
        with perimetre(self.ub,self.sb):self.autre=transmissions.noter(self.ub,'SECRET AUTRE SERVICE',menage=self.mb)
    def lire(self,nature,obj,types='messages',sous='1',u=None):
        u=u or self.ua
        with perimetre(u):return s.selection(s.Point(u,nature,obj.pk if obj else self.sa.pk),self.donnees(types,sous))
    def textes(self,rows):return [r['contribution'].contenu for r in rows if r['contribution']]
    def test_cahier_combine_vers_le_bas_pas_vers_le_haut(self):
        self.creer()
        self.assertCountEqual(self.textes(self.lire('menage',self.ma)),['Message du dossier','Message de la prise','Message de la prestation'])
        self.assertCountEqual(self.textes(self.lire('prise',self.a)),['Message de la prise','Message de la prestation'])
        self.assertEqual(self.textes(self.lire('hebergement',self.h)),['Message de la prestation'])
        self.assertEqual(self.textes(self.lire('prise',self.a,sous='0')),['Message de la prise'])
        self.assertEqual(len(self.lire('service',None)),4)
    def test_attributions_au_bon_niveau_et_auteur_message(self):
        r=a.ajouter_responsabilite(self.ua,self.da,self.da,self.pc,timezone.localdate(),'suivi',a.jeton(self.da),message='MESSAGE ÉQUIPE DOSSIER')
        rows=self.lire('menage',self.ma,'equipe');self.assertEqual(rows[0]['message'],r.message)
        self.assertFalse(self.lire('prise',self.a,'equipe'))
        self.assertEqual(rows[0]['auteur'],str(self.pa))
    def test_droits_avant_compteurs_recherche_fragments(self):
        self.creer();c=Client();c.force_login(self.ua)
        for fragment in ('','1'):
            r=c.get(reverse('suivi:cahier'),{'lia_fragment':fragment,'lia_q':'SECRET','lia_types':'messages'})
            self.assertNotContains(r,'SECRET AUTRE SERVICE');self.assertEqual(r.context['page_obj'].paginator.count,0)
        self.assertEqual(c.get(reverse('suivi:cahier'),{'lia_cible':'menage','lia_id':str(self.mb.pk)}).status_code,404)
    def test_prestation_seule_ne_voit_pas_message_du_dossier(self):
        self.creer();Service.objects.filter(pk=self.sa.pk).update(politique='individuel')
        Responsabilite.objects.create(dossier=self.da,hebergement=self.h,professionnel=self.pc,cree_par=self.admin)
        self.assertEqual(self.textes(self.lire('menage',self.ma,u=self.uc)),['Message de la prestation'])
        with perimetre(self.uc):self.assertFalse(s.Point(self.uc,'menage',self.ma.pk).ecriture())
    def test_affectation_metier_sans_tache_ne_revele_rien(self):
        coord,prof=self.compte('coord-cahier',self.sa,tache='coordination',statistiques_service=True)
        Responsabilite.objects.create(dossier=self.da,professionnel=prof,cree_par=self.admin,message='SECRET ÉQUIPE')
        c=Client();c.force_login(coord)
        self.assertEqual(c.get(reverse('suivi:cahier')).status_code,403)
    def test_menage_contrainte_une_seule_cible(self):
        from django.core.exceptions import ValidationError
        with perimetre(self.ua,self.sa):
            with self.assertRaises(ValidationError):transmissions.noter(self.ua,'Impossible',personne=self.personne_a,menage=self.ma)
            x=transmissions.noter(self.ua,'Valide',menage=self.ma)
        self.assertEqual(transmissions.cible_note(x),self.ma)
    def test_post_service_choisi_sans_changer_session(self):
        self.creer();c=Client();c.force_login(self.ua)
        url=reverse('suivi:cahier')+'?lia_cible=service&lia_id='+str(self.sa.pk)
        token=c.get(url).context['form']['lia_envoi'].value()
        r=c.post(url,{'contenu':'Nouveau service','date_fait':timezone.localdate().isoformat(),'lia_envoi':token})
        self.assertEqual(r.status_code,302)
        x=m.Transmission.objects.get(contenu='Nouveau service')
        self.assertEqual(PorteeObjet.objects.get(modele=x._meta.label_lower,identifiant=str(x.pk)).service_id,self.sa.pk)
    def test_revocation_bloque_saisie_et_lecture(self):
        self.creer();c=Client();c.force_login(self.ua)
        url=reverse('suivi:cahier')+'?lia_cible=menage&lia_id='+str(self.ma.pk)
        Habilitation.objects.filter(compte=self.ua).update(revoque_le=timezone.now())
        self.assertIn(c.post(url,{'contenu':'INTERDIT'}).status_code,(403,404))
        self.assertFalse(m.NotePartagee.objects.filter(contenu='INTERDIT').exists())
    def test_parents_ouvrent_le_bon_ecran_sur_son_cahier(self):
        with perimetre(self.ua):
            ps=s.Point(self.ua,'hebergement',self.h.pk).parents({'lia_types':['messages','equipe']})
        self.assertEqual(len(ps),3)
        self.assertIn(reverse('dossiers:prise',args=['menage',self.ma.pk,self.a.pk]),ps[0]['url'])
        self.assertTrue(all('#liaisons' in x['url'] and 'lia_ouvrir=1' in x['url'] for x in ps))
    def test_corps_rendu_et_ancien_acces_notes_unifie(self):
        self.creer();c=Client();c.force_login(self.ua)
        r=c.get(reverse('suivi:notes',args=['accompagnement',self.a.pk]))
        self.assertContains(r,'Cahier de liaison');self.assertContains(r,'Message de la prise');self.assertNotContains(r,'Message du dossier')
    def test_aucun_type_coche_ne_retourne_aucune_ligne(self):
        self.creer();d=self.donnees();d['lia_types']=[]
        with perimetre(self.ua):self.assertEqual(s.selection(s.Point(self.ua,'menage',self.ma.pk),d),[])
    def test_notification_attribution_ouvre_cahier_cible(self):
        from acteurs.notifications import visibles
        a.ajouter_responsabilite(self.ua,self.da,self.a,self.pc,timezone.localdate(),'suivi',a.jeton(self.da),message='Invitation')
        with perimetre(self.uc):url=visibles(self.uc)[0].url
        self.assertIn('lia_ouvrir=1',url);self.assertIn('lia_focus=attribution-',url);self.assertTrue(url.endswith('#liaisons'))

    def test_retry_ne_duplique_pas_et_revalide_la_portee(self):
        c=Client();c.force_login(self.ua)
        url=reverse('suivi:cahier')+'?lia_cible=menage&lia_id='+str(self.ma.pk)
        token=c.get(url).context['form']['lia_envoi'].value()
        data={'contenu':'Envoi unique','lia_envoi':token}
        self.assertEqual(c.post(url,data).status_code,302)
        self.assertEqual(c.post(url,data).status_code,302)
        self.assertEqual(m.NotePartagee.objects.filter(contenu='Envoi unique').count(),1)
        self.assertEqual(c.post(url,{**data,'contenu':'Autre contenu'}).status_code,409)
        self.assertEqual(c.post(reverse('suivi:cahier')+'?lia_cible=prise&lia_id='+str(self.a.pk),data).status_code,409)
    def test_historique_du_dossier_sans_borne_imposee(self):
        with perimetre(self.ua,self.sa):transmissions.noter(self.ua,'Message historique',menage=self.ma,date_fait=date(2020,1,1))
        c=Client();c.force_login(self.ua)
        self.assertContains(c.get(reverse('suivi:cahier'),{'lia_cible':'menage','lia_id':str(self.ma.pk)}),'Message historique')
        self.assertNotContains(c.get(reverse('suivi:cahier')),'Message historique')

    def test_services_python_sans_middleware_restent_bornes(self):
        from . import releve
        with perimetre(self.ub,self.sb):
            releve.creer_action(self.ub,'ACTION SECRÈTE AUTRE SERVICE',timezone.localdate())
        rows=s.selection(s.Point(self.ua,'ensemble'),self.donnees('actions'))
        self.assertFalse(any('SECRÈTE' in x['titre'] for x in rows))
        with self.assertRaises(m.Menage.DoesNotExist):
            s.Point(self.ua,'menage',self.mb.pk)

    def test_contrainte_sql_refuse_les_cibles_absentes_ou_multiples(self):
        from django.db import transaction,IntegrityError
        for cibles in ({},{'menage':self.ma,'personne':self.personne_a}):
            with self.assertRaises(IntegrityError),transaction.atomic():
                m.NotePartagee.objects.create(auteur=self.ua,contenu='INVALIDE',**cibles)

    def test_periodes_symboliques_et_pas_de_borne_par_defaut(self):
        with perimetre(self.ua):point=s.Point(self.ua,'prise',self.a.pk)
        def lire(**kw):
            q=QueryDict('',mutable=True);q.update(kw);f=s.filtres(q,point);self.assertTrue(f.is_valid(),f.errors);return f.cleaned_data
        self.assertIsNone(lire()['lia_debut'])
        self.assertEqual(lire(lia_periode='element')['lia_debut'],self.a.debut)
        d=lire(lia_periode='sept_jours');self.assertEqual((d['lia_fin']-d['lia_debut']).days,7)
        self.assertEqual(lire(lia_periode='toutes',lia_debut='2020-01-01')['lia_debut'],None)
        self.assertEqual(lire(lia_periode='dates',lia_debut='2020-01-01')['lia_debut'],date(2020,1,1))

    def test_presentations_du_cahier_sans_sortie_pleine_page(self):
        c=Client();c.force_login(self.ua)
        r=c.get(reverse('suivi:cahier'),{'lia_cible':'prise','lia_id':str(self.a.pk)})
        self.assertNotContains(r,'Ouvrir ce cahier en pleine page')
        self.assertContains(r,'Inclure les prestations')
        self.assertNotContains(r,'Inclure les niveaux inférieurs')
        self.assertContains(r,'Attributions et relais')
        self.assertContains(r,'Cahier de liaison du service')
