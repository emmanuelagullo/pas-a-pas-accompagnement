"""Lecture transversale : déclarations personnelles et faits de prises distincts.

Aucune écriture ni prolongation implicite de période. Les comparaisons réutilisent
la restitution du dossier ; la chronologie garde date d'effet et enregistrement.
"""
from django.urls import reverse
from . import bd6, dossier, dossier_complet
from .models import SituationSociale, SituationPersonnelle, EvenementSocial, BilanSocial, RepasDistribue, Sejour


def construire(accompagnement, acteur, beneficiaire=None, debut=None, fin=None, *,
                prises=None, personnes=None, dans_dossier=None):
    """Bornes incluses sur les faits, sans inventer un fait à l'ouverture du filtre.

    ``dans_dossier`` borne les faits personnels au contexte daté du ménage ;
    les bénéficiaires d'une prestation restent toujours ceux du fait lui-même.
    """
    prises = list(prises if prises is not None else [accompagnement])
    personnes = list(personnes if personnes is not None else accompagnement.beneficiaires.all())
    if beneficiaire:
        personnes = [p for p in personnes if p.pk == beneficiaire.pk]
    ids = {p.pk for p in personnes}
    lignes = []

    def ajouter(date, enregistre, nature, texte, personne=None, document=None,
                ancien=False, url='', personnel=False, terme=None, prise=None):
        if (debut and date < debut) or (fin and date > fin):
            return
        if personne and personne.pk not in ids or beneficiaire and personne != beneficiaire:
            return
        if personnel and dans_dossier and not dans_dossier(personne, date):
            return
        lignes.append(dict(date=date, enregistre=enregistre, nature=nature, texte=texte,
                           texte_document=document, beneficiaire=personne, ancien=ancien,
                           url=url, terme=terme, prise=prise))

    if acteur.has_perms(['personnes.view_personne', 'personnes.view_situationpersonnelle',
                         'personnes.view_revisionsituationpersonnelle']):
        for s in SituationPersonnelle.objects.filter(personne__in=personnes).select_related('personne'):
            ajouter(s.debut, s.enregistre_le, 'Déclaration personnelle',
                    f'{s.get_dimension_display()} : {s.libelle_valeur} (source : {s.source})',
                    s.personne, url=reverse('dossiers:social', args=[s.personne_id]),
                    personnel=True, terme=s.fin)
    # Les détails économiques ne deviennent jamais des prestations ni des paiements.
    for code in ('ressources', 'dettes'):
        if not acteur.has_perms(dossier_complet.droits_lecture(code)):
            continue
        for s in dossier_complet.faits(code, personnes).filter(annule_le__isnull=True):
            titre = s.get_etat_display() if s.etat != 'detail' else (
                s.libelle if code == 'ressources' else 'Total déclaré' if s.nature == 'total' else s.creancier)
            montant = '' if s.etat != 'detail' else (
                ' · montant inconnu' if s.montant is None else f' · {s.montant} {s.devise}')
            if code == 'ressources' and s.etat == 'detail':
                montant += f' · {s.get_periodicite_display()}'
            ajouter(s.debut, s.enregistre_le, dossier_complet.RUBRIQUES[code].titre,
                    f'{titre}{montant} (source : {s.source})', s.personne,
                    url=reverse('dossiers:fiche_a', args=[s.personne_id, 'economique']),
                    personnel=True, terme=s.fin)
    if not acteur.has_perms(dossier.DROITS):
        return sorted(lignes, key=ordre)
    if acteur.has_perm('personnes.view_situationsociale'):
        for s in SituationSociale.objects.filter(accompagnement__in=prises).select_related('beneficiaire', 'accompagnement'):
            ajouter(s.debut, s.cree_le, 'Ancienne situation de suivi',
                    f'{s.get_dimension_display()} : {s.libelle_valeur} (source : {s.source} ; prise en charge du {s.accompagnement.debut:%d/%m/%Y})',
                    s.beneficiaire, ancien=True, url=reverse('suivi:social', args=[s.accompagnement_id]), terme=s.fin, prise=s.accompagnement)
    if acteur.has_perm('personnes.view_evenementsocial'):
        for e in EvenementSocial.objects.filter(accompagnement__in=prises).select_related('beneficiaire', 'accompagnement'):
            ajouter(e.date_effet, e.cree_le, 'Événement antérieur' if e.date_effet < e.accompagnement.debut else 'Événement',
                    e.texte + f' (source : {e.source})', e.beneficiaire,
                    url=reverse('suivi:social', args=[e.accompagnement_id]) if acteur.has_perm('personnes.view_situationsociale') else '', prise=e.accompagnement)
    if acteur.has_perm('personnes.view_bilansocial') and not beneficiaire:
        for b in BilanSocial.objects.filter(accompagnement__in=prises).select_related('accompagnement'):
            ajouter(b.date_effet, b.cree_le, 'Bilan du ménage', b.texte, document=b.texte_document,
                    url=reverse('suivi:social', args=[b.accompagnement_id]) if acteur.has_perm('personnes.view_situationsociale') else '', prise=b.accompagnement)
    if acteur.has_perms(['personnes.view_accordrepas', 'personnes.view_repasdistribue']):
        for r in RepasDistribue.objects.filter(accord__accompagnement__in=prises).select_related('beneficiaire', 'accord'):
            statut = 'annulé' if r.annule_le else 'réalisé'
            ajouter(r.date, r.cree_le, 'Repas', f'{r.quantite} × {r.accord.get_service_display()} ({statut})', r.beneficiaire)
    if acteur.has_perms(['personnes.view_accordhebergement', 'personnes.view_sejour']):
        for s in Sejour.objects.non_annules().filter(accord__accompagnement__in=prises).prefetch_related('beneficiaires'):
            for p in s.beneficiaires.all():
                ajouter(s.debut, s.cree_le, 'Continuation individuelle' if s.origine_collective_id else 'Admission',
                        'Début du fragment individuel, sans nouvelle admission' if s.origine_collective_id else 'Entrée effective en hébergement', p)
                if s.fin:
                    # Une individualisation termine un fragment, pas l'épisode d'accueil.
                    continuation = hasattr(s, 'individualisation')
                    ajouter(s.fin, s.cree_le, 'Fin du fragment collectif' if continuation else 'Sortie',
                            'Individualisation du séjour, sans sortie déduite' if continuation else 'Fin du séjour (date exclue)', p)
    return sorted(lignes, key=ordre)


