from django.contrib.auth.decorators import login_required
from django.db import OperationalError
from django.utils import timezone
from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods, require_safe
from .models import Accompagnement, AccordHebergement, Sejour, Affectation, Absence
from .forms_hebergement import AccordForm, AdmissionForm, AffectationForm, PeriodeForm, LieuForm, ClotureForm
from .vues_suivi import traiter
from . import hebergement as h


def traiter_hebergement(*args, **kwargs):
    try:
        return traiter(*args, **kwargs)
    except OperationalError:
        return HttpResponse("L’écriture n’a pas été confirmée. Rechargez la fiche avant de réessayer.", status=409)


@require_http_methods(["GET", "POST"])
@login_required
def accorder(request, pk):
    h.droit(request.user, "add_accordhebergement")
    a = get_object_or_404(Accompagnement, pk=pk)
    form = AccordForm(request.POST or None, beneficiaires=a.beneficiaires.all(),
        initial={"debut": timezone.localdate(), "beneficiaires": list(a.beneficiaires.values_list("pk", flat=True))})
    return traiter_hebergement(request, form, "Accorder un hébergement", lambda **d:h.accorder(request.user,a,**d), a.menage, retour=lambda accord: reverse("suivi:accord_hebergement", args=[accord.pk]))


@require_safe
@login_required
def detail(request, pk):
    h.droit(request.user, "view_sejour")
    accord = get_object_or_404(AccordHebergement.objects.select_related("accompagnement__menage"),pk=pk)
    return render(request,"hebergement/detail.html", {"accord":accord,
        "aujourdhui": timezone.localdate(),
        "sejours":accord.sejours.prefetch_related("beneficiaires", "affectations__lieu", "absences").order_by("debut"),
        "operations":accord.operations.select_related("auteur") if request.user.has_perm("personnes.view_operationhebergement") else []})


@require_http_methods(["GET", "POST"])
@login_required
def admettre(request, pk):
    h.droit(request.user,"add_sejour")
    a=get_object_or_404(AccordHebergement,pk=pk)
    return traiter_hebergement(request,AdmissionForm(request.POST or None,beneficiaires=a.beneficiaires.all(),
        initial={"debut": a.debut if a.fin and timezone.localdate() >= a.fin else max(a.debut, timezone.localdate()),
                 "beneficiaires": list(a.beneficiaires.values_list("pk", flat=True))}),"Enregistrer une admission effective",lambda **d:h.admettre(request.user,a,**d),a.accompagnement.menage, retour=reverse("suivi:accord_hebergement", args=[a.pk]))


@require_http_methods(["GET", "POST"])
@login_required
def periode(request, pk, absence=False):
    h.droit(request.user,"add_absence" if absence else "add_affectation")
    if not absence: h.exiger(request.user,"view_lieuhebergement")
    s=get_object_or_404(Sejour,pk=pk)
    form=(PeriodeForm if absence else AffectationForm)(request.POST or None,
        initial={"debut": max(s.debut, timezone.localdate())})
    return traiter_hebergement(request,form,"Enregistrer une absence de tous les bénéficiaires" if absence else "Affecter tous les bénéficiaires à un lieu",lambda **d:h.ajouter_periode(request.user,s,absence=absence,**d),s.accord.accompagnement.menage, retour=reverse("suivi:accord_hebergement", args=[s.accord_id]))


@require_http_methods(["GET", "POST"])
@login_required
def terminer(request, pk, nature):
    h.droit(request.user,"change_"+nature)
    modele={"sejour":Sejour,"affectation":Affectation,"absence":Absence}[nature]
    objet=get_object_or_404(modele,pk=pk)
    s=objet if nature=="sejour" else objet.sejour
    action=h.sortir if nature=="sejour" else h.terminer_periode
    # La fin est exclue : proposer aujourd'hui seulement si la période a
    # commencé avant aujourd'hui. Une clôture le jour du début est invalide.
    debut = objet.debut
    initial = {"fin": timezone.localdate()} if debut < timezone.localdate() else {}
    return traiter_hebergement(request,ClotureForm(request.POST or None, initial=initial),"Enregistrer la sortie" if nature=="sejour" else "Clôturer la période",lambda **d:action(request.user,objet,**d),s.accord.accompagnement.menage, retour=reverse("suivi:accord_hebergement", args=[s.accord_id]))


@require_http_methods(["GET", "POST"])
@login_required
def lieu(request):
    h.droit(request.user,"add_lieuhebergement")
    h.exiger(request.user,"view_lieuhebergement")
    form=LieuForm(request.POST or None)
    from django.shortcuts import redirect
    if request.method=="POST" and form.is_valid():
        h.creer_lieu(request.user,**form.cleaned_data)
        return redirect("suivi:liste")
    return render(request,"suivi/form.html",{"form":form,"titre":"Créer un lieu d’hébergement"})
