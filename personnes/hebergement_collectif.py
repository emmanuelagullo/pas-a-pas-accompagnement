"""Actions explicites sur une sélection de séjours, avec transaction unique."""
from django.core import signing
from django.core.exceptions import ValidationError
from . import hebergement as h
from .corrections import jeton as jeton_periode
from .verrous_metier import serialiser

ACTIONS = {'affecter': ('Affecter ou changer de lieu', ('add_affectation', 'change_affectation', 'view_affectation', 'view_lieuhebergement')),
    'absence': ('Enregistrer une absence', ('add_absence', 'view_absence')),
    'retour': ('Enregistrer un retour d’absence', ('change_absence', 'view_absence')),
    'sortie': ('Enregistrer la sortie', ('change_sejour', 'change_affectation', 'change_absence'))}


def sejours_ouverts(accord):
    return accord.sejours.non_annules().filter(fin__isnull=True).prefetch_related('beneficiaires', 'affectations', 'absences').order_by('pk')


def etat(sejour):
    return [str(sejour.debut), str(sejour.fin), sejour.revision,
        sorted([str(p.pk), str(p.debut), str(p.fin), str(p.lieu_id)] for p in sejour.affectations.all()),
        sorted([str(p.pk), str(p.debut), str(p.fin)] for p in sejour.absences.all())]


def jeton(accord, sejours):
    return signing.dumps([str(accord.pk), {str(s.pk): etat(s) for s in sejours}], salt='chrs25-selection')


@serialiser('accord')
def appliquer(acteur, accord, sejours, action, date, lieu, attendu):
    h.droit(acteur, 'view_sejour')
    if action not in ACTIONS:
        raise ValidationError('Choisissez une action proposée.')
    h.exiger(acteur, *ACTIONS[action][1])
    ids = {s.pk for s in sejours}
    selection = list(sejours_ouverts(accord).filter(pk__in=ids))
    if not ids or len(selection) != len(ids):
        raise ValidationError('Choisissez des séjours ouverts de cet accord.')
    try:
        precedent = signing.loads(attendu, salt='chrs25-selection', max_age=86400)
    except signing.BadSignature as exc:
        raise ValidationError('Le formulaire a expiré. Rechargez les séjours.') from exc
    if precedent[0] != str(accord.pk) or any(precedent[1].get(str(s.pk)) != etat(s) for s in selection):
        raise ValidationError('Un séjour sélectionné a changé. Rechargez le formulaire.')
    for s in selection:
        if action == 'affecter':
            if lieu is None:
                raise ValidationError('Choisissez un lieu.')
            ouvertes = [p for p in s.affectations.all() if p.fin is None]
            if len(ouvertes) > 1:
                raise ValidationError('Plusieurs affectations ouvertes : corrigez d’abord le séjour.')
            if ouvertes:
                h.changer_lieu(acteur, ouvertes[0], date, lieu, jeton_periode(ouvertes[0]))
            else:
                h.ajouter_periode(acteur, s, date, None, lieu)
        elif action == 'absence':
            h.ajouter_periode(acteur, s, date, None, absence=True)
        elif action == 'retour':
            ouvertes = [p for p in s.absences.all() if p.fin is None]
            if len(ouvertes) != 1:
                raise ValidationError('Chaque séjour sélectionné doit avoir exactement une absence ouverte.')
            h.terminer_periode(acteur, ouvertes[0], date)
        else:
            h.sortir(acteur, s, date)
    return len(selection)
