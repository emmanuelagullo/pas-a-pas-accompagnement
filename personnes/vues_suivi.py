import uuid
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_safe
from .models import Personne, Menage, Appartenance, Accompagnement, CorrectionPeriode
from .forms_suivi import MenageForm, AppartenanceForm, AccompagnementForm, ClotureForm
from . import suivi


@require_safe
@login_required
@permission_required(("personnes.view_menage", "personnes.view_personne"), raise_exception=True)
def liste(request):
    identifiant = request.GET.get("personne", "")
    personne = (Personne.objects.filter(pk=identifiant).first() if _uuid_valide(identifiant) else None)
    return render(request, "suivi/liste.html", {
        "menages": Menage.objects.all(),
        "personne_a_rattacher": personne,
    })


@require_safe
@login_required
@permission_required(("personnes.view_menage", "personnes.view_personne"), raise_exception=True)
def detail(request, pk):
    menage = get_object_or_404(Menage, pk=pk)
    return render(request, "suivi/detail.html", {"menage": menage,
        "corrections_appartenances": CorrectionPeriode.objects.filter(menage=menage, nature="appartenance").select_related("auteur") if request.user.has_perm("personnes.view_correctionperiode") else [],
        "appartenances": menage.appartenances.select_related("personne").order_by("debut", "pk"),
        "accompagnements": menage.accompagnements.prefetch_related("beneficiaires") if request.user.has_perm("personnes.view_accompagnement") else [],
        "evenements": menage.evenements.select_related("auteur") if request.user.has_perm("personnes.view_evenementsuivi") else []})


def traiter(request, formulaire, titre, action, menage=None, retour=None):
    if request.method == "POST" and formulaire.is_valid():
        try:
            resultat = action(**formulaire.cleaned_data)
        except ValidationError as erreur:
            formulaire.add_error(None, " ".join(erreur.messages))
        else:
            messages.success(request, "Enregistrement effectué.")
            if retour:
                return redirect(retour(resultat) if callable(retour) else retour)
            return redirect("suivi:detail", pk=menage.pk if menage else resultat.pk)
    return render(request, "suivi/form.html", {"form": formulaire, "titre": titre, "menage": menage, "retour": retour if isinstance(retour, str) else None})


def _uuid_valide(valeur):
    try:
        uuid.UUID(valeur)
        return True
    except (ValueError, TypeError, AttributeError):
        return False


@require_http_methods(["GET", "POST"])
@login_required
@permission_required(("personnes.view_personne", "personnes.view_menage", "personnes.add_menage", "personnes.add_appartenance"), raise_exception=True)
def creer(request):
    initial = {}
    if request.method == "GET":
        personne = request.GET.get("personne", "")
        if _uuid_valide(personne) and Personne.objects.filter(pk=personne).exists():
            initial["personnes"] = [personne]
        initial["debut"] = timezone.localdate()
    formulaire = MenageForm(request.POST if request.method == "POST" else None, initial=initial)
    return traiter(request, formulaire, "Créer un ménage", lambda **donnees: suivi.creer_menage(request.user, **donnees))


@require_http_methods(["GET", "POST"])
@login_required
@permission_required(("personnes.view_personne", "personnes.view_menage", "personnes.add_appartenance"), raise_exception=True)
def ajouter(request, pk):
    menage = get_object_or_404(Menage, pk=pk)
    initial = {}
    if request.method == "GET":
        personne = request.GET.get("personne", "")
        if _uuid_valide(personne) and Personne.objects.filter(pk=personne).exists():
            initial["personne"] = personne
        initial["debut"] = timezone.localdate()
    return traiter(request, AppartenanceForm(request.POST or None, initial=initial), "Ajouter une appartenance", lambda **d: suivi.ajouter_appartenance(request.user, menage, **d), menage)


@require_http_methods(["GET", "POST"])
@login_required
@permission_required(("personnes.view_personne", "personnes.view_menage", "personnes.view_accompagnement", "personnes.add_accompagnement"), raise_exception=True)
def ouvrir(request, pk):
    menage = get_object_or_404(Menage, pk=pk)
    jour = timezone.localdate()
    membres = menage.appartenances.filter(debut__lte=jour).filter(Q(fin__isnull=True) | Q(fin__gt=jour)).values_list("personne_id", flat=True)
    form = AccompagnementForm(request.POST or None, initial={"debut": jour, "beneficiaires": list(membres)})
    return traiter(request, form, "Ouvrir un accompagnement — service d’essai", lambda **d: suivi.ouvrir(request.user, menage, **d), menage, retour=lambda a: reverse("suivi:accompagnement", args=[a.pk]))


@require_http_methods(["GET", "POST"])
@login_required
@permission_required(("personnes.view_personne", "personnes.view_menage"), raise_exception=True)
def clore(request, pk, type_objet, objet_pk):
    if type_objet == "accompagnement":
        suivi.exiger(request.user, "view_accompagnement", "change_accompagnement")
        modele = Accompagnement
    else:
        suivi.exiger(request.user, "change_appartenance")
        modele = Appartenance
    objet = get_object_or_404(modele, pk=objet_pk, menage_id=pk)
    return traiter(request, ClotureForm(request.POST or None), "Clôturer la période", lambda **d: suivi.clore(request.user, objet, **d), objet.menage, retour=reverse("suivi:accompagnement", args=[objet.pk]) if type_objet == "accompagnement" else None)


@require_safe
@login_required
@permission_required(("personnes.view_personne", "personnes.view_menage", "personnes.view_accompagnement"), raise_exception=True)
def accompagnement(request, pk):
    a = get_object_or_404(Accompagnement.objects.select_related("menage").prefetch_related("beneficiaires"), pk=pk)
    droits = request.user
    return render(request, "suivi/accompagnement.html", {
        "accompagnement": a,
        "accords_repas": a.accords_repas.prefetch_related("beneficiaires") if droits.has_perms(["personnes.view_accordrepas", "personnes.view_repasdistribue"]) else [],
        "accords_hebergement": a.accords_hebergement.prefetch_related("beneficiaires", "sejours") if droits.has_perms(["personnes.view_accordhebergement", "personnes.view_sejour"]) else [],
    })
