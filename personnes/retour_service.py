"""Retour vers le travail du jour, sans redirection arbitraire."""
from datetime import date
from django.urls import reverse


def contexte_jour(request):
    retour = request.POST.get("retour") or request.GET.get("retour")
    jour = date_service(request.POST.get("date_service") or request.GET.get("date_service"))
    return {"retour_jour": retour == "jour", "date_service": jour if retour == "jour" else ""}


def suffixe_jour(request):
    contexte = contexte_jour(request)
    if not contexte["retour_jour"]:
        return ""
    return "?retour=jour" + ("&date_service=" + contexte["date_service"] if contexte["date_service"] else "")


def date_service(valeur):
    try:
        jour = date.fromisoformat(valeur)
    except (TypeError, ValueError):
        return ""
    return jour.isoformat() if len(valeur) == 10 else ""


def url_jour(valeur):
    jour = date_service(valeur)
    return reverse("suivi:jour") + ("?date=" + jour if jour else "")
