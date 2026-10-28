from django.test import TestCase,Client
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from . import tests as anciens,services as s,notifications as n
from .models import Responsabilite
from .contexte import perimetre

class MessagesAttributionTests(TestCase):
    setUp=anciens.AccesTests.setUp
    compte=anciens.AccesTests.compte
    dossier=anciens.AccesTests.dossier
    def test_auteur_et_message_notifies_sans_perdre_la_trace(self):
        x=s.ajouter_responsabilite(self.ua,self.da,self.da,self.pc,timezone.localdate(),'suivi',s.jeton(self.da),message='  Remplacement pendant mon absence.  ')
        self.assertEqual(x.message,'Remplacement pendant mon absence.')
        self.assertEqual(x.auteur_affiche,str(self.pa))
        self.pa.libelle='Nom modifié ensuite';self.pa.save()
        x.refresh_from_db();self.assertNotEqual(x.auteur_affiche,str(self.pa))
        c=Client();c.force_login(self.uc);r=c.get(reverse('acteurs:notifications'))
        self.assertContains(r,'Remplacement pendant mon absence.');self.assertContains(r,x.auteur_affiche)
    def test_champ_facultatif_et_audience_explicite(self):
        c=Client();c.force_login(self.ua)
        r=c.get(reverse('acteurs:attribuer_dossier',args=[self.da.pk]))
        self.assertContains(r,'Ce n’est pas un message privé.')
        self.assertContains(r,'ce dossier')
        x=s.ajouter_responsabilite(self.ua,self.da,self.da,self.pc,timezone.localdate(),'suivi',s.jeton(self.da))
        self.assertEqual(x.message,'')
    def test_message_trop_long_annule_attribution(self):
        with self.assertRaises(ValidationError):s.ajouter_responsabilite(self.ua,self.da,self.da,self.pc,timezone.localdate(),'suivi',s.jeton(self.da),message='x'*1001)
        self.assertFalse(Responsabilite.objects.filter(dossier=self.da,professionnel=self.pc).exists())
