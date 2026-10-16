"""Stockage CHRS et consommation atomique ; primitives fournies par Pas communs."""
import logging
import secrets
import uuid
from dataclasses import dataclass
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables
from pas_communs.authentification import totp
from .models import DoubleFacteur, CodeSecours

logger = logging.getLogger("identites.securite")


@dataclass(frozen=True)
class Preuve:
    revision: str
    secours: bool = False


def compte(utilisateur):
    return DoubleFacteur.objects.filter(utilisateur=utilisateur).first()


def requis(utilisateur):
    ligne = compte(utilisateur)
    return bool((ligne and ligne.a_reinscrire) or (
        not settings.MODE_LOCAL and settings.DOUBLE_FACTEUR_POLITIQUE == "obligatoire"))


@sensitive_variables()
def commencer(utilisateur):
    with transaction.atomic():
        ligne, _ = DoubleFacteur.objects.get_or_create(utilisateur=utilisateur)
        ligne = DoubleFacteur.objects.select_for_update().get(pk=ligne.pk)
        if ligne.inscrit:
            raise ValidationError("Le second facteur est déjà activé.")
        if ligne.cle_chiffree:
            from cryptography.fernet import InvalidToken
            try:
                totp.dechiffrer(ligne.cle_chiffree, cles=settings.DOUBLE_FACTEUR_CLES)
            except InvalidToken:
                ligne.cle_chiffree = ""
        if not ligne.cle_chiffree:
            ligne.cle_chiffree = totp.chiffrer(secrets.token_bytes(totp.OCTETS_CLE), cles=settings.DOUBLE_FACTEUR_CLES)
            ligne.revision = uuid.uuid4()
            ligne.save(update_fields=["cle_chiffree", "revision"])
        return ligne


@sensitive_variables()
def _pas(ligne, saisie, instant):
    from cryptography.fernet import InvalidToken
    try:
        cle = totp.dechiffrer(ligne.cle_chiffree, cles=settings.DOUBLE_FACTEUR_CLES)
    except InvalidToken:
        logger.error("auth.cle_illisible compte=%s", ligne.utilisateur_id)
        return None
    return totp.verifier_pas(cle, saisie, dernier_pas=ligne.dernier_pas, instant=instant)


@sensitive_variables()
def verifier(utilisateur, saisie, *, revision=None, instant=None):
    ligne = compte(utilisateur)
    if not ligne or not ligne.inscrit or (revision is not None and str(ligne.revision) != revision):
        return None
    code = totp.normaliser_code_secours(saisie)
    if code:
        # La sous-requête sur la révision et l’UPDATE du code constituent une
        # seule instruction : un reset concurrent ne valide pas l’ancien code.
        accepte = CodeSecours.objects.filter(compte=ligne, compte__revision=ligne.revision,
            compte__confirme_le__isnull=False, empreinte=totp.empreinte_code_secours(code),
            utilise_le__isnull=True).update(utilise_le=timezone.now())
        return Preuve(str(ligne.revision), True) if accepte else None
    pas = _pas(ligne, saisie, instant)
    if pas is None:
        return None
    # Comparer-et-échanger, y compris sur SQLite où select_for_update est sans effet.
    accepte = DoubleFacteur.objects.filter(pk=ligne.pk, revision=ligne.revision,
        confirme_le__isnull=False, dernier_pas=ligne.dernier_pas).update(dernier_pas=pas)
    return Preuve(str(ligne.revision)) if accepte else None


@sensitive_variables()
def _codes(ligne):
    codes = set()
    while len(codes) < totp.NOMBRE_CODES_SECOURS:
        codes.add(totp.nouveau_code_secours())
    CodeSecours.objects.filter(compte=ligne).delete()
    CodeSecours.objects.bulk_create(CodeSecours(compte=ligne,
        empreinte=totp.empreinte_code_secours(code)) for code in codes)
    return [totp.presenter_code_secours(code) for code in codes]


@sensitive_variables()
def confirmer(utilisateur, saisie, *, instant=None):
    with transaction.atomic():
        ligne = compte(utilisateur)
        if not ligne or ligne.inscrit or not ligne.cle_chiffree:
            return None
        pas = _pas(ligne, saisie, instant)
        if pas is None:
            return None
        revision = uuid.uuid4()
        modifie = DoubleFacteur.objects.filter(pk=ligne.pk, revision=ligne.revision,
            confirme_le__isnull=True, dernier_pas=ligne.dernier_pas).update(
                confirme_le=timezone.now(), dernier_pas=pas, revision=revision, a_reinscrire=False)
        if not modifie:
            return None
        ligne.refresh_from_db()
        return str(revision), _codes(ligne)


@sensitive_variables()
def regenerer(utilisateur, preuve):
    with transaction.atomic():
        ligne = compte(utilisateur)
        revision = uuid.uuid4()
        if not ligne or not DoubleFacteur.objects.filter(pk=ligne.pk, revision=preuve.revision,
                confirme_le__isnull=False).update(revision=revision):
            raise ValidationError("La configuration a changé. Recommencez la connexion.")
        ligne.refresh_from_db()
        return str(revision), _codes(ligne)


@sensitive_variables()
def reinitialiser(utilisateur, *, preuve=None, a_reinscrire=True):
    with transaction.atomic():
        ligne, _ = DoubleFacteur.objects.get_or_create(utilisateur=utilisateur)
        requete = DoubleFacteur.objects.filter(pk=ligne.pk)
        if preuve is not None:
            requete = requete.filter(revision=preuve.revision, confirme_le__isnull=False)
        revision = uuid.uuid4()
        if not requete.update(cle_chiffree="", confirme_le=None, dernier_pas=0,
                revision=revision, a_reinscrire=a_reinscrire):
            raise ValidationError("La configuration a changé. Recommencez la connexion.")
        CodeSecours.objects.filter(compte=ligne).delete()
        return str(revision)
