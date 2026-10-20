from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_safe
from .models import Accompagnement, AccordRepas, RepasDistribue
from .forms_repas import AccordForm, DistributionForm, AnnulationForm
from .vues_suivi import traiter
from . import repas


@require_http_methods(["GET", "POST"])
@login_required
def accorder(request, pk):
    repas.droit(request.user, "add_accordrepas")
    suivi = get_object_or_404(Accompagnement, pk=pk)
    form = AccordForm(request.POST or None, accompagnement=suivi)
    return traiter(request, form, "Accorder des repas", lambda **d: repas.accorder(request.user, suivi, **d), suivi.menage, retour=lambda accord: reverse("suivi:accord_repas", args=[accord.pk]))


@require_safe
@login_required
def detail(request, pk):
    repas.droit(request.user, "view_repasdistribue")
    accord = get_object_or_404(AccordRepas.objects.select_related("accompagnement__menage"), pk=pk)
    realisations = accord.realisations.select_related("beneficiaire", "annule_par")
    total = realisations.filter(annule_le__isnull=True).aggregate(total=Sum("quantite"))["total"] or 0
    return render(request, "repas/detail.html", {"accord": accord, "realisations": realisations, "total": total,
        "operations": accord.operations.select_related("auteur") if request.user.has_perm("personnes.view_operationrepas") else []})


@require_http_methods(["GET", "POST"])
@login_required
def distribuer(request, pk):
    repas.droit(request.user, "add_repasdistribue")
    repas.droit(request.user, "view_repasdistribue")
    accord = get_object_or_404(AccordRepas, pk=pk)
    form = DistributionForm(request.POST or None, accord=accord)
    return traiter(request, form, "Enregistrer des repas distribués", lambda **d: repas.distribuer(request.user, accord, **d), accord.accompagnement.menage, retour=reverse("suivi:accord_repas", args=[accord.pk]))


@require_http_methods(["GET", "POST"])
@login_required
def annuler(request, pk):
    repas.droit(request.user, "change_repasdistribue")
    repas.droit(request.user, "view_repasdistribue")
    objet = get_object_or_404(RepasDistribue.objects.select_related("accord__accompagnement__menage"), pk=pk)
    return traiter(request, AnnulationForm(request.POST or None), "Annuler une distribution", lambda **d: repas.annuler(request.user, objet, **d), objet.accord.accompagnement.menage, retour=reverse("suivi:accord_repas", args=[objet.accord_id]))
