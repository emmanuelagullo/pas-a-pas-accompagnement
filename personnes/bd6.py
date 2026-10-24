"""Prises en charge et histoire sociale personnelle, sans réécriture des anciens journaux."""
from . import textes_riches as tr
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from . import suivi, dossier
from .models import (Personne, Menage, Accompagnement, SituationSociale, SituationPersonnelle,
    RevisionSituationPersonnelle, EvolutionPriseEnCharge, CommentaireDossier, Appartenance, Partenaire, Intervenant)
from .verrous_metier import serialiser

SEL = 'bd6-etat-v1'


def revision(objet):
    return objet.revision if isinstance(objet, (Menage, Partenaire, Intervenant)) else objet.revision_sociale


def jeton(objet):
    objet.refresh_from_db()
    return signing.dumps([objet._meta.model_name, str(objet.pk), revision(objet)], salt=SEL)


def reserver(objet, attendu):
    """CAS avant lecture métier. Personne seule : ne jamais prendre ensuite un verrou ménage."""
    try:
        etat = signing.loads(attendu, salt=SEL, max_age=86400)
    except (signing.BadSignature, TypeError):
        raise ValidationError('État non vérifiable. Rechargez le formulaire.')
    if not isinstance(etat, list) or len(etat) != 3 or etat[:2] != [objet._meta.model_name, str(objet.pk)]:
        raise ValidationError('Ce formulaire ne concerne pas cette cible.')
    champ = 'revision' if isinstance(objet, (Menage, Partenaire, Intervenant)) else 'revision_sociale'
    if type(objet).objects.filter(pk=objet.pk, **{champ: etat[2]}).update(**{champ: F(champ) + 1}) != 1:
        raise ValidationError('La situation a changé. Rechargez avant de réessayer.')
    objet.refresh_from_db()


@serialiser('accompagnement')
@transaction.atomic
def prolonger(acteur, accompagnement, fin_prevue, motif, attendu):
    suivi.exiger(acteur, 'view_personne', 'view_menage', 'view_accompagnement', 'prolonger_accompagnement', 'view_evolutionpriseencharge')
    reserver(accompagnement, attendu)
    if accompagnement.fin:
        raise ValidationError('Cette prise en charge est close.')
    if not motif.strip() or len(motif) > 240:
        raise ValidationError('Indiquez le motif de cette prévision (240 caractères maximum).')
    if fin_prevue <= (accompagnement.fin_prevue or accompagnement.debut):
        raise ValidationError('La nouvelle fin prévue doit être postérieure à la précédente et au début.')
    ancienne = accompagnement.fin_prevue
    accompagnement.fin_prevue = fin_prevue
    accompagnement.full_clean()
    accompagnement.save(update_fields=['fin_prevue'])
    EvolutionPriseEnCharge.objects.create(accompagnement=accompagnement, ancienne_fin=ancienne,
        nouvelle_fin=fin_prevue, motif=motif, auteur=acteur)


@serialiser('accompagnement')
@transaction.atomic
def corriger_prevision(acteur, accompagnement, fin_prevue, motif, attendu):
    suivi.exiger(acteur, 'view_personne', 'view_menage', 'view_accompagnement',
        'corriger_prevision_accompagnement', 'view_evolutionpriseencharge')
    reserver(accompagnement, attendu)
    if accompagnement.fin:
        raise ValidationError('Cette prise est close. Sa prévision historique ne peut plus être modifiée ici.')
    if not motif.strip() or len(motif) > 240:
        raise ValidationError({'motif': 'Expliquez l’erreur de prévision (240 caractères maximum).'})
    if fin_prevue == accompagnement.fin_prevue:
        raise ValidationError({'fin_prevue': 'La prévision est inchangée.'})
    if fin_prevue is not None and fin_prevue <= accompagnement.debut:
        raise ValidationError({'fin_prevue': 'La fin prévue doit être postérieure au début.'})
    ancienne = accompagnement.fin_prevue
    accompagnement.fin_prevue = fin_prevue
    accompagnement.full_clean()
    accompagnement.save(update_fields=['fin_prevue'])
    EvolutionPriseEnCharge.objects.create(accompagnement=accompagnement, ancienne_fin=ancienne,
        nouvelle_fin=fin_prevue, action='correction', motif=motif.strip(), auteur=acteur)


