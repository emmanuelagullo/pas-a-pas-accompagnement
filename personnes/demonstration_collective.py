"""Scénario COL2–4, créé uniquement avec le jeu neuf Les Passerelles."""
from datetime import timedelta,date
from decimal import Decimal
from django.utils import timezone
from django.core.management import call_command
from io import StringIO
from acteurs.models import Service,AppartenanceProfessionnelle,OffrePrestataire,TarifOffre
from acteurs.profils_collectifs import defaut
from acteurs.collecte import profil as profil_collecte
from acteurs.contexte import perimetre
from acteurs import services
from . import models as m, suivi, collectifs as c

def completer(auteur,etablissement,professionnel):
    call_command('autoriser_collectif',auteur.username,stdout=StringIO())
    auteur=type(auteur).objects.get(pk=auteur.pk)
    jour=timezone.localdate();entree=jour-timedelta(days=14)
    service=Service.objects.create(etablissement=etablissement,libelle='Les Amandiers',sous_titre='Accueil et hébergement des familles',profil_collectif=defaut(),collecte_rubriques=profil_collecte('menage'))
    service.listes_saisie = {'motif_entree': ['Mise à l’abri', 'Accueil d’une famille']}
    service.save(update_fields=['listes_saisie'])
    AppartenanceProfessionnelle.objects.create(service=service,professionnel=professionnel,debut=entree)
    services.habiliter(auteur,auteur,service,'social',entree,statistiques_service=True,exporter=True,corriger_autrui=True)
    lieu_repas=m.Partenaire.objects.create(libelle='La Table des Amandiers — fictive',cree_par=auteur)
    repas=OffrePrestataire.objects.create(lieu=lieu_repas,nature='restauration',libelle='La Table des Amandiers')
    hotel=OffrePrestataire.objects.create(lieu=etablissement.fiche,nature='hebergement',libelle='Résidence Les Amandiers')
    service.offres.set([repas,hotel]);service.catalogue_prestations=True;service.save(update_fields=['catalogue_prestations'])
    for code,label,prix in [('adulte','Adulte','8'),('enfant','Enfant','5'),('bas_age','Bas âge','0')]:
        tarif=m.TarifPrestation.objects.create(libelle='Repas — '+label,cree_par=auteur)
        m.VersionTarif.objects.create(tarif=tarif,version=1,debut=entree,libelle=tarif.libelle,unite='repas',categorie=label,montant=Decimal(prix),devise='EUR',prestataire=lieu_repas,source='Catalogue fictif',action='definition',auteur=auteur)
        TarifOffre.objects.create(offre=repas,categorie=code,libelle=label,tarif=tarif)
    with perimetre(auteur,service=service,creation='dossier',nature_creation='menage'):
        p=m.Personne.objects.create(designation='Élise Laurent',date_naissance=date(1988,4,12),precision_naissance='exacte',cree_par=auteur)
        menage=suivi.creer_menage(auteur,'Famille Laurent — Les Amandiers',[p],entree)
        prise=suivi.ouvrir(auteur,menage,[p],entree)
        prise.fin_prevue=jour+timedelta(days=14);prise.save(update_fields=['fin_prevue'])
        prise=m.Accompagnement.objects.select_related('menage').get(pk=prise.pk)
        comp=c.renseigner(auteur,prise,c.jeton(prise),debut=entree,reference=p,identifies=[p],
            complements=[{'categorie':'adulte','nombre':1,'age':None,'naissance':''},{'categorie':'enfant','nombre':2,'age':None,'naissance':''}],
            revenu=Decimal('1500'),devise='EUR',logement='Hébergement familial',projet='Retrouver un logement adapté à la famille.',actualiser=True)
        lieu=m.LieuHebergement.objects.create(libelle='Les Amandiers — appartement 4',niveau='logement',cree_par=auteur)
        prise=m.Accompagnement.objects.select_related('menage').get(pk=prise.pk)
        c.creer(auteur,prise,'hebergement',comp,c.jeton(prise),[],offre=hotel,debut=entree,arrivee=entree,fin_prevue=prise.fin_prevue,lieu=lieu)
        prise=m.Accompagnement.objects.select_related('menage').get(pk=prise.pk)
        c.creer(auteur,prise,'restauration',comp,c.jeton(prise),[
            {'categorie':'adulte','nombre':2,'prix':Decimal('8')},
            {'categorie':'enfant','nombre':2,'prix':Decimal('5')}],
            offre=repas,debut=entree,fin_prevue=prise.fin_prevue,dejeuner=True,diner=True,premier='diner',dernier='dejeuner')
    return service
