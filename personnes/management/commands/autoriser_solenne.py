from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

DROITS = {'view_complementidentite','add_complementidentite','change_complementidentite','view_revisioncomplementidentite',
    'view_relationpersonnelle','add_relationpersonnelle','change_relationpersonnelle','annuler_relationpersonnelle','view_revisionrelationpersonnelle','view_propositionsaisie', 'add_propositionsaisie', 'change_propositionsaisie', 'view_revisionpropositionsaisie', 'view_declarationfamiliale', 'add_declarationfamiliale', 'change_declarationfamiliale',
    'view_revisiondeclarationfamiliale', 'corriger_prevision_accompagnement', 'view_evolutionpriseencharge',
    'view_coordonneespersonnelles', 'add_coordonneespersonnelles', 'change_coordonneespersonnelles',
    'view_revisioncoordonneespersonnelles', 'view_contactmenage', 'add_contactmenage',
    'change_contactmenage', 'view_revisioncontactmenage', 'view_partenaire', 'add_partenaire',
    'view_fichepartenaire', 'add_fichepartenaire', 'change_fichepartenaire', 'view_revisionfichepartenaire',
    'view_intervenant', 'add_intervenant', 'view_ficheintervenant', 'add_ficheintervenant',
    'change_ficheintervenant', 'view_revisionficheintervenant', 'view_affectationintervenant',
    'add_affectationintervenant', 'change_affectationintervenant', 'view_revisionaffectationintervenant', 'annuler_affectationintervenant'}

# Droits des schémas personnels concrets du méta-lot A.
DROITS.update({'view_situationadministrative','add_situationadministrative','change_situationadministrative','view_revisionsituationadministrative'})
for nom in ('ressourcepersonnelle','dettepersonnelle','pieceadministrative','couverturesociale','protectionjuridique'):
    DROITS.update({'view_'+nom,'add_'+nom,'change_'+nom,'annuler_'+nom,'view_revision'+nom})

for racine, version, journal in (('demandeaccueil','versiondemande','revisiondemande'),('orientationparcours','versionorientation','revisionorientation'),('objectifparcours','versionobjectif','revisionobjectif'),('reperedossier','versionreperedossier','revisionreperedossier')):
    DROITS.update({'view_'+racine,'add_'+racine,'change_'+racine,'annuler_'+racine,'view_'+version,'view_'+journal})

DROITS.update({'view_revisioncontinuite','change_continuitesejour','view_revisionservicerepas','view_revisionlieu','change_lieuhebergement','view_typeaide','add_typeaide','change_typeaide','view_revisiontypeaide','view_accordaide','add_accordaide','change_accordaide','annuler_accordaide','view_remiseaide','add_remiseaide','change_remiseaide','annuler_remiseaide','view_revisionaide','view_usageaide','add_usageaide','view_revisionrepas','view_continuitesejour','add_continuitesejour'})



class Command(BaseCommand):
    help = 'Attribuer volontairement les droits livrés de reprise Solenne à un compte existant ; les droits CHRS restent indépendants.'

    def add_arguments(self, parser):
        parser.add_argument('identifiant')

    @transaction.atomic
    def handle(self, *args, **options):
        permissions = list(Permission.objects.filter(content_type__app_label='personnes', codename__in=DROITS))
        if len(permissions) != len(DROITS):
            raise CommandError('Appliquez les migrations avant cette attribution.')
        try:
            compte = get_user_model().objects.get(username=options['identifiant'])
        except get_user_model().DoesNotExist as erreur:
            raise CommandError('Compte inconnu ; aucun compte créé.') from erreur
        compte.user_permissions.add(*permissions)
        self.stdout.write('Droits Solenne attribués explicitement, sans administration ni suppression.')