@serialiser('accompagnement')
@transaction.atomic
def clore_prise(acteur, accompagnement, fin, attendu):
    suivi.exiger(acteur, 'view_personne', 'view_menage', 'view_accompagnement', 'change_accompagnement')
    reserver(accompagnement, attendu)
    suivi.clore(acteur, accompagnement, fin)


def photographie(personne, dimension):
    return [{'id': x.pk, 'debut': x.debut.isoformat(), 'fin': x.fin.isoformat() if x.fin else None,
             'valeur': x.valeur, 'source': x.source}
            for x in SituationPersonnelle.objects.filter(personne=personne, dimension=dimension).order_by('debut')]


@transaction.atomic
def renseigner(acteur, personne, dimension, valeur, debut, source, attendu, motif='', correction=None):
    suivi.exiger(acteur, 'view_personne', 'view_situationpersonnelle', 'view_revisionsituationpersonnelle', 'add_situationpersonnelle')
    # Aucun verrou ménage dans ce service : une histoire personnelle est indépendante des suivis.
    reserver(personne, attendu)
    if dimension not in dict(SituationSociale.DIMENSIONS) or valeur not in dict(SituationSociale.VALEURS.get(dimension, [])):
        raise ValidationError('Dimension ou valeur inconnue.')
    if not source.strip() or debut > timezone.localdate():
        raise ValidationError('Renseignez une source et une date non future.')
    if len(motif) > 240:
        raise ValidationError('Le motif est limité à 240 caractères.')
    avant = photographie(personne, dimension)
    if correction is not None:
        suivi.exiger(acteur, 'change_situationpersonnelle')
        if not motif.strip():
            raise ValidationError('La correction exige un motif.')
        try:
            fait = SituationPersonnelle.objects.get(pk=correction, personne=personne, dimension=dimension)
        except SituationPersonnelle.DoesNotExist:
            raise ValidationError('Situation à corriger introuvable pour cette personne.')
        if debut != fait.debut:
            raise ValidationError('Une correction de valeur conserve la date du fait ; utilisez un fait antérieur pour compléter la chronologie.')
        fait.valeur, fait.source = valeur, source
        fait.full_clean()
        fait.save(update_fields=['valeur', 'source'])
        action = 'correction'
    else:
        suivants = SituationPersonnelle.objects.filter(personne=personne, dimension=dimension, debut__gte=debut).order_by('debut')
        suivant = suivants.first()
        if suivant and suivant.debut == debut:
            raise ValidationError('Un fait existe déjà à cette date. Corrigez-le explicitement si c’est une erreur.')
        if suivant:
            suivi.exiger(acteur, 'change_situationpersonnelle')
            if not motif.strip():
                raise ValidationError('L’insertion d’un fait antérieur exige un motif.')
        precedent = SituationPersonnelle.objects.filter(personne=personne, dimension=dimension, debut__lt=debut).order_by('-debut').first()
        if precedent and (precedent.fin is None or precedent.fin > debut):
            precedent.fin = debut
            precedent.save(update_fields=['fin'])
        fait = SituationPersonnelle(personne=personne, dimension=dimension, valeur=valeur, debut=debut,
            fin=suivant.debut if suivant else None, source=source, auteur=acteur)
        fait.full_clean()
        fait.save()
        action = 'insertion' if suivant else 'changement'
    RevisionSituationPersonnelle.objects.create(personne=personne, situation=fait, action=action,
        avant=avant, apres=photographie(personne, dimension), motif=motif, auteur=acteur)
    return fait


