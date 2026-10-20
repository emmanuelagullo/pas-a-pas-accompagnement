from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = 'Attribuer explicitement CHRS1–7, corrections comprises, au compte fictif choisi.'

    def add_arguments(self,parser):parser.add_argument('identifiant')

    @transaction.atomic
    def handle(self,*args,**options):
        droits={'change_accordrepas','change_accordhebergement','change_evenementsocial','change_bilansocial','view_correctionperiode','view_revisiontextesocial'}
        permissions=list(Permission.objects.filter(content_type__app_label='personnes',codename__in=droits))
        if len(permissions)!=len(droits):raise CommandError('Appliquez les migrations avant cette attribution.')
        call_command('autoriser_chrs4',options['identifiant'],stdout=self.stdout)
        get_user_model().objects.get(username=options['identifiant']).user_permissions.add(*permissions)
        self.stdout.write('Droits CHRS1–7 attribués explicitement, sans administration ni suppression.')
