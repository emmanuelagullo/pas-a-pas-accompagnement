"""CHRS2 : accords immuables et réalisations annulables, droits explicites."""
from .verrous_metier import serialiser
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.utils import timezone
from .models import AccordRepas, RepasDistribue, OperationRepas, Accompagnement
from .suivi import exiger


def droit(acteur, action):
    exiger(acteur, "view_personne", "view_menage", "view_accompagnement", "view_accordrepas", action)


@serialiser("accompagnement")
@transaction.atomic
def accorder(acteur, accompagnement, beneficiaires, debut, fin, service, prestataire=""):
    droit(acteur, "add_accordrepas")
    accompagnement = Accompagnement.objects.get(pk=accompagnement.pk)
    ids = {p.pk for p in beneficiaires}
    if not ids or not ids.issubset(set(accompagnement.beneficiaires.values_list("pk", flat=True))):
        raise ValidationError("Choisissez des bénéficiaires de cet accompagnement.")
    if debut < accompagnement.debut or (accompagnement.fin and (fin is None or fin > accompagnement.fin)):
        raise ValidationError("La période accordée doit être comprise dans l’accompagnement.")
    accord = AccordRepas(accompagnement=accompagnement, debut=debut, fin=fin, service=service, prestataire=prestataire, cree_par=acteur)
    accord.full_clean()
    accord.save()
    accord.beneficiaires.set(ids)
    OperationRepas.objects.create(accord=accord, action="accorde", auteur=acteur, date_effet=debut)
    return accord


@serialiser("accord")
@transaction.atomic
def distribuer(acteur, accord, beneficiaire, date, quantite):
    droit(acteur, "add_repasdistribue")
    exiger(acteur, "view_repasdistribue")
    accord = AccordRepas.objects.select_related("accompagnement").get(pk=accord.pk)
    if not accord.beneficiaires.filter(pk=beneficiaire.pk).exists():
        raise ValidationError("Cette personne ne bénéficie pas de cet accord.")
    if date < accord.debut or (accord.fin and date >= accord.fin):
        raise ValidationError("La distribution doit se situer dans la période accordée.")
    suivi = accord.accompagnement
    if date < suivi.debut or (suivi.fin and date >= suivi.fin):
        raise ValidationError("La distribution doit se situer dans l’accompagnement.")
    if date > timezone.localdate():
        raise ValidationError("Une distribution effective ne peut pas être future.")
    repas = RepasDistribue(accord=accord, beneficiaire=beneficiaire, date=date, quantite=quantite, cree_par=acteur)
    repas.full_clean()
    try:
        with transaction.atomic():
            repas.save()
    except IntegrityError as erreur:
        raise ValidationError("Une distribution existe déjà pour cet accord, cette personne et ce jour. Rechargez la fiche.") from erreur
    OperationRepas.objects.create(accord=accord, repas=repas, action="distribue", auteur=acteur, date_effet=date)
    return repas


@serialiser("repas")
@transaction.atomic
def annuler(acteur, repas, motif):
    droit(acteur, "change_repasdistribue")
    exiger(acteur, "view_repasdistribue")
    motif = motif.strip()
    if not motif or len(motif) > 240:
        raise ValidationError("Indiquez un motif de 1 à 240 caractères.")
    if RepasDistribue.objects.filter(pk=repas.pk, annule_le__isnull=True).update(annule_le=timezone.now(), annule_par=acteur, motif_annulation=motif) != 1:
        raise ValidationError("Cette distribution est déjà annulée.")
    OperationRepas.objects.create(accord=repas.accord, repas=repas, action="annule", auteur=acteur, date_effet=repas.date)


def avertissements(realisations):
    """Signaler les cumuls sans transformer une alerte en interdiction globale."""
    from django.db.models import Count
    realisations = list(realisations)
    if not realisations:
        return []
    groupes = RepasDistribue.objects.filter(annule_le__isnull=True,
        beneficiaire_id__in={r.beneficiaire_id for r in realisations},
        date__in={r.date for r in realisations}).values('beneficiaire_id', 'date', 'accord__service').annotate(nombre=Count('pk'))
    cumuls = {(g['beneficiaire_id'], g['date'], g['accord__service']) for g in groupes if g['nombre'] > 1}
    alertes = []
    vus = set()
    for r in realisations:
        cle = (r.beneficiaire_id, r.date, r.accord.service)
        if r.quantite > 1:
            alertes.append(f'{r.beneficiaire} — {r.date:%d/%m/%Y} : quantité supérieure à un pour ce service. Vérifiez la quantité effectivement distribuée.')
        if cle in cumuls and cle not in vus:
            alertes.append(f'{r.beneficiaire} — {r.date:%d/%m/%Y} : plusieurs distributions pour le même service sous des accords différents. Vérifiez le cumul.')
        vus.add(cle)
    return alertes


def jeton_services(accompagnement):
    from django.core import signing
    return signing.dumps([str(accompagnement.pk), accompagnement.revision_sociale,
        str(accompagnement.debut), str(accompagnement.fin),
        sorted(str(pk) for pk in accompagnement.beneficiaires.values_list('pk', flat=True))], salt='chrs25-services-repas')


@serialiser('accompagnement')
def accorder_services(acteur, accompagnement, beneficiaires, debut, fin, services, attendu, prestataire=''):
    from django.core import signing
    from .social import verrouiller
    droit(acteur, 'add_accordrepas')
    a = verrouiller(accompagnement)
    try:
        precedent = signing.loads(attendu, salt='chrs25-services-repas', max_age=86400)
    except signing.BadSignature as exc:
        raise ValidationError('Le formulaire a expiré. Rechargez l’accompagnement.') from exc
    etat = [str(a.pk), a.revision_sociale - 1, str(a.debut), str(a.fin),
        sorted(str(pk) for pk in a.beneficiaires.values_list('pk', flat=True))]
    if precedent != etat:
        raise ValidationError('Cet accompagnement a changé. Rechargez le formulaire.')
    services = list(services)
    if not services or len(set(services)) != len(services) or not set(services).issubset(dict(AccordRepas.SERVICES)):
        raise ValidationError('Sélectionnez des services distincts parmi ceux proposés.')
    beneficiaires = list(beneficiaires)
    return [accorder(acteur, a, beneficiaires, debut, fin, service, prestataire) for service in services]
