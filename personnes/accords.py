"""BD3 : décisions sur les accords, sans réécriture des réalisations."""
from django.core import signing
from django.core.exceptions import ValidationError
from django.utils import timezone
from . import models as m
from .suivi import exiger
from .verrous_metier import serialiser
from .corrections import motif_valide

MODELES = {'repas': m.AccordRepas, 'hebergement': m.AccordHebergement}


def droits(acteur, accord, action):
    nature = accord._meta.model_name
    exiger(acteur, 'view_personne', 'view_menage', 'view_accompagnement', 'view_' + nature,
           action + '_' + nature, 'view_evolutionaccord')
    exiger(acteur, 'view_repasdistribue' if isinstance(accord, m.AccordRepas) else 'view_sejour')


def exiger_actif(accord):
    if accord.annule_le is not None:
        raise ValidationError('Cet accord est annulé. Son historique reste consultable ; aucune nouvelle opération ne peut lui être rattachée.')


def etat(accord):
    a = accord.accompagnement
    nombre = accord.realisations.count() if isinstance(accord, m.AccordRepas) else accord.sejours.count()
    return [accord._meta.model_name, str(accord.pk), accord.revision, str(accord.debut), str(accord.fin),
            str(accord.annule_le), str(a.debut), str(a.fin),
            sorted(str(pk) for pk in accord.beneficiaires.values_list('pk', flat=True)), nombre, getattr(accord,'jours_semaine',[])]


def jeton(accord):
    return signing.dumps(etat(accord), salt='bd3-accord')


def verifier(accord, attendu):
    try:
        precedent = signing.loads(attendu, salt='bd3-accord', max_age=86400)
    except (signing.BadSignature, TypeError, ValueError) as exc:
        raise ValidationError('Le formulaire a expiré. Rechargez l’accord.') from exc
    if precedent != etat(accord):
        raise ValidationError('L’accord, ses bénéficiaires ou ses opérations ont changé. Rechargez la fiche avant de réessayer.')


def tracer(acteur, accord, action, ancienne_fin, nouvelle_fin, motif):
    lien = 'accord_repas' if isinstance(accord, m.AccordRepas) else 'accord_hebergement'
    m.EvolutionAccord.objects.create(**{lien: accord}, action=action,
        ancienne_fin=ancienne_fin, nouvelle_fin=nouvelle_fin, motif=motif, auteur=acteur)


@serialiser('accord')
def prolonger(acteur, accord, fin, motif, attendu):
    droits(acteur, accord, 'prolonger')
    accord = type(accord).objects.select_related('accompagnement').get(pk=accord.pk)
    exiger_actif(accord)
    verifier(accord, attendu)
    motif = motif_valide(motif)
    if accord.fin is None:
        raise ValidationError('Cet accord est déjà sans fin prévue ; il ne peut pas être prolongé.')
    if fin is not None and fin <= accord.fin:
        raise ValidationError('La nouvelle fin doit être postérieure à la fin actuelle, ou laissée vide pour une période ouverte.')
    if accord.accompagnement.fin and (fin is None or fin > accord.accompagnement.fin):
        raise ValidationError('La prolongation ne peut pas dépasser la fin de l’accompagnement. Elle ne le rouvre pas.')
    ancienne_fin = accord.fin
    accord.fin = fin
    accord.revision += 1
    accord.full_clean()
    accord.save(update_fields=['fin', 'revision'])
    tracer(acteur, accord, 'prolongation', ancienne_fin, fin, motif)
    return accord


@serialiser('accord')
def annuler(acteur, accord, motif, attendu):
    droits(acteur, accord, 'annuler')
    accord = type(accord).objects.select_related('accompagnement').get(pk=accord.pk)
    exiger_actif(accord)
    verifier(accord, attendu)
    motif = motif_valide(motif)
    dependances = accord.realisations if isinstance(accord, m.AccordRepas) else accord.sejours
    if dependances.exists():
        raise ValidationError('Cet accord possède déjà des distributions ou des séjours, même annulés ou terminés. Il ne peut pas être annulé par ce parcours.')
    accord.annule_le = timezone.now()
    accord.annule_par = acteur
    accord.motif_annulation = motif
    accord.revision += 1
    accord.full_clean()
    accord.save(update_fields=['annule_le', 'annule_par', 'motif_annulation', 'revision'])
    tracer(acteur, accord, 'annulation', accord.fin, accord.fin, motif)
    return accord
