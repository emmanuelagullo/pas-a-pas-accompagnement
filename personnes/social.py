"""CHRS4 : valeurs datées par dimension, sans reconstruction événementielle."""
from . import textes_riches as tr
from .verrous_metier import serialiser
from django.core.exceptions import ValidationError
from django.core import signing
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone
from .models import Accompagnement, SituationSociale, EvenementSocial, BilanSocial, OperationSociale
from .suivi import exiger


def droit(acteur, action):
    exiger(acteur, "view_personne", "view_menage", "view_accompagnement", action)


def verrouiller(accompagnement):
    Accompagnement.objects.filter(pk=accompagnement.pk).update(revision_sociale=F("revision_sociale")+1)
    return Accompagnement.objects.get(pk=accompagnement.pk)


def date_valide(accompagnement, date):
    if date < accompagnement.debut or (accompagnement.fin and date >= accompagnement.fin) or date > timezone.localdate():
        raise ValidationError("La date d’effet doit appartenir à l’accompagnement et ne pas être future.")


def date_evenement(accompagnement, date):
    if date > timezone.localdate() or (accompagnement.fin and date >= accompagnement.fin):
        raise ValidationError("L’événement doit être non futur et antérieur à la fin du suivi. Son histoire peut précéder le début.")


def personne_valide(accompagnement, personne):
    if not accompagnement.beneficiaires.filter(pk=personne.pk).exists():
        raise ValidationError("Choisissez un bénéficiaire de cet accompagnement.")


def jeton_situations(accompagnement):
    return signing.dumps([str(accompagnement.pk), accompagnement.revision_sociale], salt='chrs25-situations')


def verifier_situations(accompagnement, attendu):
    try:
        etat = signing.loads(attendu, salt='chrs25-situations', max_age=86400)
    except signing.BadSignature as exc:
        raise ValidationError('Le formulaire a expiré. Rechargez le suivi social.') from exc
    # verrouiller a réservé la révision suivante dans cette transaction.
    if etat != [str(accompagnement.pk), accompagnement.revision_sociale - 1]:
        raise ValidationError('Le suivi social a changé. Rechargez le formulaire.')


@serialiser("accompagnement")
@transaction.atomic
def renseigner(acteur, accompagnement, beneficiaire, dimension, valeur, debut, source, motif='', attendu=None):
    droit(acteur, "add_situationsociale")
    droit(acteur, "view_situationsociale")
    a = verrouiller(accompagnement)
    if attendu is not None:
        verifier_situations(a, attendu)
    date_valide(a, debut)
    personne_valide(a, beneficiaire)
    serie = SituationSociale.objects.filter(accompagnement=a, beneficiaire=beneficiaire, dimension=dimension)
    if serie.filter(debut=debut).exists():
        raise ValidationError('Une situation existe déjà à cette date. Utilisez Corriger.')
    precedente = serie.filter(debut__lt=debut).order_by('-debut').first()
    suivante = serie.filter(debut__gt=debut).order_by('debut').first()
    if suivante:
        from .corrections import motif_valide
        droit(acteur, 'change_situationsociale')
        droit(acteur, 'view_correctionperiode')
        if attendu is None:
            raise ValidationError('Rechargez le formulaire pour insérer une situation antérieure.')
        motif = motif_valide(motif)
    nouvelle = SituationSociale(accompagnement=a, beneficiaire=beneficiaire, dimension=dimension,
        valeur=valeur, debut=debut, fin=suivante.debut if suivante else None, source=source, cree_par=acteur)
    nouvelle.clean_fields()
    nouvelle.clean()
    if precedente and (precedente.fin is None or precedente.fin > debut):
        ancien = (precedente.debut, precedente.fin, precedente.source)
        precedente.fin = debut
        precedente.full_clean()
        precedente.save(update_fields=['fin'])
        if suivante:
            from .corrections import enregistrer
            enregistrer(acteur, precedente, ancien, motif)
    nouvelle.full_clean()
    nouvelle.save()
    OperationSociale.objects.create(accompagnement=a, situation=nouvelle,
        action='Situation insérée' if suivante else 'Situation renseignée', date_effet=debut,
        auteur=acteur, nouvelle_valeur=valeur, motif=motif if suivante else '')
    return nouvelle


def etat_valeur(situation):
    return [str(situation.pk), situation.valeur, str(situation.debut), str(situation.fin), situation.source]


def jeton_valeur(situation):
    return signing.dumps(etat_valeur(situation), salt='chrs25-valeur')


@serialiser("situation")
@transaction.atomic
def corriger(acteur, situation, valeur, motif, attendu=None):
    droit(acteur,"change_situationsociale"); droit(acteur,"view_situationsociale")
    a=verrouiller(situation.accompagnement)
    situation=SituationSociale.objects.get(pk=situation.pk)
    if attendu is not None:
        try:
            precedent = signing.loads(attendu, salt='chrs25-valeur', max_age=86400)
        except signing.BadSignature as exc:
            raise ValidationError('Le formulaire a expiré. Rechargez la situation.') from exc
        if precedent != etat_valeur(situation):
            raise ValidationError('Cette situation a changé. Rechargez le formulaire.')
    motif=motif.strip()
    if not motif or len(motif)>240: raise ValidationError("Indiquez un motif de 1 à 240 caractères.")
    ancienne=situation.valeur
    if ancienne==valeur: raise ValidationError("La valeur est inchangée.")
    situation.valeur=valeur; situation.full_clean(); situation.save(update_fields=["valeur"])
    OperationSociale.objects.create(accompagnement=a,situation=situation,action="Valeur corrigée",date_effet=situation.debut,auteur=acteur,ancienne_valeur=ancienne,nouvelle_valeur=valeur,motif=motif)
    return situation


@serialiser("accompagnement")
@transaction.atomic
def evenement(acteur, accompagnement, beneficiaire, date_effet, texte, source, anterieur=False):
    droit(acteur,"add_evenementsocial"); droit(acteur,"view_evenementsocial")
    a=verrouiller(accompagnement)
    if date_effet < a.debut and not anterieur:
        raise ValidationError("Pour un fait antérieur, cochez explicitement l’histoire antérieure.")
    date_evenement(a, date_effet)
    personne_valide(a,beneficiaire)
    objet=EvenementSocial(accompagnement=a,beneficiaire=beneficiaire,date_effet=date_effet,texte=texte,source=source,cree_par=acteur)
    objet.full_clean(); objet.save()
    OperationSociale.objects.create(accompagnement=a,evenement=objet,action="Événement antérieur enregistré" if date_effet < a.debut else "Événement enregistré",date_effet=date_effet,auteur=acteur)
    return objet


@serialiser("accompagnement")
@transaction.atomic
def bilan(acteur, accompagnement, date_effet, texte):
    droit(acteur,"add_bilansocial"); droit(acteur,"view_bilansocial")
    a=verrouiller(accompagnement)
    date_valide(a,date_effet)
    objet=BilanSocial(accompagnement=a,date_effet=date_effet,**tr.colonnes('texte', texte, max_length=2000, required=True),cree_par=acteur)
    objet.full_clean(); objet.save()
    OperationSociale.objects.create(accompagnement=a,bilan=objet,action="Bilan enregistré",date_effet=date_effet,auteur=acteur)
    return objet


def etat_date(accompagnement, date):
    if date < accompagnement.debut or (accompagnement.fin and date >= accompagnement.fin):
        return SituationSociale.objects.none()
    return accompagnement.situations_sociales.filter(debut__lte=date).filter(Q(fin__isnull=True)|Q(fin__gt=date)).select_related("beneficiaire")
