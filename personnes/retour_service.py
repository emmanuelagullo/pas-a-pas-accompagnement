"""Retour vers le travail du jour, sans redirection arbitraire."""
from datetime import date
from django.urls import reverse


def date_service(valeur):
    try:
        jour = date.fromisoformat(valeur)
    except (TypeError, ValueError):
        return ""
    return jour.isoformat() if len(valeur) == 10 else ""


def url_jour(valeur):
    jour = date_service(valeur)
    return reverse("suivi:jour") + ("?date=" + jour if jour else "")
