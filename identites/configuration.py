"""Politique technique de l’espace fictif ; aucun rang ou rôle social."""
from importlib.util import find_spec
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

POLITIQUES = {"desactive", "optionnel", "obligatoire"}


def lire(environnement):
    politique = environnement.get("ACCOMPAGNEMENT_2FA", "desactive").strip()
    if politique not in POLITIQUES:
        raise ImproperlyConfigured("ACCOMPAGNEMENT_2FA : choisir desactive, optionnel ou obligatoire.")
    cles = [v.strip() for v in environnement.get("ACCOMPAGNEMENT_2FA_CLES", "").split(",") if v.strip()]
    return politique, cles


def disponible():
    return (not settings.MODE_LOCAL and settings.DOUBLE_FACTEUR_POLITIQUE != "desactive"
        and bool(settings.DOUBLE_FACTEUR_CLES)
        and all(find_spec(n) is not None for n in ("django_otp", "cryptography", "qrcode")))


def service_indisponible():
    return (not settings.MODE_LOCAL and settings.DOUBLE_FACTEUR_POLITIQUE != "desactive"
        and not disponible())


def verifier():
    if settings.MODE_LOCAL or settings.DOUBLE_FACTEUR_POLITIQUE == "desactive":
        return
    if not disponible():
        raise ImproperlyConfigured("Le 2FA exige requirements-2fa.txt et ACCOMPAGNEMENT_2FA_CLES.")
    from cryptography.fernet import Fernet
    try:
        for cle in settings.DOUBLE_FACTEUR_CLES:
            Fernet(cle)
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured("ACCOMPAGNEMENT_2FA_CLES contient une clé Fernet invalide.") from exc
