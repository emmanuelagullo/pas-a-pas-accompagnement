from acteurs.contexte import service_metier
"""Présentation commune des faits existants ; aucune nouvelle définition métier.

Les lectures sont regroupées par modèle, puis réparties par personne. Les
formulaires et les journaux ne sont chargés qu'à la demande.
"""
from collections import defaultdict
from datetime import timedelta
from urllib.parse import urlencode

from django import forms
from django.db.models import Q, F, Window
from django.db.models.functions import RowNumber
from django.http import Http404
from django.urls import reverse
from django.utils import timezone

from . import models as m, famille, coordonnees, complements_identite
from . import dossier_complet as complet, relations_personnelles, parcours
from .presentation_dossier_complet import lignes


def selection(request, prise, valeurs=None):
    valeurs = valeurs or {}
    vue = request.GET.get('vue_sociale') or valeurs.get('vue_sociale') or ('entree' if prise else 'today')
    if vue not in ('entree', 'today', 'fin', 'date') or vue in ('entree', 'fin') and not prise:
        raise Http404('Vue de situation inconnue.')
    if vue == 'fin' and not prise.fin:
        raise Http404('Cette prise en charge n’est pas terminée.')
    jour = timezone.localdate()
    if vue == 'entree':
        jour = prise.debut
    elif vue == 'fin':
        jour = prise.fin - timedelta(days=1)
    elif vue == 'date':
        try:
            jour = forms.DateField().clean(request.GET.get('date_sociale', valeurs.get('date_sociale')))
        except forms.ValidationError:
            raise Http404('Choisissez une date valide.')
    if jour > timezone.localdate():
        raise Http404('La situation ne peut pas être consultée dans le futur.')
    return vue, jour


