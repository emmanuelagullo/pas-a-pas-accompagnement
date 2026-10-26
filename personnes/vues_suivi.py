import uuid
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_safe
from .models import Personne, Menage, Appartenance, Accompagnement, CorrectionPeriode
from .forms_suivi import MenageForm, AppartenanceForm, AccompagnementForm, ClotureForm
from . import suivi
from .retour_service import date_service
from . import dossier


@require_safe
@login_required
@permission_required(("personnes.view_menage", "personnes.view_personne"), raise_exception=True)
def liste(request):
    identifiant = request.GET.get("personne", "")
    personne = (Personne.objects.filter(pk=identifiant).first() if _uuid_valide(identifiant) else None)
    recherche = request.GET.get("q", "").strip()
    menages = Menage.objects.all()
    for terme in recherche.split():
        menages = menages.filter(Q(libelle__icontains=terme) |
            Q(appartenances__personne__designation__icontains=terme) |
            Q(appartenances__personne__prenom__icontains=terme))
    page = Paginator(menages.distinct().order_by("libelle", "pk"), 25).get_page(request.GET.get("page"))
    return render(request, "suivi/liste.html", {
        "menages": page, "page_obj": page, "recherche": recherche,
        "personne_a_rattacher": personne,
    })


@require_safe
@login_required
@permission_required(("personnes.view_menage", "personnes.view_personne"), raise_exception=True)
def detail(request, pk):
    menage = get_object_or_404(Menage, pk=pk)
    return render(request, "suivi/detail.html", {"recherche_dossier": request.GET.get("q", "")[:160], "page_dossier": request.GET.get("page", "1")[:8], "menage": menage,
        "corrections_appartenances": CorrectionPeriode.objects.filter(menage=menage, nature="appartenance").select_related("auteur") if request.user.has_perm("personnes.view_correctionperiode") else [],
        "appartenances": menage.appartenances.select_related("personne").order_by("debut", "pk"),
        "accompagnements": menage.accompagnements.prefetch_related("beneficiaires") if request.user.has_perm("personnes.view_accompagnement") else [],
        "evenements": menage.evenements.select_related("auteur") if request.user.has_perm("personnes.view_evenementsuivi") else []})


def traiter(request, formulaire, titre, action, menage=None, retour=None, sejour=None, accompagnement=None):
    if accompagnement is None and sejour is not None:
        accompagnement = sejour.accord.accompagnement
    navigation = dossier.lire(request, accompagnement)
    if request.method == "POST" and not getattr(formulaire,"preparation_seule",False) and formulaire.is_valid():
        try:
            resultat = action(**formulaire.cleaned_data)
        except ValidationError as erreur:
            formulaire.add_error(None, " ".join(erreur.messages))
        else:
            if request.headers.get('X-Condition-Form') == '1':
                from django.http import JsonResponse
                return JsonResponse({'enregistre': True})
            messages.success(request, "Enregistrement effectué.")
            if navigation:
                return redirect(navigation["retour_dossier"])
            if retour:
                return redirect(retour(resultat) if callable(retour) else retour)
            return redirect("suivi:detail", pk=menage.pk if menage else resultat.pk)
    if request.headers.get('X-Condition-Form') == '1':
        return render(request, 'dossiers/_condition_form.html', {
            'form': formulaire, 'titre': titre, 'objet': accompagnement or menage,
            'action_formulaire': request.get_full_path()})
    return render(request, "suivi/form.html", {**navigation, "accompagnement_cible": accompagnement, "form": formulaire, "titre": titre, "menage": menage, "sejour": sejour, "retour": navigation.get("retour_dossier") or (retour if isinstance(retour, str) else None),
        "retour_jour": (request.POST.get("retour") or request.GET.get("retour")) == "jour",
        "date_service": date_service(request.POST.get("date_service") or request.GET.get("date_service"))})


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
    return traiter(request, ClotureForm(request.POST or None), "Clôturer la période", lambda **d: suivi.clore(request.user, objet, **d), objet.menage, accompagnement=objet if type_objet == "accompagnement" else None, retour=reverse("suivi:accompagnement", args=[objet.pk]) if type_objet == "accompagnement" else None)


@require_safe
@login_required
@permission_required(("personnes.view_personne", "personnes.view_menage", "personnes.view_accompagnement"), raise_exception=True)
def accompagnement(request, pk):
    a = get_object_or_404(Accompagnement.objects.select_related("menage").prefetch_related("beneficiaires"), pk=pk)
    from .lecture_dossier import contexte
    return render(request, "suivi/accompagnement.html", contexte(request, a))
