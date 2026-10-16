"""Parcours réels sur comptes fictifs, sans droit social implicite."""
from importlib.util import find_spec
from io import StringIO
import time
from unittest import skipUnless
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from pas_communs.authentification import totp
from . import configuration, double_facteur as facteur
from .models import DoubleFacteur, CodeSecours, LimiteAuthentification
from .vues import ATTENTE, PREUVE

DEPENDANCES=all(find_spec(n) is not None for n in ("cryptography","qrcode","django_otp"))
CLE="MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="  # uniquement fictive
MOT="Phrase fictive de test-7834"
RAPIDE=["django.contrib.auth.hashers.MD5PasswordHasher"]


@skipUnless(DEPENDANCES,"requirements-2fa.txt non installé")
@override_settings(DOUBLE_FACTEUR_POLITIQUE="optionnel",DOUBLE_FACTEUR_CLES=[CLE],
    MODE_LOCAL=False,PASSWORD_HASHERS=RAPIDE,AUTH_TENTATIVES_COMPTE=50,AUTH_TENTATIVES_IP=200)
class ParcoursDoubleFacteur(TestCase):
    def setUp(self):
        self.user=get_user_model().objects.create_user("essai-fictif",password=MOT)
        self.horloge=patch("django_otp.oath.time",return_value=1800000000)
        self.horloge.start();self.addCleanup(self.horloge.stop)
        self.instant=1800000000

    def code(self,cle,instant=None):
        from django_otp.oath import TOTP
        t=TOTP(cle);t.time=self.instant if instant is None else instant
        return f"{t.token():06d}"

    def inscrire(self,user=None):
        user=user or self.user
        ligne=facteur.commencer(user)
        cle=totp.dechiffrer(ligne.cle_chiffree,cles=[CLE])
        revision,codes=facteur.confirmer(user,self.code(cle,self.instant-300),instant=self.instant-300)
        return cle,codes,revision

    def connecter(self,client=None):
        return (client or self.client).post(reverse("connexion"),{"username":self.user.username,"password":MOT})

    def session_verifiee(self):
        cle,codes,revision=self.inscrire()
        self.connecter()
        self.client.post(reverse("connexion_verification"),{"code":self.code(cle)})
        return cle,codes,revision

    def gestion(self,action,code="",**kwargs):
        return self.client.post(reverse("securite_compte"),{"action":action,"mot_de_passe":MOT,"code":code,**kwargs})

    def test_inscription_complete_et_codes_affiches_une_seule_fois(self):
        self.connecter()
        reponse=self.gestion("commencer")
        self.assertContains(reponse,"<svg")
        ligne=DoubleFacteur.objects.get(utilisateur=self.user)
        cle=totp.dechiffrer(ligne.cle_chiffree,cles=[CLE])
        self.assertNotIn(totp.cle_en_base32(cle),ligne.cle_chiffree)
        self.assertFalse(ligne.inscrit)
        self.assertNotContains(self.client.get(reverse("securite_compte")),totp.cle_en_base32(cle))
        reponse=self.gestion("confirmer",self.code(cle))
        self.assertContains(reponse,"Conserver les codes de secours")
        self.assertIn("no-store",reponse["Cache-Control"])
        self.assertEqual(CodeSecours.objects.count(),10)
        for code in reponse.context["codes"]:
            self.assertNotIn(code, str(list(CodeSecours.objects.values())))
        self.assertNotContains(self.client.get(reverse("securite_compte")),reponse.context["codes"][0])
        self.assertEqual(self.client.get(reverse("personnes:liste")).status_code,403)

    def test_changer_de_compte_exige_deconnexion_explicite(self):
        autre=get_user_model().objects.create_user("autre-compte-fictif",password=MOT)
        self.inscrire(autre)
        self.connecter()
        r=self.client.post(reverse("connexion"),{"username":autre.username,"password":MOT})
        self.assertEqual(r.status_code,302)
        self.assertEqual(self.client.session["_auth_user_id"],str(self.user.pk))
        self.assertNotIn(ATTENTE,self.client.session)

    def test_aucune_session_avant_code_puis_droits_inchanges(self):
        cle,codes,revision=self.inscrire()
        r=self.connecter()
        self.assertRedirects(r,reverse("connexion_verification"),fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id",self.client.session)
        self.assertEqual(self.client.get(reverse("personnes:liste")).status_code,302)
        r=self.client.post(reverse("connexion_verification"),{"code":self.code(cle)})
        self.assertEqual(r.status_code,302)
        self.assertEqual(self.client.session[PREUVE],revision)
        self.assertEqual(self.client.get(reverse("personnes:liste")).status_code,403)
        self.assertFalse(self.user.user_permissions.exists())

    def test_code_faux_rejoue_et_autre_compte_refuses(self):
        cle,codes,_=self.inscrire()
        autre=get_user_model().objects.create_user("autre-fictif",password=MOT)
        self.inscrire(autre)
        self.assertIsNone(facteur.verifier(autre,codes[0]))
        self.connecter()
        r=self.client.post(reverse("connexion_verification"),{"code":"12345"})
        self.assertContains(r,"Code incorrect")
        self.assertNotIn("_auth_user_id",self.client.session)
        self.client.post(reverse("connexion_verification"),{"code":self.code(cle)})
        second=Client();self.connecter(second)
        self.assertContains(second.post(reverse("connexion_verification"),{"code":self.code(cle)}),"Code incorrect")
        self.assertNotIn("_auth_user_id",second.session)

    def test_secours_usage_unique_et_remplacement_telephone(self):
        cle,codes,_=self.inscrire()
        self.connecter()
        self.client.post(reverse("connexion_verification"),{"code":codes[0]})
        self.assertIn("_auth_user_id",self.client.session)
        self.assertIsNone(facteur.verifier(self.user,codes[0]))
        r=self.gestion("remplacer",codes[1]);self.assertEqual(r.status_code,302)
        self.assertEqual(CodeSecours.objects.count(),0)
        self.assertTrue(DoubleFacteur.objects.get(utilisateur=self.user).a_reinscrire)
        self.assertRedirects(self.client.get(reverse("accueil")),reverse("securite_compte"),fetch_redirect_response=False)
        self.assertContains(self.gestion("commencer"),"<svg")

    def test_renouvellement_et_activation_ferment_les_autres_sessions(self):
        autre=Client();autre.force_login(self.user)
        cle,codes,_=self.session_verifiee()
        r=self.gestion("regenerer",codes[0])
        self.assertContains(r,"Conserver les codes de secours")
        self.assertIsNone(facteur.verifier(self.user,codes[1]))
        self.assertEqual(self.client.get(reverse("accueil")).status_code,200)
        self.assertEqual(autre.get(reverse("accueil")).status_code,302)
        self.assertNotIn("_auth_user_id",autre.session)

    @override_settings(DOUBLE_FACTEUR_POLITIQUE="obligatoire")
    def test_obligation_immediate_et_retrait_refuse_meme_post_direct(self):
        self.connecter()
        for nom in ["accueil","personnes:liste","changer_mot_de_passe"]:
            self.assertRedirects(self.client.get(reverse(nom)),reverse("securite_compte"),fetch_redirect_response=False)
        self.assertEqual(self.client.post(reverse("deconnexion")).status_code,302)
        cle,codes,_=self.session_verifiee()
        self.assertContains(self.gestion("retirer",codes[0]),"obligatoire")
        self.assertTrue(DoubleFacteur.objects.get(utilisateur=self.user).inscrit)

    def test_retrait_optionnel_confirme_et_revoque_ancienne_preuve(self):
        cle,codes,_=self.session_verifiee()
        r=self.gestion("retirer",codes[0]);self.assertEqual(r.status_code,302)
        self.assertFalse(DoubleFacteur.objects.get(utilisateur=self.user).inscrit)
        self.assertEqual(self.client.get(reverse("accueil")).status_code,200)
        self.assertEqual(CodeSecours.objects.count(),0)

    def test_session_sans_preuve_ou_preuve_ancienne_fermee(self):
        self.inscrire()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accueil")).status_code,302)
        self.assertNotIn("_auth_user_id",self.client.session)

    def test_attente_expire_ou_mot_de_passe_change(self):
        cle,codes,_=self.inscrire();self.connecter()
        s=self.client.session;s[ATTENTE]["jusqua"]=time.time()-1;s.save()
        self.assertRedirects(self.client.post(reverse("connexion_verification"),{"code":codes[0]}),reverse("connexion"),fetch_redirect_response=False)
        self.connecter();self.user.set_password("Autre phrase fictive-289");self.user.save()
        self.assertEqual(self.client.post(reverse("connexion_verification"),{"code":codes[0]}).status_code,302)
        self.assertNotIn("_auth_user_id",self.client.session)

    def test_ancienne_attente_refuse_meme_le_facteur_reinscrit(self):
        self.inscrire();self.connecter()
        call_command("reinitialiser_double_facteur",self.user.username,confirmer=True,stdout=StringIO())
        _,codes,_=self.inscrire()
        self.assertContains(self.client.post(reverse("connexion_verification"),{"code":codes[0]}),"Code incorrect")
        self.assertNotIn("_auth_user_id",self.client.session)
        self.assertIsNotNone(facteur.verifier(self.user,codes[0]))

    def test_backend_retire_annule_attente(self):
        _,codes,_=self.inscrire();self.connecter()
        with override_settings(AUTHENTICATION_BACKENDS=[]):
            self.client.post(reverse("connexion_verification"),{"code":codes[0]})
        self.assertNotIn(ATTENTE,self.client.session)
        self.assertNotIn("_auth_user_id",self.client.session)

    def test_compte_desactive_entre_deux_etapes(self):
        _,codes,_=self.inscrire();self.connecter()
        self.user.is_active=False;self.user.save()
        self.client.post(reverse("connexion_verification"),{"code":codes[0]})
        self.assertNotIn("_auth_user_id",self.client.session)

    def test_recuperation_terminal_revoque_sessions_attentes_et_secours(self):
        cle,codes,_=self.session_verifiee()
        pending=Client();self.connecter(pending)
        with self.assertRaises(CommandError):call_command("reinitialiser_double_facteur",self.user.username)
        out=StringIO();call_command("reinitialiser_double_facteur",self.user.username,confirmer=True,stdout=out)
        self.assertIn("Réinscription obligatoire",out.getvalue())
        self.assertNotIn("_auth_user_id",self.client.get(reverse("accueil")).wsgi_request.session)
        self.assertEqual(pending.post(reverse("connexion_verification"),{"code":codes[0]}).status_code,200)
        self.assertNotIn("_auth_user_id",pending.session)
        self.assertIsNone(facteur.verifier(self.user,codes[1]))
        self.connecter()
        self.assertRedirects(self.client.get(reverse("accueil")),reverse("securite_compte"),fetch_redirect_response=False)

    def test_configuration_disparue_et_profil_local_ne_contournent_pas_facteur(self):
        _,codes,_=self.inscrire()
        for reglages in [{"DOUBLE_FACTEUR_POLITIQUE":"desactive"},{"MODE_LOCAL":True},{"DOUBLE_FACTEUR_CLES":[]}]:
            with override_settings(**reglages):
                self.assertEqual(self.connecter().status_code,503)
                self.assertNotIn("_auth_user_id",self.client.session)

    def test_obligation_sans_service_ne_devient_pas_connexion_simple(self):
        with override_settings(DOUBLE_FACTEUR_POLITIQUE="obligatoire",DOUBLE_FACTEUR_CLES=[]):
            self.assertEqual(self.connecter().status_code,503)
            self.assertNotIn("_auth_user_id",self.client.session)
            self.client.force_login(self.user)
            self.assertEqual(self.client.get(reverse("personnes:liste")).status_code,503)
            self.assertNotIn("_auth_user_id",self.client.session)

    def test_cle_illisible_pas_de_reinscription_silencieuse(self):
        _,codes,_=self.inscrire();self.connecter()
        from cryptography.fernet import Fernet
        with override_settings(DOUBLE_FACTEUR_CLES=[Fernet.generate_key().decode()]):
            self.assertContains(self.client.post(reverse("connexion_verification"),{"code":"123456"}),"Code incorrect")
        self.assertTrue(DoubleFacteur.objects.get(utilisateur=self.user).inscrit)

    def test_redirection_externe_refusee(self):
        _,codes,_=self.inscrire()
        self.client.post(reverse("connexion"),{"username":self.user.username,"password":MOT,"next":"https://fictif.invalid/piege"})
        r=self.client.post(reverse("connexion_verification"),{"code":codes[0]})
        self.assertEqual(r.url,reverse("accueil"))

    def test_mutations_exigent_mot_de_passe_et_csrf(self):
        self.connecter()
        self.assertNotContains(self.gestion("commencer",mot_de_passe="faux"),"<svg")
        self.assertFalse(DoubleFacteur.objects.exists())
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        for nom,data in [("securite_compte",{"action":"commencer","mot_de_passe":MOT}),
                         ("connexion_verification",{"code":"123456"})]:
            self.assertEqual(client.post(reverse(nom),data).status_code,403)

    def test_journal_ne_contient_ni_secret_ni_codes(self):
        cle,codes,_=self.inscrire();self.connecter()
        with self.assertLogs("identites.securite",level="INFO") as logs:
            self.client.post(reverse("connexion_verification"),{"code":codes[0]})
        contenu=" ".join(logs.output)
        self.assertIn("auth.connexion_2fa",contenu)
        for secret in [MOT,codes[0],totp.cle_en_base32(cle),self.code(cle)]:self.assertNotIn(secret,contenu)

    def test_changement_mot_de_passe_conserve_session_et_facteur(self):
        _,codes,_=self.session_verifiee()
        autre=Client();self.connecter(autre)
        autre.post(reverse("connexion_verification"),{"code":codes[0]})
        r=self.client.post(reverse("changer_mot_de_passe"),{"old_password":MOT,
            "new_password1":"Nouvelle phrase fictive-834", "new_password2":"Nouvelle phrase fictive-834"})
        self.assertEqual(r.status_code,302)
        self.assertEqual(self.client.get(reverse("accueil")).status_code,200)
        self.assertEqual(autre.get(reverse("accueil")).status_code,302)
        self.assertTrue(DoubleFacteur.objects.get(utilisateur=self.user).inscrit)

    def test_exception_recuperation_profil_sans_2fa_explicitement_limitee(self):
        self.session_verifiee()
        with self.assertRaises(CommandError):
            call_command("reinitialiser_double_facteur",self.user.username,confirmer=True,profil_sans_2fa=True)
        with override_settings(MODE_LOCAL=True):
            call_command("reinitialiser_double_facteur",self.user.username,confirmer=True,profil_sans_2fa=True,stdout=StringIO())
            self.assertEqual(self.connecter().status_code,302)
        ligne=DoubleFacteur.objects.get(utilisateur=self.user)
        self.assertFalse(ligne.a_reinscrire)
        self.assertFalse(ligne.inscrit)
        self.assertFalse(self.user.user_permissions.exists())

    def test_rotation_chiffrement_conserve_ancienne_cle_et_secours(self):
        cle,codes,_=self.inscrire()
        from cryptography.fernet import Fernet
        with override_settings(DOUBLE_FACTEUR_CLES=[Fernet.generate_key().decode(),CLE]):
            self.assertIsNotNone(facteur.verifier(self.user,self.code(cle)))
            self.assertIsNotNone(facteur.verifier(self.user,codes[0]))

    def test_diagnostic_masque_cles_et_posts_meme_en_debug(self):
        from django.test import RequestFactory
        from django.views.debug import get_exception_reporter_filter
        from .vues import securite
        request=RequestFactory().post("/mon-compte/securite/",{"mot_de_passe":MOT,"code":"secret-fictif"})
        request.sensitive_post_parameters="__ALL__"
        with override_settings(DEBUG=True):
            filtre=get_exception_reporter_filter(request)
            self.assertNotIn(CLE,str(filtre.get_safe_settings()))
            donnees=filtre.get_post_parameters(request)
            self.assertNotIn(MOT,str(donnees))
            self.assertNotIn("secret-fictif",str(donnees))

    def test_configuration_invalide_refusee_explicitement(self):
        with self.assertRaises(ImproperlyConfigured):configuration.lire({"ACCOMPAGNEMENT_2FA":"obligatoir"})
        with override_settings(DOUBLE_FACTEUR_CLES=[]):
            with self.assertRaises(ImproperlyConfigured):configuration.verifier()
        with override_settings(DOUBLE_FACTEUR_CLES=["invalide"]):
            with self.assertRaises(ImproperlyConfigured):configuration.verifier()

    def test_codes_plafonnes_par_compte_puis_attente_abandonnee(self):
        _,codes,_=self.inscrire()
        a,b,c=Client(),Client(),Client()
        for client in (a,b,c):self.connecter(client)
        with override_settings(AUTH_TENTATIVES_COMPTE=2):
            for client in (a,b):
                self.assertEqual(client.post(reverse("connexion_verification"),{"code":"12345"}).status_code,200)
            self.assertEqual(c.post(reverse("connexion_verification"),{"code":codes[0]}).status_code,429)
        self.assertNotIn(ATTENTE,c.session)
        self.assertNotIn("_auth_user_id",c.session)

    @override_settings(AUTH_TENTATIVES_COMPTE=2)
    def test_gestion_plafonnee_et_mot_de_passe_ancien_trop_long_non_hache(self):
        self.connecter()
        for _ in range(2):self.gestion("commencer",mot_de_passe="faux")
        self.assertEqual(self.gestion("commencer").status_code,429)
        self.assertFalse(DoubleFacteur.objects.exists())

    def test_mot_de_passe_changement_plafonne_avant_hachage(self):
        self.connecter()
        with patch.object(get_user_model(),"check_password") as verifier:
            r=self.client.post(reverse("changer_mot_de_passe"),{"old_password":"x"*1025,
                "new_password1":"Nouvelle phrase fictive-834","new_password2":"Nouvelle phrase fictive-834"})
        self.assertEqual(r.status_code,200)
        verifier.assert_not_called()


@override_settings(PASSWORD_HASHERS=RAPIDE,AUTH_TENTATIVES_COMPTE=2,AUTH_TENTATIVES_IP=3)
class LimitesTests(TestCase):
    def test_connexion_limitee_par_compte_entre_clients_et_adresses(self):
        for i in range(2):
            self.assertEqual(Client().post(reverse("connexion"),{"username":"inconnu","password":"faux"},REMOTE_ADDR=f"192.0.2.{i}").status_code,200)
        self.assertEqual(Client().post(reverse("connexion"),{"username":"inconnu","password":"faux"},REMOTE_ADDR="192.0.2.3").status_code,429)
        self.assertFalse(LimiteAuthentification.objects.filter(cle__contains="inconnu").exists())

    def test_ip_commune_plusieurs_identifiants_et_fenetre_suivante(self):
        with patch("time.time",return_value=1800000000):
            for i in range(3):
                self.assertEqual(self.client.post(reverse("connexion"),{"username":f"inconnu{i}","password":"faux"}).status_code,200)
            self.assertEqual(self.client.post(reverse("connexion"),{"username":"encore","password":"faux"}).status_code,429)
        with patch("time.time",return_value=1800000000+settings.AUTH_FENETRE_SECONDES):
            self.assertEqual(self.client.post(reverse("connexion"),{"username":"encore","password":"faux"}).status_code,200)

    def test_compteur_bloque_si_stockage_indisponible(self):
        from django.db import OperationalError
        with patch("identites.limites.LimiteAuthentification.objects.get_or_create",side_effect=OperationalError):
            self.assertEqual(self.client.post(reverse("connexion"),{"username":"x","password":"x"}).status_code,429)

    def test_purge_ne_leve_pas_les_blocages_actuels(self):
        from django.utils import timezone
        from datetime import timedelta
        LimiteAuthentification.objects.create(cle="ancienne",expire_le=timezone.now()-timedelta(seconds=1))
        LimiteAuthentification.objects.create(cle="actuelle",expire_le=timezone.now()+timedelta(minutes=15))
        call_command("purger_limites_authentification",stdout=StringIO())
        self.assertEqual(list(LimiteAuthentification.objects.values_list("cle",flat=True)),["actuelle"])