def presentation(request, personnes, jour, objet, nature, prise, params):
    acteur = request.user
    personnes = list(personnes)
    from . import retraits_chronologiques
    precedents = {}
    # Une seule déclaration précédente par personne et série suffit pour
    # distinguer les champs repris de ceux modifiés à la date sélectionnée.
    for model in dict.fromkeys(s.modele for s in retraits_chronologiques.series().values()
                               if acteur.has_perms(retraits_chronologiques.droits(s)[:3])):
        partition = [F('personne_id')]
        if model is m.SituationPersonnelle:
            partition.append(F('dimension'))
        qs = model.objects.filter(personne__in=personnes, debut__lt=jour).annotate(
            _rang=Window(expression=RowNumber(), partition_by=partition,
                         order_by=[F('debut').desc(), F('pk').desc()])).filter(_rang=1)
        for x in qs:
            precedents[(model, x.personne_id, getattr(x, 'dimension', ''))] = x
    resultats = {p.pk: {'personne': p, 'groupes': [], 'ancre': 'social-' + str(p.pk)} for p in personnes}
    query = {**params, 'saisie_sociale': '1', 'date': jour.isoformat(), 'depuis_nature': nature,
             'depuis_pk': str(objet.pk), 'depuis_prise': str(prise.pk) if prise else ''}
    if prise:
        query['contexte_prise'] = str(prise.pk)

    def url(nom, *args):
        return reverse(nom, args=args) + '?' + urlencode({**query, **({'portee': '1'} if nom.endswith('corriger') else {})})

    if nature == 'menage':
        for p in personnes:
            resultats[p.pk]['url_dossier'] = reverse('dossiers:detail', args=['personne', p.pk]) + '?' + urlencode({
                **params, 'origine_menage': str(objet.pk), 'origine_sejour': params.get('sejour', ''),
                'origine_repas': params.get('repas', ''),
                'vue_sociale': 'date' if params.get('vue_sociale') in ('entree', 'fin') else params.get('vue_sociale', 'today')})

    def groupe(p, code, titre, facts, model, champs, ajouter='', historique='', changer=None, corriger=None, multiple=False):
        fiches = []
        for x in facts:
            contenu = lignes(model, x, champs)
            if isinstance(x, m.SituationPersonnelle):
                contenu = [('Situation', x.libelle_valeur)]
            contenu = [(label, ' ; '.join(str(v) for v in valeur) if isinstance(valeur, list)
                        else 'Oui' if valeur is True else 'Non' if valeur is False else valeur)
                       for label, valeur in contenu]
            precedent = precedents.get((model, p.pk, getattr(x, 'dimension', '')))
            if precedent and precedent.fin != getattr(x, 'debut', None):
                precedent = None
            champs_affiches = []
            for c, (label, valeur) in zip(champs, contenu):
                herite = getattr(x, 'debut', jour) < jour
                repris = bool(getattr(x, 'debut', None) == jour and precedent
                              and getattr(x, c) == getattr(precedent, c))
                origine = precedent if repris else x
                vide = getattr(x, c) in (None, '', [])
                champs_affiches.append({'label': label, 'valeur': valeur, 'herite': herite or repris,
                    'vide': vide, 'origine': getattr(origine, 'debut', None), 'repris': repris})
            retrait = code in retraits_chronologiques.series() and getattr(x, 'debut', None) == jour
            fiches.append({'fait': x, 'lignes': contenu, 'champs': champs_affiches,
                'retirer': url('dossiers:condition_retirer', p.pk, code, x.pk)
                    if retrait and acteur.has_perms(retraits_chronologiques.droits(retraits_chronologiques.configuration(code))) else '',
                'resume': [c for c in champs_affiches if not c['vide']],
                'herite': getattr(x, 'debut', jour) < jour,
                'changer': changer(x) if changer and getattr(x, 'debut', jour) < jour else '',
                'corriger': corriger(x) if corriger else ''})
        resultats[p.pk]['groupes'].append({'code': code, 'titre': titre, 'fiches': fiches,
            'ajouter': ajouter if multiple or not fiches else '', 'historique': historique,
            'ancre': 'social-' + str(p.pk) + '-' + code,
            'vides': [model._meta.get_field(c).verbose_name for c in champs] if not fiches else []})

    # Identité principale : elle n'a pas de période de validité, contrairement
    # aux compléments déclarés. Ne pas lui inventer un héritage à date.
    for p in personnes:
        groupe(p, 'identite', 'Identité', [p], m.Personne,
               ('designation', 'prenom', 'date_naissance', 'annee_naissance', 'precision_naissance'),
               historique=url('personnes:detail', p.pk),
               corriger=(lambda x: url('personnes:corriger_identite', x.pk))
               if acteur.has_perms(('personnes.change_personne', 'personnes.view_revisionidentite')) else None)

    series = [
        ('complements', 'Identité déclarée', m.ComplementIdentite, complements_identite,
         'complements_identite_nouveaux', 'complements_identite_corriger', 'complements_identite'),
        ('famille', 'Situation familiale déclarée', m.DeclarationFamiliale, famille,
         'famille_nouvelle', 'famille_corriger', 'famille'),
        ('coordonnees', 'Coordonnées', m.CoordonneesPersonnelles, coordonnees,
         'coordonnees_nouvelles', 'coordonnees_corriger', 'coordonnees')]
    for code, titre, model, service, nouveau, corrige, histoire in series:
        if not acteur.has_perms(service.DROITS_LECTURE):
            continue
        faits = {x.personne_id: x for x in service.a_date(personnes, jour)}
        for p in personnes:
            peut = acteur.has_perm('personnes.add_' + model._meta.model_name)
            groupe(p, code, titre, [faits[p.pk]] if p.pk in faits else [], model, service.CHAMPS,
                   ajouter=url('dossiers:' + nouveau, p.pk) if peut else '',
                   historique=url('dossiers:' + histoire, p.pk),
                   changer=(lambda x, n=nouveau, p=p: url('dossiers:' + n, p.pk)) if peut else None,
                   corriger=(lambda x, n=corrige, p=p: url('dossiers:' + n, p.pk, x.pk))
                   if peut and acteur.has_perm('personnes.change_' + model._meta.model_name) else None)

    if acteur.has_perms(('personnes.view_situationpersonnelle', 'personnes.view_revisionsituationpersonnelle')):
        faits = {(x.personne_id, x.dimension): x for x in m.SituationPersonnelle.objects.filter(
            personne__in=personnes, debut__lte=jour).filter(Q(fin__isnull=True) | Q(fin__gt=jour))}
        for p in personnes:
            for dimension, titre in m.SituationSociale.DIMENSIONS:
                x = faits.get((p.pk, dimension))
                peut = acteur.has_perm('personnes.add_situationpersonnelle')
                groupe(p, 'ressources-globales' if dimension == 'ressources' else dimension, titre, [x] if x else [], m.SituationPersonnelle, ('valeur',),
                    ajouter=url('dossiers:social_nouveau', p.pk, dimension) if peut else '',
                    historique=url('dossiers:social', p.pk),
                    changer=(lambda x, p=p, d=dimension: url('dossiers:social_nouveau', p.pk, d)) if peut else None,
                    corriger=(lambda x, p=p, d=dimension: url('dossiers:social_corriger', p.pk, d, x.pk))
                    if peut and acteur.has_perm('personnes.change_situationpersonnelle') else None)
                # La valeur détaillée reste prioritaire dans la synthèse bd6 ;
                # ici la déclaration globale est explicitement nommée.
                if dimension == 'ressources':
                    resultats[p.pk]['groupes'][-1]['titre'] = 'Ressources — déclaration globale conservée'

    if acteur.has_perms(complet.ADMIN_LECTURE):
        faits = {x.personne_id: x for x in complet.administration_a_date(personnes, jour)}
        for p in personnes:
            peut = acteur.has_perm('personnes.add_situationadministrative')
            groupe(p, 'administration', 'Administration et droits', [faits[p.pk]] if p.pk in faits else [],
                m.SituationAdministrative, complet.ADMIN_CHAMPS,
                ajouter=url('dossiers:administration_nouvelle', p.pk) if peut else '',
                historique=url('dossiers:fiche_a', p.pk, 'droits'),
                changer=(lambda x, p=p: url('dossiers:administration_nouvelle', p.pk)) if peut else None,
                corriger=(lambda x, p=p: url('dossiers:administration_corriger', p.pk, x.pk))
                if peut and acteur.has_perm('personnes.change_situationadministrative') else None)

    for code, r in complet.RUBRIQUES.items():
        if not acteur.has_perms(complet.droits_lecture(code)):
            continue
        par_personne = defaultdict(list)
        for x in complet.a_date(code, personnes, jour):
            par_personne[x.personne_id].append(x)
        for p in personnes:
            peut = acteur.has_perm('personnes.add_' + r.modele._meta.model_name)
            mod = peut and acteur.has_perm('personnes.change_' + r.modele._meta.model_name)
            groupe(p, code, r.titre, par_personne[p.pk], r.modele, r.champs,
                ajouter=url('dossiers:fait_a_nouveau', p.pk, code) if peut else '',
                historique=url('dossiers:fiche_a', p.pk, r.groupe),
                changer=(lambda x, p=p, c=code: url('dossiers:fait_a_changer', p.pk, c, x.pk) if x.fin is None else '') if mod else None,
                corriger=(lambda x, p=p, c=code: url('dossiers:fait_a_corriger', p.pk, c, x.pk)) if mod else None, multiple=True)

    if acteur.has_perms(relations_personnelles.DROITS_LECTURE):
        par_personne = defaultdict(list)
        faits = m.RelationPersonnelle.objects.filter(
            Q(personne_a__in=personnes) | Q(personne_b__in=personnes), debut__lte=jour,
            annule_le__isnull=True).filter(Q(fin__isnull=True) | Q(fin__gt=jour)).select_related('personne_a', 'personne_b')
        for x in faits:
            for pk in (x.personne_a_id, x.personne_b_id):
                par_personne[pk].append(x)
        for p in personnes:
            peut = acteur.has_perm('personnes.add_relationpersonnelle')
            groupe(p, 'relations', 'Liens personnels déclarés', par_personne[p.pk], m.RelationPersonnelle,
                ('personne_a', 'nature', 'personne_b', 'precision'),
                ajouter=url('dossiers:relation_nouvelle', p.pk) if peut else '',
                historique=url('dossiers:relations_personnelles', p.pk),
                changer=(lambda x, p=p: url('dossiers:relation_changer', p.pk, x.pk) if x.fin is None else '')
                if peut and acteur.has_perm('personnes.change_relationpersonnelle') else None,
                corriger=(lambda x, p=p: url('dossiers:relation_corriger', p.pk, x.pk))
                if peut and acteur.has_perm('personnes.change_relationpersonnelle') else None, multiple=True)

    projets = []
    for code, r in parcours.RUBRIQUES.items():
        if not acteur.has_perms(parcours.droits(code)):
            continue
        qs = parcours.a_date(code, jour)
        if nature == 'personne':
            qs = qs.filter(Q(element__personne=objet) | Q(element__beneficiaires=objet)).distinct()
        else:
            qs = qs.filter(element__menage=objet)
        if not acteur.has_perm('personnes.view_menage'):
            qs = qs.filter(element__menage__isnull=True)
        # Même cible qu'auparavant : le dossier garde son histoire au-delà de
        # la prise ; le rattachement est affiché, sans recopie ni déduction.
        items = []
        for x in qs.select_related('element__personne', 'element__menage').prefetch_related('element__beneficiaires'):
            valeurs = lignes(r.version, x, r.champs)
            renseignees = [ligne for champ, ligne in zip(r.champs, valeurs) if getattr(x, champ) not in (None, '', [])]
            integrale = params.get('presentation_sociale') != 'synthese'
            items.append({'fait': x, 'lignes': valeurs, 'affichees': valeurs if integrale else renseignees,
                'beneficiaires': list(x.element.beneficiaires.all()),
                'url': url('dossiers:parcours_element', code, x.element_id),
                'changer': url('dossiers:parcours_changer', code, x.element_id)
                    if x.debut < jour and acteur.has_perm('personnes.change_' + r.racine._meta.model_name) else '',
                'corriger': url('dossiers:parcours_corriger', code, x.element_id, x.pk)
                    if acteur.has_perm('personnes.change_' + r.racine._meta.model_name) else '',
                'herite': x.debut < jour})
        projets.append({'ancre': 'projet-' + code, 'titre': r.titre, 'items': items,
            'nouveau': url('dossiers:parcours_nouveau', nature, objet.pk, code)
                if acteur.has_perm('personnes.add_' + r.racine._meta.model_name) else '',
            'url': url('dossiers:parcours', nature, objet.pk) + '&rubrique=' + code})
    return list(resultats.values()), projets