def etat(acteur, personnes, date):
    """Restitution datée ; les divergences historiques restent visibles, jamais fusionnées en migration."""
    if not acteur.has_perm('personnes.view_personne'):
        return []
    personnes = list(personnes)
    from . import famille, coordonnees
    declarations = {x.personne_id: x for x in famille.a_date(personnes, date)} if acteur.has_perms(famille.DROITS_LECTURE) else {}
    contacts = {x.personne_id: x for x in coordonnees.a_date(personnes, date)} if acteur.has_perms(coordonnees.DROITS_LECTURE) else {}
    from . import complements_identite,relations_personnelles
    identites={x.personne_id:x for x in complements_identite.a_date(personnes,date)} if acteur.has_perms(complements_identite.DROITS_LECTURE) else {}
    from .models import RelationPersonnelle
    liens=list(RelationPersonnelle.objects.filter(Q(personne_a__in=personnes)|Q(personne_b__in=personnes),debut__lte=date,annule_le__isnull=True).filter(Q(fin__isnull=True)|Q(fin__gt=date)).select_related('personne_a','personne_b')) if acteur.has_perms(relations_personnelles.DROITS_LECTURE) else []
    communs = list(SituationPersonnelle.objects.filter(personne__in=personnes, debut__lte=date).filter(
        Q(fin__isnull=True) | Q(fin__gt=date))) if acteur.has_perm('personnes.view_situationpersonnelle') else []
    anciens = list(SituationSociale.objects.filter(beneficiaire__in=personnes, debut__lte=date,
        accompagnement__debut__lte=date).filter(Q(fin__isnull=True) | Q(fin__gt=date)).filter(
        Q(accompagnement__fin__isnull=True) | Q(accompagnement__fin__gt=date)).select_related('accompagnement')) if acteur.has_perms(
            ['personnes.view_situationsociale', *dossier.DROITS]) else []
    from . import dossier_complet
    dossier_a=dossier_complet.syntheses(acteur,personnes,date)
    resultat = []
    for personne in personnes:
        lignes = []
        for dimension, libelle in SituationSociale.DIMENSIONS:
            fait = next((x for x in communs if x.personne_id == personne.pk and x.dimension == dimension), None)
            temoins = [x for x in anciens if x.beneficiaire_id == personne.pk and x.dimension == dimension and (not fait or x.debut >= fait.debut)]
            valeurs = {x.valeur for x in temoins}
            if fait:
                valeurs.add(fait.valeur)
            conflit = len(valeurs) > 1
            texte = 'Informations divergentes — à vérifier' if conflit else (fait.libelle_valeur if fait else temoins[0].libelle_valeur if temoins else 'Non renseigné')
            projection=next((d for d in dossier_a.get(personne.pk,[]) if dimension=='ressources' and d['code']=='ressources' and d.get('valeur_sociale')),None)
            ancienne_synthese=''
            if projection:
                nouveau=dict(SituationSociale.VALEURS['ressources'])[projection['valeur_sociale']]
                if (fait or temoins) and texte!=nouveau:ancienne_synthese=texte
                texte=nouveau
            lignes.append({'projection':projection,'ancienne_synthese':ancienne_synthese,'dimension': dimension, 'libelle': libelle, 'texte': texte, 'fait': fait,
                           'anciens': temoins, 'conflit': conflit})
        resultat.append({'personne': personne, 'lignes': lignes, 'famille': declarations.get(personne.pk),
            'coordonnees': contacts.get(personne.pk), 'dossier_a':dossier_a.get(personne.pk,[]), 'identite_declaree':identites.get(personne.pk),
            'liens_personnels':[{'libelle':r.libelle_depuis(personne),'autre':r.autre(personne)} for r in liens if personne.pk in (r.personne_a_id,r.personne_b_id)]})
    return resultat


