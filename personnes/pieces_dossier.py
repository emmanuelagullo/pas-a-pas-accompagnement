"""Pièces opaques de petit volume : octets et versions dans la copie transactionnelle.

Aucun chemin local fourni par l'utilisateur, lancement de programme ou rendu
HTML d'un fichier. Les téléchargements privés restituent les octets conservés.
"""
import hashlib
import unicodedata
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from . import models as m, suivi, bd6

MAX_FICHIER=5*1024*1024
CIBLES={'personne':m.Personne,'menage':m.Menage,'accompagnement':m.Accompagnement}


def nature(cible):
    for code,model in CIBLES.items():
        if isinstance(cible,model):return code
    raise ValidationError('Cible de document inconnue.')


def droit(acteur,cible):
    suivi.exiger(acteur,'view_personne','view_piecedossier','view_versionpiecedossier','view_'+nature(cible))
    if isinstance(cible,m.Accompagnement):suivi.exiger(acteur,'view_personne','view_menage')


def reserver(cible,attendu):
    if isinstance(cible,m.Accompagnement):m.Menage.objects.filter(pk=cible.menage_id).update(revision=F('revision')+1)
    bd6.reserver(cible,attendu)


def lire_fichier(fichier):
    if fichier.size<=0 or fichier.size>MAX_FICHIER:raise ValidationError({'fichier':'Choisissez un fichier non vide de 5 Mio maximum.'})
    nom=fichier.name
    if len(nom)>180 or any(c in nom for c in '/\\') or any(unicodedata.category(c).startswith('C') for c in nom):raise ValidationError({'fichier':'Utilisez un nom de fichier simple de 180 caractères au plus.'})
    contenu=fichier.read(MAX_FICHIER+1)
    if not contenu or len(contenu)>MAX_FICHIER:raise ValidationError({'fichier':'Choisissez un fichier non vide de 5 Mio maximum.'})
    return nom,contenu


@transaction.atomic
def ajouter(acteur,cible,attendu,*,titre,date_document,source,fichier,piece=None,motif=''):
    droit(acteur,cible)
    suivi.exiger(acteur,'add_versionpiecedossier', 'add_piecedossier' if piece is None else 'change_piecedossier')
    if not titre.strip() or len(titre)>160:raise ValidationError({'titre':'Nommez ce document (160 caractères au plus).'})
    if not source.strip() or len(source)>160:raise ValidationError({'source':'Indiquez la provenance du fichier (160 caractères au plus).'})
    if date_document and date_document>timezone.localdate():raise ValidationError({'date_document':'La date du document ne peut pas être future.'})
    if fichier is not None:nom,contenu=lire_fichier(fichier)
    elif piece is None:raise ValidationError({'fichier':'Choisissez le fichier à conserver.'})
    reserver(cible,attendu)
    if piece is None:piece=m.PieceDossier.objects.create(**{nature(cible):cible},auteur=acteur)
    else:
        piece=m.PieceDossier.objects.get(pk=piece.pk)
        if getattr(piece,nature(cible)+'_id')!=cible.pk:raise ValidationError('Ce document appartient à une autre cible.')
        if piece.annule_le:raise ValidationError('Une pièce annulée conserve ses versions mais ne peut plus être modifiée.')
        if not motif.strip() or len(motif)>240:raise ValidationError({'motif':'Expliquez ce remplacement ou cette correction (240 caractères au plus).'})
    derniere=piece.versions.first()
    if fichier is None:
        nom=derniere.nom_fichier;contenu=octets(acteur,derniere)
    v=m.VersionPieceDossier(piece=piece,version=derniere.version+1 if derniere else 1,titre=titre.strip(),date_document=date_document,nom_fichier=nom,contenu=contenu,taille=len(contenu),empreinte=hashlib.sha256(contenu).hexdigest(),source=source.strip(),motif=motif.strip(),auteur=acteur)
    v.full_clean();v.save();return piece


@transaction.atomic
def annuler(acteur,piece,attendu,motif):
    cible=piece.cible;droit(acteur,cible);suivi.exiger(acteur,'annuler_piecedossier')
    reserver(cible,attendu);piece=m.PieceDossier.objects.get(pk=piece.pk)
    if type(piece.cible) is not type(cible) or piece.cible.pk!=cible.pk:raise ValidationError('La cible de cette pièce a changé. Rechargez le dossier.')
    if piece.annule_le:raise ValidationError('Ce document est déjà annulé.')
    if not motif.strip() or len(motif)>240:raise ValidationError({'motif':'Expliquez l’annulation (240 caractères au plus).'})
    piece.annule_le=timezone.now();piece.annule_par=acteur;piece.motif_annulation=motif.strip();piece.full_clean();piece.save(update_fields=['annule_le','annule_par','motif_annulation'])


def octets(acteur,version):
    droit(acteur,version.piece.cible)
    contenu=bytes(version.contenu)
    if len(contenu)!=version.taille or hashlib.sha256(contenu).hexdigest()!=version.empreinte:raise ValidationError('Le contenu conservé ne correspond plus à son empreinte. Aucun fichier altéré n’est téléchargé.')
    return contenu
