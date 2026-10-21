from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from .models import Transmission, NotePartagee, Personne, Accompagnement, Sejour
from . import transmissions
from .retour_service import date_service, url_jour


class TexteForm(forms.Form):
    contenu = forms.CharField(label="Texte", widget=forms.Textarea(attrs={"rows": 4}))


class CorrectionForm(TexteForm):
    texte_attendu = forms.CharField(widget=forms.HiddenInput)
    motif = forms.CharField(label="Motif de correction", widget=forms.Textarea(attrs={"rows": 2}))


@login_required
@permission_required("personnes.view_transmission", raise_exception=True)
@require_http_methods(["GET", "POST"])
def cahier(request):
    form = TexteForm(request.POST or None)
    if request.method == "POST" and request.user.has_perm("personnes.add_transmission") and form.is_valid():
        transmissions.transmettre(request.user, form.cleaned_data["contenu"])
        if request.POST.get("retour") == "jour":
            return redirect(url_jour(request.POST.get("date_service")))
        return redirect("suivi:cahier")
    if request.method == "POST" and not request.user.has_perm("personnes.add_transmission"):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request, "suivi/transmissions.html", {"titre": "Cahier de liaison",
        "form": form if request.user.has_perm("personnes.add_transmission") else None,
        "contributions": Transmission.objects.select_related("auteur").prefetch_related("revisions__auteur"), "nature": "transmission",
        "retour_jour": request.GET.get("retour") == "jour" or request.POST.get("retour") == "jour",
        "date_service": date_service(request.POST.get("date_service") or request.GET.get("date_service"))})


CIBLES = {"personne": (Personne, "view_personne"), "accompagnement": (Accompagnement, "view_accompagnement"), "sejour": (Sejour, "view_sejour")}


@login_required
@permission_required("personnes.view_notepartagee", raise_exception=True)
@require_http_methods(["GET", "POST"])
def notes(request, nature, pk):
    if nature not in CIBLES:
        from django.http import Http404
        raise Http404
    modele, permission = CIBLES[nature]
    if not request.user.has_perm("personnes." + permission):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    cible = get_object_or_404(modele, pk=pk)
    form = TexteForm(request.POST or None)
    if request.method == "POST":
        if not request.user.has_perm("personnes.add_notepartagee"):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        if form.is_valid():
            transmissions.noter(request.user, form.cleaned_data["contenu"], **{nature: cible})
            return redirect("suivi:notes", nature=nature, pk=pk)
    return render(request, "suivi/transmissions.html", {"titre": "Notes partagées",
        "form": form if request.user.has_perm("personnes.add_notepartagee") else None,
        "contributions": NotePartagee.objects.filter(**{nature: cible}).select_related("auteur").prefetch_related("revisions__auteur"), "nature": "note"})


@login_required
@require_http_methods(["GET", "POST"])
def corriger(request, nature, pk):
    if nature not in ("transmission", "note"):
        from django.http import Http404
        raise Http404
    modele = Transmission if nature == "transmission" else NotePartagee
    permission = "transmission" if nature == "transmission" else "notepartagee"
    for droit in ("view_" + permission, "change_" + permission):
        if not request.user.has_perm("personnes." + droit):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
    contribution = get_object_or_404(modele, pk=pk)
    if nature == "note":
        cible = contribution.personne or contribution.accompagnement or contribution.sejour
        if not request.user.has_perm("personnes.view_" + type(cible).__name__.lower()):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
    form = CorrectionForm(request.POST or None, initial={"contenu": contribution.contenu, "texte_attendu": contribution.contenu})
    if request.method == "POST" and form.is_valid():
        try:
            transmissions.rectifier(request.user, contribution, form.cleaned_data["contenu"],
                                     form.cleaned_data["motif"], texte_attendu=form.cleaned_data["texte_attendu"])
        except ValidationError as erreur:
            form.add_error(None, erreur)
            return render(request, "suivi/corriger_transmission.html", {"form": form}, status=409)
        if nature == "transmission":
            return redirect("suivi:cahier")
        cible_nature = next(n for n in CIBLES if getattr(contribution, n + "_id") is not None)
        return redirect("suivi:notes", nature=cible_nature, pk=getattr(contribution, cible_nature + "_id"))
    return render(request, "suivi/corriger_transmission.html", {"form": form})