def ordre(ligne):
    return ligne['date'], ligne['enregistre'], ligne['nature'], str(ligne['beneficiaire'])


def comparer(acteur, personnes, date_initiale, date_finale, *, dans_dossier=None):
    """Même lecture qu'au dossier/à l'entrée, jamais un classement de progression."""
    personnes = list(personnes)
    def lecture(jour):
        selection = [p for p in personnes if not dans_dossier or dans_dossier(p, jour)]
        return {e['personne'].pk: e for e in bd6.etat(acteur, selection, jour)}
    initial, final = lecture(date_initiale), lecture(date_finale)
    resultat = []
    for p in personnes:
        for i, (_, libelle) in enumerate(SituationSociale.DIMENSIONS):
            a = initial.get(p.pk, {}).get('lignes', [])
            b = final.get(p.pk, {}).get('lignes', [])
            resultat.append(dict(beneficiaire=p, dimension=libelle,
                initial_lecture=a[i] if a else None, final_lecture=b[i] if b else None))
        # Montants comparables seulement ; dettes totales et détails restent séparés.
        for code in ('ressources', 'dettes'):
            if acteur.has_perms(dossier_complet.droits_lecture(code)):
                def synthese(etat):
                    return next((d['texte'] for d in etat.get(p.pk, {}).get('dossier_a', []) if d['code'] == code), 'Hors du contexte daté du ménage')
                resultat.append(dict(beneficiaire=p, dimension=dossier_complet.RUBRIQUES[code].titre + ' détaillées',
                                      initial=synthese(initial), final=synthese(final)))
    return resultat