def cible_commentaire(objet):
    return {'menage' if isinstance(objet, Menage) else 'accompagnement' if isinstance(objet, Accompagnement) else 'personne': objet}


@transaction.atomic
def commenter(acteur, objet, texte, motif, attendu):
    suivi.exiger(acteur, 'view_personne', 'view_commentairedossier', 'add_commentairedossier')
    if not isinstance(objet, Personne):
        suivi.exiger(acteur, 'view_menage')
    if isinstance(objet, Accompagnement):
        suivi.exiger(acteur, 'view_accompagnement')
        # Même ordre que tous les services liés : ménage puis accompagnement.
        Menage.objects.filter(pk=objet.menage_id).update(revision=F('revision') + 1)
    reserver(objet, attendu)
    cible = cible_commentaire(objet)
    if CommentaireDossier.objects.filter(**cible).exists() and not motif.strip():
        raise ValidationError('Expliquez la modification du commentaire.')
    commentaire = CommentaireDossier(**cible, **tr.colonnes('texte', texte, max_length=4000), motif=motif, auteur=acteur)
    commentaire.full_clean()
    commentaire.save()
    return commentaire


@transaction.atomic
def ajouter_membre(acteur, menage, debut, attendu, personne=None, designation='', prenom=''):
    suivi.exiger(acteur, 'view_personne', 'view_menage', 'add_appartenance')
    reserver(menage, attendu)
    if personne is None:
        suivi.exiger(acteur, 'add_personne')
        personne = Personne(designation=designation, prenom=prenom, cree_par=acteur)
        personne.full_clean()
        personne.save()
    if Appartenance.objects.filter(menage=menage, personne=personne).filter(Q(fin__isnull=True) | Q(fin__gt=debut)).exists():
        raise ValidationError('Cette personne a déjà une appartenance recouvrant cette date ou une période ultérieure. Consultez son historique.')
    return suivi.ajouter_appartenance(acteur, menage, personne, debut)


def nombre_jours(periodes, jour):
    """Union des intervalles civils, sans multiplication par bénéficiaire ou service."""
    bornes = sorted((p.debut, p.fin or max(p.debut, jour)) for p in periodes)
    total, fin = 0, None
    for debut, borne in bornes:
        depart = max(debut, fin) if fin else debut
        total += max(0, (borne - depart).days)
        fin = max(fin, borne) if fin else borne
    return total


def resume_prestations(a, sejours, repas, jour, lieux=False):
    sejours = [s for s in sejours if s.accord.accompagnement_id == a.pk]
    repas = [r for r in repas if r.accompagnement_id == a.pk and not r.annule_le]
    morceaux = []
    if sejours:
        texte = f'Héberg. {nombre_jours(sejours, jour)} nuits'
        if any(s.fin is None for s in sejours):
            texte += ' à ce jour · ouvert'
        if lieux:
            actuelles = [x for s in sejours if s.debut <= jour and (s.fin is None or s.fin > jour)
                for x in getattr(s, 'lieux_dossier', []) if x.debut <= jour and (x.fin is None or x.fin > jour)]
            connues = sorted([x for s in sejours for x in getattr(s, 'lieux_dossier', [])
                if x.debut <= jour], key=lambda x: (x.debut, x.pk), reverse=True)
            if actuelles:
                noms = list(dict.fromkeys(str(x.lieu) for x in actuelles))
                texte += ' — Lieu actuel : ' + ' ; '.join(noms)
            elif connues:
                derniere = connues[0]
                texte += f' — Dernier lieu connu : {derniere.lieu} (depuis le {derniere.debut:%d/%m/%Y})'
            else:
                texte += ' — Lieu non renseigné'
        morceaux.append(texte)
    if repas:
        texte = f'Repas {nombre_jours(repas, jour)} jours accordés'
        if any(r.fin is None for r in repas):
            texte += ' à ce jour · sans fin prévue'
        morceaux.append(texte)
    return ' · '.join(morceaux) or 'Aucune prestation consultable'
