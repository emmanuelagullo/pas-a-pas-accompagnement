from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_safe
from .models import Menage, Appartenance, Accompagnement
from .forms_suivi import MenageForm, AppartenanceForm, AccompagnementForm, ClotureForm
from . import suivi


@require_safe
@login_required
@permission_required(("personnes.view_menage", "personnes.view_personne"), raise_exception=True)
def liste(request):
    return render(request, "suivi/liste.html", {"menages": Menage.objects.all()})


@require_safe
@login_required
@permission_required(("personnes.view_menage", "personnes.view_personne"), raise_exception=True)
def detail(request, pk):
    menage = get_object_or_404(Menage, pk=pk)
    return render(request, "suivi/detail.html", {"menage": menage,
        "appartenances": menage.appartenances.select_related("personne").order_by("debut", "pk"),
        "accompagnements": menage.accompagnements.prefetch_related("beneficiaires") if request.user.has_perm("personnes.view_accompagnement") else [],
        "evenements": menage.evenements.select_related("auteur") if request.user.has_perm("personnes.view_evenementsuivi") else []})


def traiter(request, formulaire, titre, action, menage=None):
    if request.method == "POST" and formulaire.is_valid():
        try:
            resultat = action(**formulaire.cleaned_data)
        except ValidationError as erreur:
            formulaire.add_error(None, " ".join(erreur.messages))
        else:
            return redirect("suivi:detail", pk=menage.pk if menage else resultat.pk)
    return render(request, "suivi/form.html", {"form": formulaire, "titre": titre, "menage": menage})


@require_http_methods(["GET", "POST"])
@login_required
@permission_required(("personnes.view_personne", "personnes.view_menage", "personnes.add_menage", "personnes.add_appartenance"), raise_exception=True)
def creer(request):
    return traiter(request, MenageForm(request.POST or None), "Créer un ménage", lambda **donnees: suivi.creer_menage(request.user, **donnees))


@require_http_methods(["GET", "POST"])
@login_required
@permission_required(("personnes.view_personne", "personnes.view_menage", "personnes.add_appartenance"), raise_exception=True)
def ajouter(request, pk):
    menage = get_object_or_404(Menage, pk=pk)
    return traiter(request, AppartenanceForm(request.POST or None), "Ajouter une appartenance", lambda **d: suivi.ajouter_appartenance(request.user, menage, **d), menage)


@require_http_methods(["GET", "POST"])
@login_required
@permission_required(("personnes.view_personne", "personnes.view_menage", "personnes.view_accompagnement", "personnes.add_accompagnement"), raise_exception=True)
def ouvrir(request, pk):
    menage = get_object_or_404(Menage, pk=pk)
    jour = timezone.localdate()
    membres = menage.appartenances.filter(debut__lte=jour).filter(Q(fin__isnull=True) | Q(fin__gt=jour)).values_list("personne_id", flat=True)
    form = AccompagnementForm(request.POST or None, initial={"debut": jour, "beneficiaires": list(membres)})
    return traiter(request, form, "Ouvrir un accompagnement — service d’essai", lambda **d: suivi.ouvrir(request.user, menage, **d), menage)


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
    return traiter(request, ClotureForm(request.POST or None), "Clôturer la période", lambda **d: suivi.clore(request.user, objet, **d), objet.menage)
