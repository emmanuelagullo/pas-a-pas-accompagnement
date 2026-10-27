from datetime import timedelta, date
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, Client
from django.utils import timezone
from .models import *
from .contexte import perimetre, courant
from . import politique as p, services as s
from personnes import models as m, suivi, hebergement, transmissions


class AccesTests(TestCase):
    def setUp(self):
        self.admin=get_user_model().objects.create_user('organisation-fictive')
        self.admin.user_permissions.add(Permission.objects.get(codename='gerer_organisation'))
        org=m.Partenaire.objects.create(libelle='Association fictive',cree_par=self.admin)
        self.org=OrganismeGestionnaire.objects.create(organisme=org)
        fiche=m.Partenaire.objects.create(libelle='Établissement fictif',cree_par=self.admin)
        self.etab=Etablissement.objects.create(organisme=self.org,fiche=fiche)
        self.sa=Service.objects.create(etablissement=self.etab,libelle='Service A')
        self.sb=Service.objects.create(etablissement=self.etab,libelle='Service B')
        self.ua,self.pa=self.compte('nadia-fictive',self.sa)
        self.ub,self.pb=self.compte('camille-fictive',self.sb)
        self.uc,self.pc=self.compte('collegue-fictif',self.sa)
        self.da,self.personne_a,self.ma,self.a,self.h=self.dossier(self.sa,self.ua,'A')
        self.db,self.personne_b,self.mb,self.b,self.hb=self.dossier(self.sb,self.ub,'B')
        ConfigurationAcces.objects.create(active=True)

    def compte(self,nom,service,tache='social',**kw):
        u=get_user_model().objects.create_user(nom,password='Mot-de-passe-fictif-2026')
        u.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes'))
        prof=m.Intervenant.objects.create(libelle=nom,cree_par=self.admin)
        LienCompteProfessionnel.objects.create(compte=u,professionnel=prof)
        AppartenanceProfessionnelle.objects.create(professionnel=prof,service=service,debut=date(2020,1,1))
        s.habiliter(self.admin,u,service,tache,date(2020,1,1),**kw)
        return u,prof

    def dossier(self,service,u,nom):
        personne=m.Personne.objects.create(designation='Personne fictive '+nom,cree_par=u)
        menage=m.Menage.objects.create(libelle='Ménage fictif '+nom,cree_par=u)
        appart=m.Appartenance.objects.create(menage=menage,personne=personne,debut=date(2020,1,1))
        a=m.Accompagnement.objects.create(menage=menage,debut=date(2020,1,1),cree_par=u);a.beneficiaires.add(personne)
        h=m.AccordHebergement.objects.create(accompagnement=a,debut=date(2020,1,1),fin=date(2030,1,1),cree_par=u);h.beneficiaires.add(personne)
        ds=DossierService.objects.create(service=service,menage=menage,cree_par=u,en_attente=False)
        for x in (personne,menage,appart,a,h):
            PorteeObjet.objects.create(modele=x._meta.label_lower,identifiant=str(x.pk),service=service,dossier=ds,
                prise=a if x in (a,h) else None,prestation_modele='accordhebergement' if x==h else '',prestation_id=h.pk if x==h else None)
        return ds,personne,menage,a,h

    def test_collectif_separe_services_listes_joins_et_http(self):
        with perimetre(self.ua):
            self.assertEqual(list(m.Personne.objects.values_list('pk',flat=True)),[self.personne_a.pk])
            self.assertEqual(m.Accompagnement.objects.count(),1)
            self.assertFalse(m.AccordHebergement.objects.filter(pk=self.hb.pk).exists())
            self.assertEqual(m.Sejour.objects.non_annules().count(),0)
        client=Client();client.force_login(self.ua)
        self.assertEqual(client.get('/personnes/'+str(self.personne_b.pk)+'/').status_code,404)
        self.assertEqual(client.get('/personnes/'+str(self.personne_b.pk)+'/pdf/').status_code,404)
        r=client.get('/',{'q':'fictive','fragment':'1'})
        self.assertNotContains(r,'Ménage fictif B');self.assertContains(r,'Ménage fictif A')

    def test_appartenance_et_responsabilite_sans_habilitation_ne_donnent_rien(self):
        Habilitation.objects.filter(compte=self.ua).update(revoque_le=timezone.now())
        Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin)
        with perimetre(self.ua):
            self.assertEqual(m.Personne.objects.count(),0)
            with self.assertRaises(PermissionDenied):suivi.clore(self.ua,self.a,date(2027,1,1))

    def test_politique_individuelle_et_lecture_partagee(self):
        self.sa.politique='individuel';self.sa.save()
        with perimetre(self.ua):self.assertEqual(m.Accompagnement.objects.count(),0)
        Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin)
        with perimetre(self.ua):self.assertEqual(m.Accompagnement.objects.count(),1)
        with perimetre(self.uc):self.assertEqual(m.Accompagnement.objects.count(),0)
        s.changer_politique(self.admin,self.sa,'lecture',s.jeton(self.sa))
        with perimetre(self.uc):
            self.assertEqual(m.Accompagnement.objects.count(),1)
            self.assertEqual(m.Accompagnement.objects.filter(pk=self.a.pk).update(fin=date(2026,1,1)),0)
            with self.assertRaises(PermissionDenied):
                self.a.fin=date(2026,1,1);self.a.save()

    def test_creation_autonome_et_reprise_sans_attribution_globale(self):
        self.sa.politique='individuel';self.sa.save()
        with perimetre(self.ua,self.sa):
            x=m.Personne.objects.create(designation='Nouveau fictif',cree_par=self.ua)
            self.assertTrue(m.Personne.objects.filter(pk=x.pk).exists())
        ds=DossierService.objects.get(personne=x)
        self.assertFalse(ds.en_attente)
        veilleur,_=self.compte('veilleur-fictif',self.sa,'accueil')
        with perimetre(veilleur,self.sa):
            y=m.Personne.objects.create(designation='Accueil fictif',cree_par=veilleur)
        attente=DossierService.objects.get(personne=y)
        self.assertTrue(attente.en_attente)
        s.commencer(self.uc,attente,s.jeton(attente))
        with self.assertRaises(s.Conflit):s.commencer(self.ua,attente,s.jeton(attente))
        with perimetre(self.uc):self.assertTrue(m.Personne.objects.filter(pk=y.pk).exists())

    def test_prestation_seule_nouvre_pas_histoire_sociale(self):
        self.sa.politique='individuel';self.sa.save()
        Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,hebergement=self.h,cree_par=self.admin)
        fait=m.SituationPersonnelle.objects.create(personne=self.personne_a,dimension='logement',valeur='inconnu',debut=date(2020,1,1),auteur=self.admin)
        PorteeObjet.objects.create(modele=fait._meta.label_lower,identifiant=str(fait.pk),dossier=self.da,service=self.sa)
        with perimetre(self.ua):
            self.assertTrue(m.Accompagnement.objects.filter(pk=self.a.pk).exists())
            self.assertTrue(m.AccordHebergement.objects.filter(pk=self.h.pk).exists())
            self.assertFalse(m.SituationPersonnelle.objects.exists())
            self.assertEqual(m.Accompagnement.objects.filter(pk=self.a.pk).update(fin=date(2026,1,1)),0)

    def test_relais_date_et_fin_des_acces_sans_recriture(self):
        self.sa.politique='individuel';self.sa.save()
        r=Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin,debut=timezone.now()-timedelta(days=3))
        rh=Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,hebergement=self.h,cree_par=self.admin,debut=timezone.now()-timedelta(days=3))
        attendu=s.jeton(self.da);lignes,proposition=s.proposition_relais(self.ua,self.da,self.da)
        self.assertEqual({x.pk for x in lignes},{r.pk,rh.pk})
        s.relayer(self.ua,self.da,self.pc,attendu,proposition)
        with self.assertRaises(s.Conflit):s.relayer(self.ua,self.da,self.pc,attendu,proposition)
        with perimetre(self.ua):self.assertEqual(m.Accompagnement.objects.count(),0)
        with perimetre(self.uc):self.assertEqual(m.Accompagnement.objects.count(),1)
        self.assertEqual(Responsabilite.objects.count(),4)
        self.assertEqual(JournalAcces.objects.filter(action='relais').count(),1)

    def test_habilitation_expiree_ne_ressuscite_pas_par_date_consultee(self):
        Habilitation.objects.filter(compte=self.ua).update(fin=timezone.localdate())
        with perimetre(self.ua):self.assertEqual(m.Accompagnement.objects.filter(debut__lte=date(2020,1,1)).count(),0)

    def test_portee_non_affectee_cachee_et_ecriture_directe_refusee(self):
        with perimetre(self.ua):
            self.assertEqual(m.Accompagnement.objects.filter(pk=self.b.pk).update(fin=date(2026,1,1)),0)
            with self.assertRaises(PermissionDenied):suivi.clore(self.ua,self.b,date(2026,1,1))
        PorteeObjet.objects.filter(modele='personnes.personne',identifiant=str(self.personne_a.pk)).delete()
        self.da.en_attente=False;self.da.save()
        # Le dossier du ménage reste trouvable ; aucune autre origine n'est inventée.
        self.assertFalse(PorteeObjet.objects.filter(modele='personnes.personne',identifiant=str(self.personne_a.pk)).exists())

    def test_stats_globales_ne_donnent_pas_justificatifs(self):
        coord,prof=self.compte('coordination-fictive',self.sa,'coordination',statistiques_service=True,statistiques_etablissement=True)
        with perimetre(coord,self.sa,'service'):self.assertEqual(m.Accompagnement.objects.count(),1)
        with perimetre(coord,self.sa,'etablissement'):self.assertEqual(m.Accompagnement.objects.count(),2)
        with perimetre(coord,self.sa):self.assertEqual(m.Accompagnement.objects.count(),0)
        client=Client();client.force_login(coord)
        self.assertEqual(client.get('/personnes/'+str(self.personne_a.pk)+'/').status_code,403)

    def test_contexte_est_reinitialise_apres_exception(self):
        with self.assertRaises(RuntimeError):
            with perimetre(self.ua):raise RuntimeError
        self.assertIsNone(courant())

    def test_registre_et_config_sans_creation_de_compte(self):
        avant=get_user_model().objects.count()
        AppartenanceProfessionnelle.objects.create(professionnel=self.pa,service=self.sb,debut=date(2020,1,1))
        with perimetre(self.ua):self.assertEqual(m.Accompagnement.objects.count(),1)
        self.assertEqual(get_user_model().objects.count(),avant)

    def test_meme_identite_deux_services_faits_personnels_separes(self):
        from personnes import famille,bd6
        DossierService.objects.create(service=self.sb,personne=self.personne_a,cree_par=self.admin,en_attente=False)
        with perimetre(self.ub,self.sb):
            f=famille.renseigner(self.ub,self.personne_a,date(2026,1,1),'Entretien fictif B',bd6.jeton(self.personne_a),
                situation_familiale='Valeur fictive B',rapports_parentaux='',fratrie='',enfants_a_charge=None,enfants_non_a_charge=None,grossesse=None)
            self.assertTrue(m.DeclarationFamiliale.objects.filter(personne=self.personne_a).exists())
        with perimetre(self.ua,self.sa):self.assertFalse(m.DeclarationFamiliale.objects.filter(personne=self.personne_a).exists())

    def test_queryset_reutilise_ne_conserve_pas_acces_du_premier_compte(self):
        qs=m.Personne.objects.order_by('pk')
        self.assertEqual(len(list(qs)),2)
        with perimetre(self.ua):self.assertEqual([x.pk for x in qs],[self.personne_a.pk])
        with perimetre(self.ub):self.assertEqual([x.pk for x in qs],[self.personne_b.pk])

    def test_usurpation_auteur_et_deplacement_de_rattachement_refuses(self):
        with perimetre(self.ua,self.sa):
            with self.assertRaises(PermissionDenied):m.Personne.objects.create(designation='Fictif',cree_par=self.ub)
            with self.assertRaises(PermissionDenied):m.Accompagnement.objects.filter(pk=self.a.pk).update(menage=self.mb)
            with self.assertRaises(PermissionDenied):m.Personne.objects.create(pk=self.personne_b.pk,designation='Remplacement interdit',cree_par=self.ua)
        self.personne_b.refresh_from_db();self.assertEqual(self.personne_b.designation,'Personne fictive B')

    def test_piece_privee_versions_et_export_separe_de_lecture(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from personnes import pieces_dossier,bd6
        with perimetre(self.ua,self.sa):
            piece=pieces_dossier.ajouter(self.ua,self.personne_a,bd6.jeton(self.personne_a),titre='Pièce fictive A',date_document=None,
                source='Document fictif',fichier=SimpleUploadedFile('fictif.txt',b'Contenu strictement fictif A'))
        version=m.VersionPieceDossier._base_manager.get(piece=piece)
        url='/dossiers/pieces/fichier/'+str(version.pk)+'/'
        c=Client();c.force_login(self.ua)
        self.assertEqual(c.get(url).status_code,403)
        Habilitation.objects.filter(compte=self.ua).update(exporter=True)
        self.assertEqual(c.get(url).status_code,200)
        c.force_login(self.ub);self.assertEqual(c.get(url).status_code,404)

    def test_statistiques_mes_dossiers_et_totaux_de_service_distincts(self):
        c=Client();c.force_login(self.ua)
        params={'rapport':'synthese','debut':'2026-01-01','fin':'2026-02-01'}
        r=c.get('/statistiques/',params);self.assertEqual(r.status_code,200)
        self.assertEqual(r.context_data['resultats']['accompagnements'],0)
        self.assertEqual(c.get('/statistiques/',{**params,'portee_statistiques':'service'}).status_code,403)
        Habilitation.objects.filter(compte=self.ua).update(statistiques_service=True)
        r=c.get('/statistiques/',{**params,'portee_statistiques':'service'});self.assertEqual(r.status_code,200)
        self.assertEqual(r.context_data['resultats']['accompagnements'],1)
        self.assertEqual(c.get('/statistiques/',{**params,'portee_statistiques':'service','format':'csv'}).status_code,403)
        Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin)
        r=c.get('/statistiques/',params);self.assertEqual(r.context_data['resultats']['accompagnements'],1)

    def test_export_dun_service_non_autorise_non_ouvert_par_un_autre(self):
        # Deux habilitations du même compte ne fusionnent pas leurs options d'export.
        AppartenanceProfessionnelle.objects.create(professionnel=self.pa,service=self.sb,debut=date(2020,1,1))
        s.habiliter(self.admin,self.ua,self.sb,'social',date(2020,1,1),exporter=True)
        c=Client();c.force_login(self.ua)
        self.assertEqual(c.get('/personnes/'+str(self.personne_a.pk)+'/fiche.pdf').status_code,403)

    def test_relais_http_et_csrf(self):
        from django.urls import reverse
        r=Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin,debut=timezone.now()-timedelta(days=1))
        c=Client();c.force_login(self.ua)
        url=reverse('acteurs:relais_dossier',args=[self.da.pk]);page=c.get(url)
        self.assertEqual(page.status_code,200)
        f=page.context['form']
        reponse=c.post(url,{'entrant':str(self.pc.pk),'sortant':str(self.pa.pk),'date':timezone.localdate().isoformat(),
            'descendants':'on','attendu':f.initial['attendu'],'proposition':f.initial['proposition']})
        self.assertEqual(reponse.status_code,302)
        r.refresh_from_db();self.assertIsNotNone(r.fin)
        c=Client(enforce_csrf_checks=True);c.force_login(self.ua)
        self.assertEqual(c.post(reverse('acteurs:reprendre',args=[self.da.pk]),{}).status_code,403)

    def test_recherche_ordre_et_mes_dossiers_sans_doublon(self):
        from .recherche import classer
        self.da.en_attente=True;self.da.save()
        Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,hebergement=self.h,cree_par=self.admin)
        with perimetre(self.ua,self.sa):
            lignes=classer(self.ua,m.Menage.objects.all(),'menage','tous',self.sa.pk)
            self.assertEqual([x.pk for x in lignes],[self.ma.pk]);self.assertEqual(lignes[0].acteur_groupe,'En attente')
            self.assertEqual(len(classer(self.ua,m.Menage.objects.all(),'menage','mes',self.sa.pk)),1)

    def test_pas_de_permission_inventee_et_options_metier_existantes(self):
        with perimetre(self.ua):
            self.assertFalse(self.ua.has_perm('personnes.permission_imaginaire'))
            self.assertTrue(self.ua.has_perm('personnes.corriger_prevision_accompagnement'))

    def test_notes_sociales_non_ouvertes_par_la_permanence(self):
        veilleur,prof=self.compte('nuit-notes-fictive',self.sa,'accueil')
        with perimetre(self.ua,self.sa):
            prive=transmissions.noter(self.ua,'Note sociale fictive',personne=self.personne_a)
            operation=transmissions.noter(self.ua,'Consigne fictive de prestation',accord_hebergement=self.h)
        with perimetre(veilleur,self.sa):
            self.assertFalse(m.NotePartagee.objects.filter(pk=prive.pk).exists())
            self.assertTrue(m.NotePartagee.objects.filter(pk=operation.pk).exists())

    def test_affectation_supplementaire_nelargit_pas_les_services(self):
        self.sa.politique='individuel';self.sa.save()
        Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,cree_par=self.admin)
        s.ajouter_responsabilite(self.ua,self.da,self.da,self.pc,timezone.localdate(),'ponctuel',s.jeton(self.da))
        with perimetre(self.uc):self.assertTrue(m.Accompagnement.objects.filter(pk=self.a.pk).exists())
        with self.assertRaises(ValidationError):s.ajouter_responsabilite(self.ua,self.da,self.da,self.pb,timezone.localdate(),'suivi',s.jeton(self.da))
        with self.assertRaises(PermissionDenied):s.proposition_relais(self.ub,self.da,self.da,sortant=self.pa.pk)

    def test_exploitation_datee_et_qualification_relative(self):
        lieu=m.LieuHebergement.objects.create(libelle='Lieu physique fictif',cree_par=self.admin)
        x=s.changer_exploitation(self.admin,self.sa,lieu,date(2026,1,1),etablissement=self.etab,attendu=s.jeton(self.sa))
        self.assertEqual(s.qualifier_hebergement(self.etab,lieu,date(2026,1,2)),'Même établissement')
        externe=m.Partenaire.objects.create(libelle='Prestataire fictif extérieur',cree_par=self.admin)
        s.changer_exploitation(self.admin,self.sa,lieu,date(2026,2,1),organisme_exterieur=externe,attendu=s.jeton(self.sa))
        self.assertEqual(s.qualifier_hebergement(self.etab,lieu,date(2026,1,31)),'Même établissement')
        self.assertEqual(s.qualifier_hebergement(self.etab,lieu,date(2026,2,1)),'Organisme extérieur')
        x.refresh_from_db();self.assertEqual(x.fin,date(2026,2,1))

    def test_url_inconnue_reste_404(self):
        client=Client();client.force_login(self.ua)
        self.assertEqual(client.get('/route-fictive-inexistante/').status_code,404)

    def test_plusieurs_services_ont_un_service_courant_par_defaut(self):
        AppartenanceProfessionnelle.objects.create(professionnel=self.pa,service=self.sb,debut=date(2020,1,1))
        s.habiliter(self.admin,self.ua,self.sb,'social',date(2020,1,1))
        client=Client();client.force_login(self.ua)
        response=client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertContains(response,'Service A')

    def test_configuration_sans_habilitation_peut_choisir_un_professionnel(self):
        from django.urls import reverse
        client=Client();client.force_login(self.admin)
        response=client.get(reverse('acteurs:membre',args=[self.sa.pk]))
        self.assertEqual(response.status_code,200)
        self.assertIn(self.pa,response.context['form'].fields['professionnel'].queryset)
        self.assertFalse(p.habilitations(self.admin).exists())

    def test_cloture_arrete_suivis_de_prise_et_prestations_pas_dossier(self):
        self.sa.politique='individuel';self.sa.save()
        debut=timezone.now()-timedelta(days=2)
        prise=Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,prise=self.a,debut=debut,cree_par=self.admin)
        prestation=Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,hebergement=self.h,debut=debut,cree_par=self.admin)
        future=Responsabilite.objects.create(dossier=self.da,professionnel=self.pc,prise=self.a,debut=timezone.now()+timedelta(days=5),cree_par=self.admin)
        dossier=Responsabilite.objects.create(dossier=self.da,professionnel=self.pc,debut=debut,cree_par=self.admin)
        attendu=s.jeton(self.da)
        with perimetre(self.ua,self.sa):
            suivi.clore(self.ua,self.a,timezone.localdate())
            self.assertFalse(m.Accompagnement.objects.filter(pk=self.a.pk).exists())
        prise.refresh_from_db();prestation.refresh_from_db();future.refresh_from_db();dossier.refresh_from_db()
        self.assertIsNotNone(prise.fin);self.assertIsNotNone(prestation.fin)
        self.assertIsNotNone(future.annule_le);self.assertIsNone(dossier.fin)
        with perimetre(self.uc,self.sa):self.assertTrue(m.Accompagnement.objects.filter(pk=self.a.pk).exists())
        self.assertEqual(JournalAcces.objects.filter(action='fin_prise').count(),1)
        with self.assertRaises(s.Conflit):s.reserver(self.da,attendu)

    def test_relais_inclut_hebergement_reel_au_dela_de_fin_accord(self):
        self.h.fin=timezone.localdate()-timedelta(days=1);self.h.save()
        sejour=m.Sejour.objects.create(accord=self.h,debut=date(2020,1,1),cree_par=self.ua)
        r=Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,hebergement=self.h,cree_par=self.admin)
        lignes,_=s.proposition_relais(self.ua,self.da,self.da)
        self.assertIn(r.pk,[x.pk for x in lignes])
        sejour.fin=timezone.localdate();sejour.save()
        lignes,_=s.proposition_relais(self.ua,self.da,self.da)
        self.assertNotIn(r.pk,[x.pk for x in lignes])

    def test_affectation_ancienne_verifie_sans_ecrire_et_sans_droits(self):
        import json,hashlib
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from io import StringIO
        from django.core.management import call_command,CommandError
        PorteeObjet.objects.filter(modele='personnes.accordhebergement',identifiant=str(self.h.pk)).delete()
        manifeste={'service':self.sa.pk,'dossiers':[{'nature':'menage','id':str(self.ma.pk),'objets':[{'modele':'personnes.accordhebergement','id':str(self.h.pk)}]}]}
        avant=(Habilitation.objects.count(),Responsabilite.objects.count())
        with TemporaryDirectory() as temporaire:
            fichier=Path(temporaire)/'inventaire.json';octets=json.dumps(manifeste).encode();fichier.write_bytes(octets)
            call_command('affecter_donnees_service',str(fichier),auteur=self.admin.username,stdout=StringIO())
            self.assertFalse(PorteeObjet.objects.filter(identifiant=str(self.h.pk)).exists())
            with self.assertRaises(CommandError):call_command('affecter_donnees_service',str(fichier),auteur=self.admin.username,appliquer=True,empreinte='fausse',stdout=StringIO())
            call_command('affecter_donnees_service',str(fichier),auteur=self.admin.username,appliquer=True,empreinte=hashlib.sha256(octets).hexdigest(),stdout=StringIO())
        origine=PorteeObjet.objects.get(modele='personnes.accordhebergement',identifiant=str(self.h.pk))
        self.assertEqual(origine.dossier,self.da);self.assertEqual(origine.prise,self.a)
        self.assertEqual(avant,(Habilitation.objects.count(),Responsabilite.objects.count()))

    def test_activation_explicite_ne_cree_aucune_habilitation(self):
        from django.core.management import call_command,CommandError
        from io import StringIO
        ConfigurationAcces.objects.update(active=False)
        avant=(Habilitation.objects.count(),Responsabilite.objects.count(),PorteeObjet.objects.count())
        with self.assertRaises(CommandError):call_command('activer_acces_services',auteur=self.ua.username,stdout=StringIO())
        self.assertFalse(p.active())
        call_command('activer_acces_services',auteur=self.ua.username,confirmer=True,stdout=StringIO())
        self.assertTrue(p.active())
        self.assertEqual(avant,(Habilitation.objects.count(),Responsabilite.objects.count(),PorteeObjet.objects.count()))

    def test_cache_requete_invalide_par_revocation_et_politique(self):
        qs=m.Accompagnement.objects.all()
        with perimetre(self.ua,self.sa):
            self.assertEqual(len(list(qs)),1)
            self.assertTrue(self.ua.has_perm('personnes.view_accompagnement'))
            Habilitation.objects.filter(compte=self.ua).update(revoque_le=timezone.now())
            self.assertEqual(len(list(qs)),0)
            self.assertFalse(self.ua.has_perm('personnes.view_accompagnement'))
        with perimetre(self.uc,self.sa):
            self.assertEqual(m.Accompagnement.objects.count(),1)
            Service.objects.filter(pk=self.sa.pk).update(politique='individuel')
            self.assertEqual(m.Accompagnement.objects.count(),0)

    def test_terminer_intervention_http_ne_garde_pas_acces_individuel(self):
        from django.urls import reverse
        self.sa.politique='individuel';self.sa.save()
        r=Responsabilite.objects.create(dossier=self.da,professionnel=self.pa,debut=timezone.now()-timedelta(days=1),cree_par=self.admin)
        c=Client();c.force_login(self.ua)
        url=reverse('acteurs:terminer',args=[r.pk])
        self.assertEqual(c.get(url).status_code,200)
        reponse=c.post(url,{'date':timezone.localdate().isoformat(),'attendu':s.jeton(self.da)})
        self.assertEqual(reponse.status_code,302)
        self.assertEqual(reponse['Location'],'/')
        self.assertEqual(c.get(reverse('dossiers:detail',args=['menage',self.ma.pk])).status_code,404)

    def test_creation_menage_confie_collegue_sans_dossier_personnel_cache(self):
        from django.urls import reverse
        self.sa.politique='individuel';self.sa.save()
        c=Client();c.force_login(self.ua)
        r=c.post(reverse('dossiers:creer',args=['menage']),{'libelle':'Ménage créé pour collègue fictif','premiere_personne':'nouvelle',
            'designation':'Personne créée pour collègue fictif','prenom':'','debut':timezone.localdate().isoformat(),'responsable_acteurs':str(self.pc.pk)})
        self.assertEqual(r.status_code,302)
        self.assertEqual(r['Location'],'/')
        ds=DossierService.objects.get(menage__libelle='Ménage créé pour collègue fictif')
        personne=m.Personne._base_manager.get(designation='Personne créée pour collègue fictif')
        self.assertFalse(DossierService.objects.filter(personne=personne).exists())
        self.assertEqual(Responsabilite.objects.get(dossier=ds).professionnel,self.pc)
        with perimetre(self.ua,self.sa):self.assertFalse(m.Personne.objects.filter(pk=personne.pk).exists())
        with perimetre(self.uc,self.sa):self.assertTrue(m.Personne.objects.filter(pk=personne.pk).exists())

    def test_inventaire_refuse_parent_prive_absent_des_la_verification(self):
        import json
        from tempfile import TemporaryDirectory
        from pathlib import Path
        from io import StringIO
        from django.core.management import call_command,CommandError
        PorteeObjet.objects.filter(modele='personnes.accompagnement',identifiant=str(self.a.pk)).delete()
        PorteeObjet.objects.filter(modele='personnes.accordhebergement',identifiant=str(self.h.pk)).delete()
        d={'service':self.sa.pk,'dossiers':[{'nature':'menage','id':str(self.ma.pk),'objets':[{'modele':'personnes.accordhebergement','id':str(self.h.pk)}]}]}
        with TemporaryDirectory() as temporaire:
            f=Path(temporaire)/'inventaire.json';f.write_text(json.dumps(d))
            with self.assertRaises(CommandError):call_command('affecter_donnees_service',str(f),auteur=self.admin.username,stdout=StringIO())
        self.assertFalse(PorteeObjet.objects.filter(modele='personnes.accordhebergement',identifiant=str(self.h.pk)).exists())

    def test_creation_revalide_lien_professionnel_meme_apres_lecture(self):
        from django.db import models
        sans_appartenance=m.Intervenant.objects.create(libelle='Autre professionnel fictif non habilité',cree_par=self.admin)
        with perimetre(self.ua,self.sa):
            self.assertTrue(m.Menage.objects.exists())
            # Simuler une modification externe qui ne partage pas le cache local.
            models.QuerySet(model=LienCompteProfessionnel).filter(compte=self.ua).update(professionnel=sans_appartenance)
            with self.assertRaises((ValidationError,PermissionDenied)):
                m.Personne.objects.create(designation='Création après changement interdite',cree_par=self.ua)
