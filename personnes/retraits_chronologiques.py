"""Retrait conservatoire des seules séries personnelles à valeur unique.

Les collections (dettes, ressources détaillées, liens...) ne sont pas des
valeurs uniques : elles conservent leurs opérations spécialisées.
"""
from dataclasses import dataclass
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from . import models as m, famille, coordonnees, complements_identite, dossier_complet
from .series_personnelles import photographie

SEL = 'condition-retrait-v1'


@dataclass(frozen=True)
class Serie:
    modele: type
    journal: type
    champs: tuple
    lien: str
    titre: str
    dimension: str = ''


def series():
    out = {
        'famille': Serie(m.DeclarationFamiliale, m.RevisionDeclarationFamiliale, famille.CHAMPS, 'declaration', 'Situation familiale'),
        'coordonnees': Serie(m.CoordonneesPersonnelles, m.RevisionCoordonneesPersonnelles, coordonnees.CHAMPS, 'coordonnees', 'Coordonnées'),
        'complements': Serie(m.ComplementIdentite, m.RevisionComplementIdentite, complements_identite.CHAMPS, 'complement', 'Identité déclarée'),
        'administration': Serie(m.SituationAdministrative, m.RevisionSituationAdministrative, dossier_complet.ADMIN_CHAMPS, 'situation', 'Administration et droits')}
    for dimension, titre in m.SituationSociale.DIMENSIONS:
        code = 'ressources-globales' if dimension == 'ressources' else dimension
        out[code] = Serie(m.SituationPersonnelle, m.RevisionSituationPersonnelle, ('valeur',), 'situation', titre, dimension)
    return out


def configuration(code):
    try:
        return series()[code]
    except KeyError:
        raise ValidationError('Cette rubrique ne possède pas de retrait chronologique.')


def droits(serie):
    return ('personnes.view_personne', 'personnes.view_' + serie.modele._meta.model_name,
            'personnes.view_' + serie.journal._meta.model_name,
            'personnes.add_' + serie.modele._meta.model_name, 'personnes.change_' + serie.modele._meta.model_name)


def selection(serie, personne):
    q = serie.modele.objects.filter(personne=personne)
    return q.filter(dimension=serie.dimension) if serie.dimension else q


def etat(serie, personne):
    if serie.dimension:
        from .bd6 import photographie as photo_sociale
        return photo_sociale(personne, serie.dimension)
    return photographie(personne, serie.modele, serie.champs)


def apercu(acteur, personne, code, fait_pk):
    serie = configuration(code)
    if not acteur.has_perms(droits(serie)):
        raise PermissionDenied
    try:
        fait = selection(serie, personne).get(pk=fait_pk)
    except serie.modele.DoesNotExist:
        raise ValidationError('Changement introuvable, retiré ou étranger à cette personne.')
    precedent = selection(serie, personne).filter(debut__lt=fait.debut).order_by('-debut', '-pk').first()
    if precedent and precedent.fin != fait.debut:
        precedent = None  # Ne pas combler une période sans information.
    return serie, fait, precedent


def preuve(code, personne, fait, precedent):
    return signing.dumps([code, str(personne.pk), fait.pk, fait.debut.isoformat(),
        fait.fin.isoformat() if fait.fin else None, precedent.pk if precedent else None], salt=SEL)


def prises_concernees(acteur, personne, debut, fin):
    from . import dossier
    if not acteur.has_perms(dossier.DROITS):
        return None
    q = m.Accompagnement.objects.filter(beneficiaires=personne, debut__gte=debut)
    if fin:
        q = q.filter(debut__lt=fin)
    q = q.select_related('menage').distinct().order_by('debut', 'pk')
    return {'nombre': q.count(), 'entrees': list(q[:10])}


def retirer(acteur, personne, code, fait_pk, attendu, preuve_portee, confirmer, motif=''):
    serie = configuration(code)
    if not acteur.has_perms(droits(serie)):
        raise PermissionDenied
    if confirmer is not True:
        raise ValidationError('Confirmez le retrait après lecture de sa portée.')
    if len(motif) > 240:
        raise ValidationError({'motif': 'Le contexte est limité à 240 caractères.'})
    with transaction.atomic():
        from . import bd6
        from django.utils import timezone
        bd6.reserver(personne, attendu)
        serie, fait, precedent = apercu(acteur, personne, code, fait_pk)
        try:
            portee = signing.loads(preuve_portee, salt=SEL, max_age=86400)
            courante = signing.loads(preuve(code, personne, fait, precedent), salt=SEL)
        except (signing.BadSignature, TypeError):
            raise ValidationError('Portée non vérifiable. Rechargez avant de confirmer.')
        if portee != courante:
            raise ValidationError('La portée a changé. Rechargez avant de confirmer.')
        avant = etat(serie, personne)
        fait.retire_le = timezone.now()
        fait.save(update_fields=['retire_le'])
        if precedent:
            precedent.fin = fait.fin
            precedent.full_clean()
            precedent.save(update_fields=['fin'])
        serie.journal.objects.create(personne=personne, **{serie.lien: fait}, action='retrait',
            avant=avant, apres=etat(serie, personne), motif=motif.strip(), auteur=acteur)
        return fait
