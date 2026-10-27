from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand,CommandError
from acteurs.essai import preparer


class Command(BaseCommand):
    help='Sur une base métier vide uniquement : préparer des dossiers fictifs et activer les accès pour des comptes existants explicitement désignés.'
    def add_arguments(self,p):
        p.add_argument('--compte-social',required=True)
        p.add_argument('--compte-accueil')
        p.add_argument('--compte-coordination')
        p.add_argument('--confirmer',action='store_true')
    def handle(self,*args,**o):
        if not o['confirmer']:raise CommandError('Essai fictif sur base vide uniquement. Ajoutez --confirmer pour accorder les tâches explicitement désignées et activer le contrôle.')
        try:
            def compte(cle):return get_user_model().objects.get(username=o[cle],is_active=True) if o[cle] else None
            service=preparer(compte('compte_social'),compte('compte_accueil'),compte('compte_coordination'))
        except (get_user_model().DoesNotExist,ValidationError) as e:
            raise CommandError(' '.join(e.messages) if isinstance(e,ValidationError) else 'Compte existant introuvable.') from e
        self.stdout.write(f'Essai fictif actif : service {service.pk}. Aucun compte créé. Ouvrez Dossiers ; la configuration est dans Organisation. Le compte social peut exporter et consulter les statistiques de son service.')
