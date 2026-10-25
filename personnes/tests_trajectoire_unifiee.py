"""Cas métier transversaux ; données exclusivement fictives."""
from datetime import date
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from . import bd6, dossier_complet, social, suivi
from . import models as m
from .tests_dossier_complet import valeurs


class TrajectoireUnifieeTests(TestCase):
    def setUp(self):
        self.u = get_user_model().objects.create_superuser('trajectoire-fictive', password='fictif')
        self.p = m.Personne.objects.create(designation='Léa fictive', cree_par=self.u)
        self.q = m.Personne.objects.create(designation='Noé fictif', cree_par=self.u)
        self.m = suivi.creer_menage(self.u, 'Les Passerelles — ménage fictif', [self.p, self.q], date(2026, 1, 1))
        self.a = suivi.ouvrir(self.u, self.m, [self.p], date(2026, 1, 1))
        self.b = suivi.ouvrir(self.u, self.m, [self.q], date(2026, 3, 1))
        self.url = reverse('dossiers:trajectoire', args=['personne', self.p.pk])
        self.murl = reverse('dossiers:trajectoire', args=['menage', self.m.pk])
        self.client.force_login(self.u)

    def fait(self, valeur='formation', debut=date(2026, 2, 1), **kw):
        return bd6.renseigner(self.u, self.p, 'emploi', valeur, debut, 'Entretien fictif', bd6.jeton(self.p), **kw)

    def ligne(self, jour=date(2026, 2, 2)):
        return bd6.etat(self.u, [self.p], jour)[0]['lignes'][1]

    def test_personnel_prioritaire_et_tous_les_temoins_conserves(self):
        social.renseigner(self.u, self.a, self.p, 'emploi', 'sans_emploi', date(2026, 1, 1), 'Ancien A fictif')
        c = suivi.ouvrir(self.u, self.m, [self.p], date(2026, 1, 1))
        social.renseigner(self.u, c, self.p, 'emploi', 'emploi', date(2026, 1, 1), 'Ancien B fictif')
        sans = self.ligne()
        self.assertEqual(sans['texte'], 'Non renseigné')
        self.assertTrue(sans['conflit'])
        fait = self.fait()
        avec = self.ligne()
        self.assertEqual(avec['texte'], 'En formation')
        self.assertEqual(len(avec['anciens']), 2)
        self.assertTrue(avec['conflit'])
        page = self.client.get(self.url, {'debut':'2026-02-02', 'fin':'2026-02-02'})
        self.assertContains(page, 'En formation'); self.assertContains(page, 'Ancien A fictif')
        self.assertFalse(any(l['nature'] == 'Déclaration personnelle' for l in page.context['lignes']))
        self.assertEqual(m.SituationPersonnelle.objects.count(), 1)
        self.assertEqual(m.SituationSociale.objects.count(), 2)
        # La restitution à l'entrée est recalculable et emploie la même règle.
        page = self.client.get(reverse('suivi:resume', args=[c.pk]))
        self.assertContains(page, 'Ancien A fictif')
        self.assertContains(page, 'Aucune déclaration personnelle consultable')
        self.assertEqual(m.SituationPersonnelle.objects.get().pk, fait.pk)

    def test_changement_entre_prises_et_correction_retroactive(self):
        self.a.fin = date(2026, 2, 1); self.a.save(update_fields=['fin'])
        c = suivi.ouvrir(self.u, self.m, [self.p], date(2026, 4, 1))
        ancien = self.fait('sans_emploi', date(2026, 1, 1))
        self.fait('formation', date(2026, 3, 1))
        self.fait('emploi', ancien.debut, correction=ancien.pk, motif='Erreur fictive corrigée')
        page = self.client.get(self.url, {'debut':'2026-01-15', 'fin':'2026-03-15'})
        emploi = next(l for l in page.context['comparaison'] if l['dimension'] == 'Emploi / formation')
        self.assertEqual(emploi['initial_lecture']['texte'], 'En emploi')
        self.assertEqual(emploi['final_lecture']['texte'], 'En formation')
        page = self.client.get(self.url, {'prise':str(c.pk), 'debut':'2026-03-01', 'fin':'2026-03-15'})
        self.assertContains(page, 'En formation')  # Pas de bornage arbitraire à avril.
        histoire = self.client.get(reverse('dossiers:social', args=[self.p.pk]))
        self.assertContains(histoire, 'Erreur fictive corrigée')
        self.assertContains(histoire, 'sans_emploi')
        self.assertEqual(m.RevisionSituationPersonnelle.objects.count(), 3)

    def test_inconnu_fin_exclue_et_pas_de_continuite_inventee(self):
        self.fait('inconnu', date(2026, 2, 1))
        s = m.SituationPersonnelle.objects.get(); s.fin=date(2026, 3, 1);s.save(update_fields=['fin'])
        self.assertEqual(self.ligne(date(2026, 1, 31))['texte'], 'Non renseigné')
        self.assertEqual(self.ligne(date(2026, 2, 28))['texte'], s.libelle_valeur)
        self.assertEqual(self.ligne(date(2026, 3, 1))['texte'], 'Non renseigné')
        page = self.client.get(self.url, {'debut':'2026-03-02','fin':'2026-03-01'})
        self.assertTrue(page.context['form'].errors);self.assertEqual(page.context['lignes'], [])
        page = self.client.get(self.url, {'fin':'2099-01-01'})
        self.assertTrue(page.context['form'].errors)

    def test_personne_menage_beneficiaires_et_bilans_distincts(self):
        social.evenement(self.u, self.a, self.p, date(2026,1,2), 'Événement de Léa fictive', 'Fictif')
        social.evenement(self.u, self.b, self.q, date(2026,3,2), 'Événement de Noé fictif', 'Fictif')
        social.bilan(self.u, self.a, date(2026,1,3), 'Bilan collectif fictif')
        page = self.client.get(self.url)
        self.assertContains(page, 'Événement de Léa fictive')
        self.assertNotContains(page, 'Événement de Noé fictif');self.assertNotContains(page, 'Bilan collectif fictif')
        self.assertContains(self.client.get(self.murl), 'Bilan collectif fictif')
        self.assertNotContains(self.client.get(self.murl, {'beneficiaire':str(self.p.pk)}), 'Bilan collectif fictif')
        page = self.client.get(self.murl, {'prise':str(self.a.pk)})
        self.assertNotContains(page, 'Événement de Noé fictif')
        self.assertTrue(self.client.get(self.url, {'prise':str(self.b.pk)}).context['form'].errors)
        self.assertTrue(self.client.get(self.murl, {'prise':str(self.b.pk), 'beneficiaire':str(self.p.pk)}).context['form'].errors)

    def test_appartenance_datee_et_beneficiaire_hors_composition(self):
        lien = m.Appartenance.objects.get(menage=self.m, personne=self.p)
        lien.fin=date(2026,2,1);lien.save(update_fields=['fin'])
        self.a.fin=date(2026,2,1);self.a.save(update_fields=['fin'])
        autre=suivi.creer_menage(self.u,'Autre ménage fictif',[self.p],date(2026,2,1))
        c=suivi.ouvrir(self.u,autre,[self.p],date(2026,2,1))
        self.fait()
        social.evenement(self.u,c,self.p,date(2026,2,2),'Fait autre ménage fictif','Fictif')
        self.assertContains(self.client.get(self.url),'Fait autre ménage fictif')
        page=self.client.get(self.murl,{'debut':'2026-02-01','fin':'2026-02-02'})
        self.assertNotContains(page,'Fait autre ménage fictif');self.assertNotContains(page,'En formation')
        # Une prise explicite permet la lecture, sans rétablir une appartenance.
        suivi.ouvrir(self.u,self.m,[self.p],date(2026,2,1))
        self.assertContains(self.client.get(self.murl,{'fin':'2026-02-02'}),'En formation')
        self.assertEqual(m.Appartenance.objects.get(pk=lien.pk).fin,date(2026,2,1))

    def ressource(self, **kw):
        return dossier_complet.enregistrer(self.u,'ressources',self.p,date(2026,1,1),None,'Relevé fictif',bd6.jeton(self.p),**valeurs('ressources',**kw))

    def test_ressources_dettes_sans_double_compte_et_correction(self):
        ancien=bd6.renseigner(self.u,self.p,'ressources','sans_ressources',date(2026,1,1),'Synthèse fictive',bd6.jeton(self.p))
        x=self.ressource()
        for nature,creancier,montant in [('total','',1000),('detail','Créancier fictif',100)]:
            dossier_complet.enregistrer(self.u,'dettes',self.p,date(2026,1,1),None,'Dette fictive',bd6.jeton(self.p),**valeurs('dettes',nature=nature,creancier=creancier,montant=Decimal(montant)))
        page=self.client.get(self.url,{'debut':'2026-02-01','fin':'2026-02-02'})
        self.assertContains(page,'800.50 EUR');self.assertContains(page,'total déclaré : 1000.00 EUR')
        self.assertContains(page,'détails connus : 100.00 EUR');self.assertNotContains(page,'1100.00 EUR')
        self.assertContains(page,'Synthèse personnelle conservée')
        self.assertEqual(m.SituationPersonnelle.objects.get(pk=ancien.pk).valeur,'sans_ressources')
        rapport=self.client.get(reverse('dossiers:rapport_a'),{'rubrique':'ressources','date':'2026-02-02','format':'csv'})
        self.assertIn(b'800.50',rapport.content)
        dossier_complet.annuler(self.u,'ressources',self.p,x,'Erreur fictive',bd6.jeton(self.p))
        self.assertNotContains(self.client.get(self.url),'800.50 EUR')
        self.assertEqual(dossier_complet.RUBRIQUES['ressources'].journal.objects.count(),2)

    def test_droits_partiels_anciennes_versions_et_exports(self):
        self.fait();self.ressource()
        social.renseigner(self.u,self.a,self.p,'emploi','sans_emploi',date(2026,1,1),'Témoin réservé fictif')
        lecteur=get_user_model().objects.create_user('lecteur-fictif')
        noms=['view_personne','view_situationpersonnelle','view_ressourcepersonnelle']
        lecteur.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes',codename__in=noms))
        self.client.force_login(lecteur)
        page=self.client.get(self.url)
        self.assertNotContains(page,'En formation');self.assertNotContains(page,'800.50');self.assertNotContains(page,'Témoin réservé fictif')
        self.assertEqual(self.client.get(reverse('dossiers:social',args=[self.p.pk])).status_code,403)
        self.assertEqual(self.client.get(reverse('dossiers:rapport_a'),{'rubrique':'ressources','format':'csv'}).status_code,403)
        lecteur.user_permissions.add(Permission.objects.get(content_type__app_label='personnes',codename='view_revisionsituationpersonnelle'))
        self.assertContains(self.client.get(self.url),'En formation')
        self.assertEqual(self.client.get(self.murl).status_code,403)
        self.assertEqual(self.client.get(reverse('suivi:trajectoire',args=[self.a.pk])).status_code,403)

    def test_retours_bd_source_date_et_ancienne_url(self):
        self.fait()
        social.evenement(self.u,self.a,self.p,date(2026,2,2),'Événement fictif','Fictif')
        page=self.client.get(self.url,{'prise':str(self.a.pk),'retour_prise':str(self.a.pk),'fin':'2026-02-03','q':'Léa','sejour':'invalide'})
        self.assertIn(reverse('dossiers:prise',args=['personne',self.p.pk,self.a.pk]),page.context['retour_trajectoire'])
        self.assertIn('date_service=2026-02-03',page.context['retour_trajectoire'])
        source=next(l['url'] for l in page.context['lignes'] if l['nature']=='Événement')
        retour=self.client.get(source).context['retour_dossier']
        self.assertIn(reverse('dossiers:detail',args=['personne',self.p.pk]),retour)
        self.assertContains(self.client.get(reverse('suivi:trajectoire',args=[self.a.pk])),'En formation')
        from . import dossier
        from django.test import RequestFactory
        requete = RequestFactory().get('/'); requete.user = self.u
        contexte = dossier.pour_prise(requete,self.a,'personne',self.p.pk,{'date_service':'2026-02-01'})
        social.bilan(self.u,self.a,date(2026,2,1),'Bilan hors sélection individuelle')
        ancienne = self.client.get(reverse('suivi:trajectoire',args=[self.a.pk]), {
            'contexte_dossier':contexte['contexte_dossier'], 'fin':'2026-02-03'})
        self.assertNotContains(ancienne,'Bilan hors sélection individuelle')
        retour = self.client.get(ancienne.context['retour_trajectoire'])
        self.assertEqual(retour.context['parametres_navigation']['date_service'],'2026-02-03')
        self.assertEqual(self.client.post(self.url).status_code,405)
        self.assertIn('no-store',page['Cache-Control'])
        # La lecture ne crée ni situation, ni événement, ni journal.
        self.assertEqual(m.SituationPersonnelle.objects.count(),1)
        self.assertEqual(m.RevisionSituationPersonnelle.objects.count(),1)

    def test_continuations_et_lecture_sans_effet_sur_les_statistiques(self):
        from . import hebergement as h, continuite_hebergement as ch, statistiques
        a = suivi.ouvrir(self.u,self.m,[self.p,self.q],date(2026,1,1))
        accord = h.accorder(self.u,a,[self.p,self.q],date(2026,1,1),date(2026,2,1))
        sejour = h.admettre(self.u,accord,[self.p,self.q],date(2026,1,1))
        ch.individualiser(self.u,sejour,date(2026,1,5),'Continuation fictive',ch.jeton(sejour))
        enfant = sejour.continuations.get(beneficiaires=self.p)
        h.sortir(self.u,enfant,date(2026,1,8))
        avant = statistiques.bilan(date(2026,1,1),date(2026,2,1))
        page = self.client.get(self.url)
        lignes = page.context['lignes']
        self.assertEqual(sum(l['nature']=='Admission' for l in lignes),1)
        self.assertEqual(sum(l['nature']=='Continuation individuelle' for l in lignes),1)
        self.assertEqual(sum(l['nature']=='Sortie' for l in lignes),1)
        self.assertEqual(sum(l['nature']=='Fin du fragment collectif' for l in lignes),1)
        self.assertEqual(avant,statistiques.bilan(date(2026,1,1),date(2026,2,1)))
        self.assertEqual(m.SituationPersonnelle.objects.count(),0)
        self.assertEqual(m.SituationSociale.objects.count(),0)