@service_metier
def documents(acteur, cible):
    """Métadonnées des documents ; aucun chargement des fichiers binaires."""
    from django.db.models import OuterRef, Subquery
    from . import pieces_dossier
    type_cible = pieces_dossier.nature(cible)
    if not acteur.has_perms(('personnes.view_' + type_cible,
                            'personnes.view_piecedossier', 'personnes.view_versionpiecedossier')):
        return []
    versions = m.VersionPieceDossier.objects.filter(piece_id=OuterRef('pk')).order_by('-version')
    return list(m.PieceDossier.objects.filter(**{type_cible: cible}, annule_le__isnull=True).annotate(
        titre_courant=Subquery(versions.values('titre')[:1].selection()),
        version_courante=Subquery(versions.values('pk')[:1].selection())).order_by('-enregistre_le'))


@service_metier
def contextes(acteur, personnes, objet=None):
    """Libellés récents des journaux autorisés, sans nouvel objet d'entretien.

    Le contexte décrit l’opération ; il ne réécrit ni motif ancien ni source. Les propositions
    sont limitées au dossier et aux rubriques que l'acteur peut consulter.
    """
    trouves = []
    series = [
        (famille.DROITS_LECTURE, m.RevisionDeclarationFamiliale, 'personne'),
        (coordonnees.DROITS_LECTURE, m.RevisionCoordonneesPersonnelles, 'personne'),
        (complements_identite.DROITS_LECTURE, m.RevisionComplementIdentite, 'personne'),
        (complet.ADMIN_LECTURE, m.RevisionSituationAdministrative, 'personne'),
        (('personnes.view_situationpersonnelle', 'personnes.view_revisionsituationpersonnelle'),
         m.RevisionSituationPersonnelle, 'personne')]
    series += [(complet.droits_lecture(code), r.journal, 'fait__personne')
               for code, r in complet.RUBRIQUES.items()]
    for droits, journal, lien in series:
        if acteur.has_perms(droits):
            trouves.extend(journal.objects.filter(**{lien + '__in': personnes}).exclude(contexte_saisie='')
                           .order_by('-enregistre_le').values_list('enregistre_le', 'contexte_saisie')[:10])
    if acteur.has_perms(('personnes.view_personne', 'personnes.view_revisionidentite')):
        trouves.extend(m.RevisionIdentite.objects.filter(personne__in=personnes).exclude(contexte_saisie='').values_list('enregistre_le', 'contexte_saisie').order_by('-enregistre_le')[:10])
    if acteur.has_perms(relations_personnelles.DROITS_LECTURE):
        trouves.extend(m.RevisionRelationPersonnelle.objects.filter(Q(relation__personne_a__in=personnes) | Q(relation__personne_b__in=personnes)).exclude(contexte_saisie='').values_list('enregistre_le', 'contexte_saisie').order_by('-enregistre_le')[:10])
    for code, r in parcours.RUBRIQUES.items():
        if acteur.has_perms(parcours.droits(code)):
            q = Q(element__menage=objet) if isinstance(objet, m.Menage) else Q(element__personne__in=personnes) | Q(element__beneficiaires__in=personnes)
            trouves.extend(r.journal.objects.filter(q).exclude(contexte_saisie='').distinct().values_list('enregistre_le', 'contexte_saisie').order_by('-enregistre_le')[:10])
    if acteur.has_perms(('personnes.view_informationsaccompagnement', 'personnes.view_accompagnement')):
        q = Q(accompagnement__menage=objet) if isinstance(objet, m.Menage) else Q(accompagnement__beneficiaires__in=personnes)
        trouves.extend(m.InformationsAccompagnement.objects.filter(q).exclude(contexte_saisie='').distinct().values_list('enregistre_le', 'contexte_saisie').order_by('-enregistre_le')[:10])
    resultats = []
    for _, motif in sorted(trouves, reverse=True):
        if motif not in resultats:
            resultats.append(motif)
        if len(resultats) == 30:
            break
    return resultats
