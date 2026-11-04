"""Scénario COL2–4, créé uniquement avec le jeu neuf Les Passerelles."""
from datetime import timedelta,date
from decimal import Decimal
from django.utils import timezone
from django.core.management import call_command
from io import StringIO
from acteurs.models import Service,AppartenanceProfessionnelle
from acteurs.profils_collectifs import defaut
from acteurs.contexte import perimetre
from acteurs import services
from . import models as m, suivi, collectifs as c

def completer(auteur,etablissement,professionnel):
    call_command('autoriser_collectif',auteur.username,stdout=StringIO())
    auteur=type(auteur).objects.get(pk=auteur.pk)
    jour=timezone.localdate();entree=jour-timedelta(days=14)
    service=Service.objects.create(etablissement=etablissement,libelle='Les Amandiers',profil_collectif=defaut())
    AppartenanceProfessionnelle.objects.create(service=service,professionnel=professionnel,debut=entree)
    services.habiliter(auteur,auteur,service,'social',entree,statistiques_service=True,exporter=True,corriger_autrui=True)
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
        c.creer(auteur,prise,'hebergement',comp,c.jeton(prise),[],debut=entree,arrivee=entree,fin_prevue=prise.fin_prevue,lieu=lieu)
        prise=m.Accompagnement.objects.select_related('menage').get(pk=prise.pk)
        c.creer(auteur,prise,'restauration',comp,c.jeton(prise),[
            {'categorie':'adulte','nombre':2,'prix':Decimal('8')},
            {'categorie':'enfant','nombre':2,'prix':Decimal('5')}],
            debut=entree,fin_prevue=prise.fin_prevue,dejeuner=True,diner=True,premier='diner',dernier='dejeuner')
    return service
