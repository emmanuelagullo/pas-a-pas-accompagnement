"""Lecture chronologique d'un accompagnement, sans inférer un score social.

Les dates d'effet et les horodatages d'enregistrement sont conservés séparément.
La sélection des prestations dépend explicitement des droits du lecteur.
"""
from .models import SituationSociale, EvenementSocial, BilanSocial, RepasDistribue, Sejour


def construire(accompagnement, acteur, beneficiaire=None, debut=None, fin=None):
    """Retourne des lignes triées par date d'effet, fin de filtre incluse."""
    lignes = []

    def ajouter(date, enregistre, nature, texte, personne=None):
        if debut and date < debut or fin and date > fin:
            return
        if beneficiaire and personne != beneficiaire:
            return
        lignes.append({"date": date, "enregistre": enregistre, "nature": nature,
                       "texte": texte, "beneficiaire": personne})

    for s in SituationSociale.objects.filter(accompagnement=accompagnement).select_related('beneficiaire'):
        ajouter(s.debut, s.cree_le, 'Situation',
                f'{s.get_dimension_display()} : {s.libelle_valeur} (source : {s.source})', s.beneficiaire)
    if acteur.has_perm('personnes.view_evenementsocial'):
        for e in EvenementSocial.objects.filter(accompagnement=accompagnement).select_related('beneficiaire'):
            ajouter(e.date_effet, e.cree_le, 'Événement antérieur' if e.date_effet < accompagnement.debut else 'Événement',
                    e.texte + f' (source : {e.source})', e.beneficiaire)
    if acteur.has_perm('personnes.view_bilansocial') and not beneficiaire:
        for b in BilanSocial.objects.filter(accompagnement=accompagnement):
            ajouter(b.date_effet, b.cree_le, 'Bilan du ménage', b.texte)
    if acteur.has_perms(['personnes.view_accordrepas', 'personnes.view_repasdistribue']):
        for r in RepasDistribue.objects.filter(accord__accompagnement=accompagnement).select_related('beneficiaire', 'accord'):
            statut = 'annulé' if r.annule_le else 'réalisé'
            ajouter(r.date, r.cree_le, 'Repas', f'{r.quantite} × {r.accord.get_service_display()} ({statut})', r.beneficiaire)
    if acteur.has_perms(['personnes.view_accordhebergement', 'personnes.view_sejour']):
        for s in Sejour.objects.filter(accord__accompagnement=accompagnement).prefetch_related('beneficiaires'):
            for p in s.beneficiaires.all():
                ajouter(s.debut, s.cree_le, 'Admission', 'Entrée effective en hébergement', p)
                if s.fin:
                    ajouter(s.fin, s.cree_le, 'Sortie', 'Fin du séjour (date exclue)', p)
    return sorted(lignes, key=lambda l: (l['date'], l['enregistre'], l['nature'], str(l['beneficiaire'])))


def comparer(accompagnement, beneficiaire, date_initiale, date_finale):
    """Deux instantanés descriptifs, sans classement ni inférence de progression."""
    personnes = ([beneficiaire] if beneficiaire else list(accompagnement.beneficiaires.all()))
    situations = list(SituationSociale.objects.filter(
        accompagnement=accompagnement, debut__lte=date_finale,
        beneficiaire__in=personnes).order_by('debut'))

    def valeur(personne, dimension, date):
        for situation in reversed(situations):
            if (situation.beneficiaire_id == personne.pk and situation.dimension == dimension
                    and situation.debut <= date and (situation.fin is None or date < situation.fin)):
                return situation.libelle_valeur
        return 'Non renseigné'

    return [dict(beneficiaire=personne, dimension=libelle,
                 initial=valeur(personne, code, date_initiale),
                 final=valeur(personne, code, date_finale))
            for personne in personnes for code, libelle in SituationSociale.DIMENSIONS]
