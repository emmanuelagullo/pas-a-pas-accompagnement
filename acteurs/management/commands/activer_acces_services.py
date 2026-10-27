from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from acteurs.models import ConfigurationAcces, Service, JournalAcces
from acteurs.politique import habilitations
from django.utils import timezone

class Command(BaseCommand):
    help='Activer explicitement le contrôle des accès ; les données sans affectation deviennent inaccessibles par le logiciel.'
    def add_arguments(self,p):
        p.add_argument('--auteur',required=True)
        p.add_argument('--confirmer',action='store_true')
    @transaction.atomic
    def handle(self,*args,**o):
        if not o['confirmer']:raise CommandError('Sauvegardez et vérifiez les affectations puis ajoutez --confirmer. Aucun droit ne sera créé.')
        try:auteur=get_user_model().objects.get(username=o['auteur'],is_active=True)
        except get_user_model().DoesNotExist as e:raise CommandError('Compte responsable introuvable.') from e
        if not Service.objects.exists() or not habilitations(auteur).exists():raise CommandError('Préparez au moins un service et une habilitation effective pour le compte responsable.')
        ConfigurationAcces.objects.update_or_create(pk=1,defaults={'active':True})
        for service in Service.objects.all():
            JournalAcces.objects.create(service=service,auteur=auteur,action='activation',date_effet=timezone.localdate(),apres={'controle_actif':True})
        self.stdout.write('Contrôle actif. Aucun accès global attribué. Les données sans affectation restent conservées et inaccessibles.')
