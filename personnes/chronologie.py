"""Projection de consultation : aucune date ni réalisation n'est déduite."""
from datetime import timedelta
from urllib.parse import urlencode

from django import forms
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from acteurs.contexte import service_metier
from . import models as m, dossier, aides

CLES = ('chrono_debut', 'chrono_fin', 'chrono_type', 'chrono_page', 'chrono_prise', 'chrono_ancre', 'chrono_origine')
TYPES = [('', 'Tout'), ('prise', 'Prises en charge'), ('hebergement', 'Hébergement'),
         ('lieu', 'Lieux'), ('absence', 'Absences'), ('repas', 'Repas accordés'), ('aide', 'Transports et autres aides')]


class Filtres(forms.Form):
    chrono_debut = forms.DateField(label='Du (inclus)', widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
    chrono_fin = forms.DateField(label='Au (exclu)', widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
    chrono_type = forms.ChoiceField(label='Afficher', choices=TYPES, required=False)

    def clean(self):
        d = super().clean()
        if d.get('chrono_debut') and d.get('chrono_fin'):
            jours = (d['chrono_fin'] - d['chrono_debut']).days
            if not 0 < jours <= 1096:
                self.add_error('chrono_fin', 'Choisissez une fenêtre de 1 jour à 3 ans.')
        return d


def lien(nature, pk, params):
    return reverse('dossiers:chronologie', args=[nature, pk]) + '?' + urlencode(params)


def recouvre(debut, fin):
    return Q(debut__lt=fin) & (Q(fin__isnull=True) | Q(fin__gt=debut))


def geometrie(debut, fin, gauche, droite):
    """Clippage uniquement ; une borne ouverte n'est pas une fin effective."""
    if debut is None or debut >= droite or (fin is not None and fin <= gauche):
        return None
    total = (droite - gauche).days
    x = max(debut, gauche)
    y = min(fin or droite, droite)
    return {'gauche': f'{100 * (x - gauche).days / total:.4f}',
            'largeur': f'{100 * (y - x).days / total:.4f}',
            'avant': debut < gauche, 'apres': fin is None or fin > droite}


@service_metier
def construire(acteur, objet, nature, params, debut, fin):
    """Chaque modèle est sélectionné par son gestionnaire contrôlé avant agrégation.

    Les FK jointes ne servent pas à contourner la visibilité des parents.
    Les accords et réalisations restent deux lignes distinctes.
    """
    if not acteur.has_perms(dossier.DROITS):
        return []
    prises = objet.accompagnements.prefetch_related('beneficiaires')
    if params.get('chrono_prise'):
        prises = prises.filter(pk=params['chrono_prise'])
    prises = {a.pk: a for a in prises}
    lignes = []

    def ajouter(obj, groupe, libelle, url, a, etat='', debut_obj=None, fin_obj=None):
        borne_debut = debut_obj or obj.debut
        borne_fin = fin_obj if fin_obj is not None else obj.fin
        prevu = groupe in ('repas', 'aide') or libelle in ('Hébergement autorisé', 'Prévision de la prise en charge')
        fin_dessin = borne_fin
        if borne_fin is None and not prevu:
            fin_dessin = timezone.localdate() + timedelta(days=1)
            if borne_debut >= fin_dessin:
                return
        geo = geometrie(borne_debut, fin_dessin, debut, fin)
        if geo is None:
            return
        cle = f'{obj._meta.model_name}-{obj.pk}' + ('-prevision' if libelle == 'Prévision de la prise en charge' else '')
        porteurs = sejours[obj.sejour_id] if groupe in ('lieu', 'absence') else obj
        portee = str(objet) if nature == 'personne' else ' ; '.join(str(p) for p in porteurs.beneficiaires.all())
        lignes.append({'id': cle, 'groupe': groupe, 'libelle': libelle,
                       'debut': borne_debut, 'fin': borne_fin, 'etat': etat,
                       'url': url, 'prise': a, 'parent_debut': a.debut, 'prevu': prevu, 'portee': portee,
                       'annule': bool(getattr(obj, 'annule_le', None)), **geo})

    for a in prises.values():
        url = reverse('dossiers:prise', args=[nature, objet.pk, a.pk])
        ajouter(a, 'prise', 'Prise en charge', url, a, 'Clôture effective' if a.fin else 'Clôture non enregistrée')
        if a.fin_prevue:
            # L'autorisation prévue n'efface pas une clôture ni ne ferme une période ouverte.
            ajouter(a, 'prise', 'Prévision de la prise en charge', url, a,
                    'Fin prévue dépassée' if not a.fin and a.fin_prevue <= timezone.localdate() else 'Fin prévue', fin_obj=a.fin_prevue)

    def beneficiaire(qs):
        return qs.filter(beneficiaires=objet).distinct() if nature == 'personne' else qs

    if acteur.has_perms(['personnes.view_accordhebergement', 'personnes.view_sejour']):
        accords = beneficiaire(m.AccordHebergement.objects.filter(accompagnement_id__in=prises).prefetch_related('beneficiaires'))
        accords = {x.pk: x for x in accords}
        for x in accords.values():
            ajouter(x, 'hebergement', 'Hébergement autorisé', reverse('suivi:accord_hebergement', args=[x.pk]), prises[x.accompagnement_id], 'Annulé' if x.annule_le else 'Autorisation, sans preuve d’arrivée')
        sejours = beneficiaire(m.Sejour.objects.filter(accord_id__in=accords).filter(recouvre(debut, fin)))
        if not acteur.has_perm('personnes.view_annulationarrivee'):
            sejours = sejours.non_annules()
        sejours = {s.pk: s for s in sejours.prefetch_related('beneficiaires')}
        for s in sejours.values():
            ajouter(s, 'hebergement', 'Continuation individuelle' if s.origine_collective_id else 'Séjour enregistré',
                    reverse('suivi:accord_hebergement', args=[s.accord_id]) + '#sejour-' + str(s.pk),
                    prises[accords[s.accord_id].accompagnement_id], 'Arrivée annulée' if s.annule_le else 'Sortie effective' if s.fin else 'Sortie non enregistrée ; présence non attestée')
        actifs = {k: s for k, s in sejours.items() if not s.annule_le}
        if acteur.has_perms(['personnes.view_affectation', 'personnes.view_lieuhebergement']):
            affectations = list(m.Affectation.objects.filter(sejour_id__in=actifs).filter(recouvre(debut, fin)))
            lieux = {x.pk: x.libelle for x in m.LieuHebergement.objects.filter(pk__in={a.lieu_id for a in affectations})}
            for x in affectations:
                if x.lieu_id not in lieux:
                    continue
                s = actifs[x.sejour_id]
                ajouter(x, 'lieu', lieux[x.lieu_id], reverse('suivi:accord_hebergement', args=[s.accord_id]) + '#affectation-' + str(x.pk), prises[accords[s.accord_id].accompagnement_id], 'Affectation enregistrée')
        if acteur.has_perm('personnes.view_absence'):
            for x in m.Absence.objects.filter(sejour_id__in=actifs).filter(recouvre(debut, fin)):
                s = actifs[x.sejour_id]
                ajouter(x, 'absence', 'Absence enregistrée', reverse('suivi:accord_hebergement', args=[s.accord_id]) + '#absence-' + str(x.pk), prises[accords[s.accord_id].accompagnement_id], 'Ne clôt pas le séjour')
    if acteur.has_perms(['personnes.view_accordrepas', 'personnes.view_repasdistribue']):
        for x in beneficiaire(m.AccordRepas.objects.filter(accompagnement_id__in=prises).filter(recouvre(debut, fin)).prefetch_related('beneficiaires')):
            ajouter(x, 'repas', x.get_service_display(), reverse('suivi:accord_repas', args=[x.pk]), prises[x.accompagnement_id],
                    'Annulé' if x.annule_le else 'Repas accordés selon les jours autorisés ; distributions distinctes')
    if acteur.has_perms(aides.LECTURE):
        for x in beneficiaire(m.AccordAide.objects.filter(accompagnement_id__in=prises).filter(recouvre(debut, fin)).prefetch_related('beneficiaires')):
            ajouter(x, 'aide', x.libelle, reverse('dossiers:aide', args=[x.pk]), prises[x.accompagnement_id],
                    'Annulé' if x.annule_le else 'Autorisation ; remises et usages distincts')
    syntheses = {}
    for ligne in lignes:
        if ligne['groupe'] != 'prise' and not ligne['annule']:
            syntheses.setdefault(ligne['prise'].pk, set()).add(ligne['libelle'])
    for ligne in lignes:
        if ligne['libelle'] == 'Prise en charge':
            ligne['synthese'] = ' · '.join(sorted(syntheses.get(ligne['prise'].pk, set()))) or 'Aucune prestation consultable dans cette fenêtre'
    type_choisi = params.get('chrono_type')
    if type_choisi:
        lignes = [x for x in lignes if x['groupe'] == type_choisi]
    return sorted(lignes, key=lambda x: (x['debut'], x['groupe'], x['id'], x['libelle']))
