"""Configuration technique explicite : aucun accès de dossier n'est accordé."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from personnes.models import Partenaire
from acteurs.models import OrganismeGestionnaire, Etablissement, Service


class Command(BaseCommand):
    help='Préparer un service depuis des organismes existants ; autoriser un compte existant à configurer seulement l’organisation.'
    def add_arguments(self,p):
        p.add_argument('--organisme',required=True,help='UUID explicite de la fiche de l’organisme gestionnaire.')
        p.add_argument('--etablissement',required=True,help='UUID explicite de la fiche de l’établissement.')
        p.add_argument('--service',required=True)
        p.add_argument('--compte-configuration',required=True)
        p.add_argument('--confirmer',action='store_true')
    @transaction.atomic
    def handle(self,*args,**o):
        if not o['confirmer']:raise CommandError('Ajoutez --confirmer après vérification des identifiants. Aucun droit de dossier ne sera attribué.')
        try:
            organisme=Partenaire.objects.get(pk=o['organisme']);fiche=Partenaire.objects.get(pk=o['etablissement'])
            compte=get_user_model().objects.get(username=o['compte_configuration'],is_active=True)
        except (Partenaire.DoesNotExist,get_user_model().DoesNotExist,ValueError,ValidationError) as e:
            raise CommandError('Organisme, établissement ou compte existant introuvable.') from e
        g,_=OrganismeGestionnaire.objects.get_or_create(organisme=organisme)
        etab,_=Etablissement.objects.get_or_create(fiche=fiche,defaults={'organisme':g})
        if etab.organisme_id!=g.pk:raise CommandError('L’établissement relève déjà d’un autre organisme.')
        service,_=Service.objects.get_or_create(etablissement=etab,libelle=o['service'])
        service.full_clean()
        compte.user_permissions.add(Permission.objects.get(content_type__app_label='acteurs',codename='gerer_organisation'))
        self.stdout.write(f'Service {service.pk} préparé. Configuration autorisée, sans habilitation de service ni accès de dossier ajouté.')