class CopieTrajectoireTests(TransactionTestCase):
    def test_copie_restauree_restitue_sans_convertir_les_anciens_faits(self):
        import json, os, sqlite3, subprocess, sys
        from contextlib import closing
        from pathlib import Path
        from tempfile import TemporaryDirectory
        from django.db import connection
        from pas_communs.paquets import creer_sauvegarde
        from pas_a_pas_accompagnement import paquets
        if connection.vendor != 'sqlite':
            self.skipTest('Copie SQLite uniquement.')
        u = get_user_model().objects.create_superuser('copie-trajectoire-fictive')
        p = m.Personne.objects.create(designation='Personne fictive copiée',cree_par=u)
        menage = suivi.creer_menage(u,'Les Passerelles — copie fictive',[p],date(2026,1,1))
        a = suivi.ouvrir(u,menage,[p],date(2026,1,1))
        social.renseigner(u,a,p,'emploi','sans_emploi',date(2026,1,1),'Ancien témoin fictif')
        bd6.renseigner(u,p,'emploi','formation',date(2026,2,1),'Entretien fictif',bd6.jeton(p))
        with TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir()
            (source/'secret-key').write_text('cle-fictive-copie-trajectoire')
            with closing(sqlite3.connect(source/paquets.PROFIL.base)) as db:
                connection.connection.backup(db)
            archive=root/'copie.zip';creer_sauvegarde(source,archive,profil=paquets.PROFIL)
            prep=paquets.verifier(archive,root,'preparation');destination=root/'restauree'
            paquets.installer_copie(prep,destination)
            code = '''import os,json
os.environ['DJANGO_SETTINGS_MODULE']='pas_a_pas_accompagnement.settings'
import django;django.setup()
from django.contrib.auth import get_user_model
from personnes import bd6,models as m
from datetime import date
u=get_user_model().objects.get(username='copie-trajectoire-fictive')
p=m.Personne.objects.get()
l=bd6.etat(u,[p],date(2026,2,2))[0]['lignes'][1]
print(json.dumps([l['texte'],[x.valeur for x in l['anciens']],m.SituationPersonnelle.objects.count(),m.RevisionSituationPersonnelle.objects.count()],ensure_ascii=False))
'''
            env={**os.environ,'ACCOMPAGNEMENT_DONNEES':str(destination)}
            r=subprocess.run([sys.executable,'-c',code],env=env,text=True,capture_output=True,check=True)
            self.assertEqual(json.loads(r.stdout),['En formation',['sans_emploi'],1,1])
