"""Lecture du dossier : sélection bornée à l'accompagnement et filtrée par droits."""
from urllib.parse import urlencode
from django.urls import reverse
from .retour_service import url_jour
from django.db.models import Prefetch
from django.utils import timezone
from .models import Sejour, Affectation, Absence
from . import dossier


def choisir(lignes, valeur):
    return next((ligne for ligne in lignes if str(ligne.pk) == valeur), lignes[0] if lignes else None)


def contexte(request, a):
    droits = request.user
    anciennes = dossier.lire(request, a).get('dossier_valeurs', {})
    lecture_h = droits.has_perms(['personnes.view_accordhebergement', 'personnes.view_sejour'])
    lecture_r = droits.has_perms(['personnes.view_accordrepas', 'personnes.view_repasdistribue'])
    sejours, accords_h, accords_r = [], [], []
    lieux = droits.has_perms(['personnes.view_affectation', 'personnes.view_lieuhebergement'])
    if lecture_h:
        accords_h = list(a.accords_hebergement.select_related('annule_par').prefetch_related('beneficiaires').order_by('-debut', 'pk'))
        qs = Sejour.objects.filter(accord__accompagnement=a).select_related('accord').prefetch_related('beneficiaires')
        if lieux:
            qs = qs.prefetch_related(Prefetch('affectations', queryset=Affectation.objects.select_related('lieu').order_by('-debut', '-pk'), to_attr='lieux_dossier'))
        if droits.has_perm('personnes.view_absence'):
            qs = qs.prefetch_related(Prefetch('absences', queryset=Absence.objects.order_by('-debut', '-pk'), to_attr='absences_dossier'))
        sejours = list(qs)
        sejours.sort(key=lambda s: (s.fin is not None, -s.debut.toordinal(), str(s.pk)))
        for s in sejours:
            s.lieu_ouvert = next((x for x in getattr(s, 'lieux_dossier', []) if x.fin is None), None)
            s.absence_ouverte = next((x for x in getattr(s, 'absences_dossier', []) if x.fin is None), None)
        avec_sejour = {s.accord_id for s in sejours}
        accords_h = [accord for accord in accords_h if accord.pk not in avec_sejour]
    if lecture_r:
        accords_r = list(a.accords_repas.select_related('annule_par').prefetch_related('beneficiaires').order_by('-debut', 'pk'))
    accords_r.sort(key=lambda accord: (accord.annule_le is not None, -accord.debut.toordinal(), str(accord.pk)))
    selection_h = choisir(sejours, request.GET.get('sejour', anciennes.get('sejour', '')))
    selection_r = choisir(accords_r, request.GET.get('repas', anciennes.get('repas', '')))
    navigation = dossier.creer(request, a, selection_h, selection_r)
    valeurs = navigation['dossier_valeurs']
    origine = url_jour(valeurs['date_service']) if valeurs['origine'] == 'jour' else reverse('suivi:liste') + '?' + urlencode({'q': valeurs['recherche'], 'page': valeurs['page']})
    return {**navigation, 'retour_origine': origine, 'accompagnement': a,
            'aujourdhui': timezone.localdate(), 'lecture_hebergement': lecture_h, 'lecture_repas': lecture_r,
            'lecture_lieux': lieux, 'sejours_dossier': sejours, 'accords_sans_sejour': accords_h,
            'accords_repas': accords_r,
            'selection_sejour': selection_h, 'selection_repas': selection_r,
            'informations': a.informations.select_related('auteur') if droits.has_perm('personnes.view_informationsaccompagnement') else []}
