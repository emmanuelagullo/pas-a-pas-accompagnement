"""Essai volontaire sur une base métier vide, sans créer de compte."""
from datetime import timedelta
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from personnes import models as m
from .models import *
from . import services as s
from .contexte import courant


@transaction.atomic
def preparer(social, accueil=None, coordination=None):
    if courant() or m.Personne._base_manager.exists() or m.Menage._base_manager.exists() or Service.objects.exists():
        raise ValidationError('Cet essai exige une base métier vide ; aucune donnée existante ne sera modifiée.')
    comptes=[x for x in (social,accueil,coordination) if x]
    if len({x.pk for x in comptes})!=len(comptes) or any(not x.is_active for x in comptes):
        raise ValidationError('Choisissez des comptes existants, actifs et distincts.')
    social.user_permissions.add(Permission.objects.get(content_type__app_label='acteurs',codename='gerer_organisation'))
    for attribut in ('_perm_cache','_user_perm_cache','_group_perm_cache'):
        social.__dict__.pop(attribut,None)
    org=m.Partenaire.objects.create(libelle='Association fictive Les Passerelles',cree_par=social)
    g=OrganismeGestionnaire.objects.create(organisme=org)
    fiche=m.Partenaire.objects.create(libelle='Établissement Les Passerelles — essai acteurs',cree_par=social)
    etab=Etablissement.objects.create(organisme=g,fiche=fiche)
    service=Service.objects.create(etablissement=etab,libelle='Accompagnement — essai fictif')
    autre=Service.objects.create(etablissement=etab,libelle='Autre service — essai fictif',politique='individuel')
    hier=timezone.localdate()-timedelta(days=30)
    debut=timezone.now()-timedelta(days=30)
    def professionnel(nom,compte=None,tache=None,**options):
        p=m.Intervenant.objects.create(libelle=nom,cree_par=social)
        AppartenanceProfessionnelle.objects.create(service=service,professionnel=p,debut=hier)
        if compte:
            LienCompteProfessionnel.objects.create(compte=compte,professionnel=p)
            s.habiliter(social,compte,service,tache,hier,**options)
        return p
    moi=professionnel('Professionnel social fictif',social,'social',statistiques_service=True,exporter=True,corriger_autrui=True)
    collegue=professionnel('Collègue fictif — sans compte')
    nuit=professionnel('Accueil fictif',accueil,'accueil')
    if coordination:professionnel('Coordination fictive',coordination,'coordination',statistiques_service=True,statistiques_etablissement=True)
    def dossier(nom,prof=None,attente=False,termine=False,cible_service=service):
        personne=m.Personne.objects.create(designation=nom,cree_par=accueil if attente and accueil else social)
        menage=m.Menage.objects.create(libelle=nom,cree_par=social)
        lien=m.Appartenance.objects.create(personne=personne,menage=menage,debut=hier)
        ds=DossierService.objects.create(service=cible_service,menage=menage,en_attente=attente,cree_par=social)
        prise=m.Accompagnement.objects.create(menage=menage,debut=hier,
            fin=timezone.localdate()-timedelta(days=2) if termine else None,cree_par=social)
        prise.beneficiaires.add(personne)
        for objet in (personne,menage,lien,prise):
            PorteeObjet.objects.create(modele=objet._meta.label_lower,identifiant=str(objet.pk),dossier=ds,service=cible_service,
                prise=prise if objet==prise else None)
        if prof:Responsabilite.objects.create(dossier=ds,professionnel=prof,debut=debut,cree_par=social)
        return ds,personne,prise
    dossier('Essai — Mon dossier en cours',moi)
    dossier('Essai — En attente de suivi',attente=True)
    dossier('Essai — Dossier du collègue',collegue)
    dossier('Essai — Mon dossier terminé',moi,termine=True)
    ds,personne,prise=dossier('Essai — Ma prestation seule',collegue)
    accord=m.AccordHebergement.objects.create(accompagnement=prise,debut=hier,fin=timezone.localdate()+timedelta(days=30),cree_par=social)
    accord.beneficiaires.add(personne)
    PorteeObjet.objects.create(modele=accord._meta.label_lower,identifiant=str(accord.pk),dossier=ds,service=service,prise=prise,
        prestation_modele='accordhebergement',prestation_id=accord.pk)
    Responsabilite.objects.create(dossier=ds,professionnel=moi,hebergement=accord,debut=debut,cree_par=social)
    dossier('Essai — Dossier réservé à un autre service',cible_service=autre)
    ConfigurationAcces.objects.update_or_create(pk=1,defaults={'active':True})
    s.journal(social,service,'essai_fictif',{}, {'controle_actif':True,'comptes_crees':0})
    return service
