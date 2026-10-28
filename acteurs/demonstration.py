"""Enrichissement du jeu Les Passerelles neuf ; jamais d’une base existante."""
from datetime import timedelta
import re
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from personnes import models as m
from personnes.demonstration import espace_metier_vide, preparer_jeu_public
from pas_a_pas_accompagnement.demo import MOT_DE_PASSE
from . import services, politique, portees
from .models import (Service, OrganismeGestionnaire, Etablissement, LienCompteProfessionnel,
                     AppartenanceProfessionnelle, DossierService, PorteeObjet,
                     Responsabilite, ConfigurationAcces)


@transaction.atomic
def preparer():
    if not getattr(settings, 'DEMONSTRATION_PUBLIQUE', False):
        raise ValidationError('Parcours réservé à la démonstration publique jetable.')
    if get_user_model().objects.exists() or not espace_metier_vide() or Service.objects.exists():
        raise ValidationError('Base non vide : aucune donnée modifiée.')
    preparer_jeu_public()
    comptes={u.username:u for u in get_user_model().objects.all()}
    comptes['coordination']=get_user_model().objects.create_user('coordination',password=MOT_DE_PASSE)
    auteur=comptes['essai']
    auteur.user_permissions.add(Permission.objects.get(content_type__app_label='acteurs',codename='gerer_organisation'))
    organisme=m.Partenaire.objects.create(libelle='Association Les Passerelles',cree_par=auteur)
    fiche=m.Partenaire.objects.get(libelle='Établissement Les Passerelles (fictive)')
    org=OrganismeGestionnaire.objects.create(organisme=organisme)
    etab=Etablissement.objects.create(organisme=org,fiche=fiche)
    service=Service.objects.create(etablissement=etab,libelle='Accompagnement')
    debut=timezone.localdate()-timedelta(days=3650)
    pros={}
    for nom,libelle,tache,options in (
        ('essai','Alexis','social',dict(statistiques_service=True,exporter=True,corriger_autrui=True)),
        ('nadia','Nadia','social',dict(statistiques_service=True)),
        ('remi','Rémi','accueil',{}),('camille','Camille','gestion',{}),
        ('coordination','Coordination','coordination',dict(statistiques_service=True,statistiques_etablissement=True))):
        prof=m.Intervenant.objects.create(libelle=libelle,cree_par=auteur)
        pros[nom]=prof
        LienCompteProfessionnel.objects.create(compte=comptes[nom],professionnel=prof)
        AppartenanceProfessionnelle.objects.create(service=service,professionnel=prof,debut=debut)
        services.habiliter(auteur,comptes[nom],service,tache,debut,**options)
    # Les seuls dossiers du scénario sont ceux du jeu métier, sans duplication.
    for menage in m.Menage.objects.order_by('libelle','pk'):
        ds=DossierService.objects.create(service=service,menage=menage,cree_par=auteur,
                                         en_attente=menage.libelle.startswith('Noor'))
        PorteeObjet.objects.create(modele=menage._meta.label_lower,identifiant=str(menage.pk),service=service,dossier=ds)
        if not ds.en_attente:
            prof=pros['essai'] if menage.libelle.startswith(('Alex','Samira')) else pros['nadia']
            Responsabilite.objects.create(dossier=ds,professionnel=prof,cree_par=auteur)
    for personne in m.Personne.objects.all():
        lien=m.Appartenance.objects.filter(personne=personne).order_by('-debut','pk').first()
        ds=DossierService.objects.get(menage=lien.menage,service=service) if lien else DossierService.objects.create(service=service,personne=personne,cree_par=auteur,en_attente=True)
        PorteeObjet.objects.create(modele=personne._meta.label_lower,identifiant=str(personne.pk),service=service,dossier=ds)
    # Affectation limitée à cette génération fictive, dans la même transaction.
    # Les versions/journaux suivent leur parent exact ; aucune commande de reprise
    # de données existantes ne déduit ainsi des partages.
    restants=[]
    for modele in apps.get_app_config('personnes').get_models():
        if modele._meta.model_name in politique.REPERTOIRES|{'personne','menage','modelerapport','importparametrage'}:continue
        restants.extend(modele._base_manager.all())
    while restants:
        suivants=[]
        for objet in restants:
            parents=[f for f in objet._meta.fields if f.is_relation and f.remote_field.model._meta.app_label=='personnes' and f.remote_field.model._meta.model_name not in politique.REPERTOIRES and getattr(objet,f.attname,None)]
            if any(not PorteeObjet.objects.filter(modele=f.remote_field.model._meta.label_lower,identifiant=str(getattr(objet,f.attname))).exists() for f in parents):
                suivants.append(objet);continue
            origine=portees.parent(objet)
            prive=any(f.is_relation and f.remote_field.model._meta.app_label=='personnes' and f.remote_field.model._meta.model_name not in politique.REPERTOIRES and getattr(objet,f.attname,None) for f in objet._meta.fields)
            if not origine and prive:
                suivants.append(objet);continue
            prise=objet if objet._meta.model_name=='accompagnement' else (origine.prise if origine else None)
            prestation=objet if objet._meta.model_name in ('accordhebergement','accordrepas','accordaide') else None
            PorteeObjet.objects.create(modele=objet._meta.label_lower,identifiant=str(objet.pk),service=service,
                dossier=origine.dossier if origine else None,prise=prise,
                prestation_modele=prestation._meta.model_name if prestation else (origine.prestation_modele if origine else ''),
                prestation_id=prestation.pk if prestation else (origine.prestation_id if origine else None))
        if len(suivants)==len(restants):raise ValidationError('Portée fictive indéterminée : '+', '.join(sorted({x._meta.model_name for x in suivants})))
        restants=suivants
    # Une seule mention globale suffit pour les noms inventés du jeu neuf.
    for modele,champ in ((m.Personne,'designation'),(m.Menage,'libelle'),(m.Intervenant,'libelle'),(m.Partenaire,'libelle'),(m.LieuHebergement,'libelle'),(m.FichePartenaire,'nom'),(m.FicheIntervenant,'nom')):
        for objet in modele._base_manager.all():
            valeur=re.sub(r'\s*\((?:professionnel )?ficti(?:f|ve)s?\)','',getattr(objet,champ))
            if modele==m.Menage:valeur=valeur.replace(' — Établissement Les Passerelles','')
            modele._base_manager.filter(pk=objet.pk).update(**{champ:valeur})
    ConfigurationAcces.objects.update_or_create(pk=1,defaults={'active':True})
    services.journal(auteur,service,'demonstration_acteurs',{}, {'controle_actif':True,'jeu':'Les Passerelles'})
    return service
