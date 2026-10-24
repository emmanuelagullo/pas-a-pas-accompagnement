from . import textes_riches as tr
from django import forms
from .champs_saisie import FormulaireMetier
from django.db import OperationalError
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .models import Transmission, NotePartagee, Personne, Accompagnement, Sejour
from . import transmissions, dossier
from .retour_service import date_service, url_jour, contexte_jour, suffixe_jour


class TexteForm(FormulaireMetier):
    contenu = tr.ChampTexte(label="Texte", widget=tr.WidgetTexte(attrs={"rows": 4}))


class CorrectionForm(TexteForm):
    etat_attendu = forms.CharField(widget=forms.HiddenInput, required=False)
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
    a = cible if nature == 'accompagnement' else cible.accord.accompagnement if nature == 'sejour' else None
    navigation = dossier.lire_personne(request, cible.pk) if nature == 'personne' else dossier.lire(request, a)
    form = TexteForm(request.POST or None)
    if request.method == "POST":
        if not request.user.has_perm("personnes.add_notepartagee"):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        if form.is_valid():
            transmissions.noter(request.user, form.cleaned_data["contenu"], **{nature: cible})
            if navigation:
                return redirect(navigation["retour_dossier"])
            return redirect(reverse("suivi:notes", kwargs={"nature": nature, "pk": pk}) + suffixe_jour(request))
    retour = None
    if nature == 'personne':
        retour = reverse('personnes:detail', args=[cible.pk])
    elif nature == 'accompagnement' and request.user.has_perms(['personnes.view_personne', 'personnes.view_menage']):
        retour = reverse('suivi:accompagnement', args=[cible.pk])
    elif nature == 'sejour' and request.user.has_perms(['personnes.view_personne', 'personnes.view_menage', 'personnes.view_accompagnement', 'personnes.view_accordhebergement']):
        retour = reverse('suivi:accord_hebergement', args=[cible.accord_id])
    return render(request, "suivi/transmissions.html", {**contexte_jour(request), **navigation, "cible": cible, "cible_nature": nature, "titre": "Notes partagées", "retour_cible": retour + suffixe_jour(request) if retour and nature == "sejour" else retour,
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
    retour = reverse("suivi:cahier")
    contexte = None
    cible_nature = None
    if nature == "note":
        cible_nature = next(n for n in CIBLES if getattr(contribution, n + "_id") is not None)
        contexte = cible
        retour = reverse("suivi:notes", kwargs={"nature": cible_nature, "pk": cible.pk})
    retour += suffixe_jour(request)
    a = contexte if cible_nature == 'accompagnement' else contexte.accord.accompagnement if cible_nature == 'sejour' else None
    navigation = dossier.lire_personne(request, contexte.pk) if cible_nature == 'personne' else dossier.lire(request, a)
    if navigation:
        retour = navigation['retour_dossier']
    donnees = {**navigation, **contexte_jour(request), "contribution": contribution, "cible": contexte,
               "cible_nature": cible_nature, "retour": retour}
    form = CorrectionForm(request.POST or None, initial={"contenu": tr.lire_objet(contribution, "contenu"), "texte_attendu": contribution.contenu, "etat_attendu": transmissions.jeton(contribution)})
    if request.method == "POST" and form.is_valid():
        try:
            transmissions.rectifier(request.user, contribution, form.cleaned_data["contenu"],
                                     form.cleaned_data["motif"], texte_attendu=form.cleaned_data["texte_attendu"], etat_attendu=form.cleaned_data["etat_attendu"])
        except (ValidationError, OperationalError) as erreur:
            form.add_error(None, erreur if isinstance(erreur, ValidationError) else 'Le stockage est occupé. Votre saisie est conservée ; consultez la contribution avant de réessayer.')
            return render(request, "suivi/corriger_transmission.html", {**donnees, "form": form}, status=409)
        return redirect(retour)
    return render(request, "suivi/corriger_transmission.html", {**donnees, "form": form})
