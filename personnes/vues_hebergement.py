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
from .retour_service import url_jour, date_service, contexte_jour
from . import dossier
from datetime import date


def jour_hebergement(request, accompagnement=None):
    retour = request.POST.get('retour') or request.GET.get('retour')
    valeur = date_service(request.POST.get('date_service') or request.GET.get('date_service')) if retour == 'jour' else ''
    if not valeur:
        valeur = dossier.lire(request, accompagnement).get('dossier_valeurs', {}).get('date_service', '')
    return date.fromisoformat(valeur) if valeur else timezone.localdate()


def retour_hebergement(request, accord_id):
    if (request.POST.get("retour") or request.GET.get("retour")) == "jour" and request.user.has_perm("personnes.view_sejour"):
        return url_jour(request.POST.get("date_service") or request.GET.get("date_service"))
    return reverse("suivi:accord_hebergement", args=[accord_id])


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
    return traiter_hebergement(request, form, "Accorder un hébergement", lambda **d:h.accorder(request.user,a,**d), a.menage, accompagnement=a, retour=lambda accord: reverse("suivi:accord_hebergement", args=[accord.pk]))


@require_safe
@login_required
def detail(request, pk):
    h.droit(request.user, "view_sejour")
    accord = get_object_or_404(AccordHebergement.objects.select_related("accompagnement__menage"),pk=pk)
    from .hebergement_collectif import ACTIONS
    actions_collectives = any(request.user.has_perms(["personnes." + d for d in droits]) for _, droits in ACTIONS.values())
    return render(request,"hebergement/detail.html", {**contexte_jour(request), **dossier.lire(request, accord.accompagnement), "accord":accord, "actions_collectives": actions_collectives,
        "aujourdhui": timezone.localdate(),
        "annulation_possible": not accord.sejours.exists(),
        "evolutions": accord.evolutions.select_related("auteur") if request.user.has_perm("personnes.view_evolutionaccord") else [],
        "sejours":accord.sejours.prefetch_related("beneficiaires", "affectations__lieu", "absences").order_by("debut"),
        "operations":accord.operations.select_related("auteur") if request.user.has_perm("personnes.view_operationhebergement") else []})


@require_http_methods(["GET", "POST"])
@login_required
def admettre(request, pk):
    h.droit(request.user,"add_sejour")
    a=get_object_or_404(AccordHebergement,pk=pk)
    if a.annule_le is not None:
        from django.http import HttpResponse
        return HttpResponse('Cet accord est annulé ; aucune nouvelle réalisation ne peut lui être rattachée.', status=409)
    return traiter_hebergement(request,AdmissionForm(request.POST or None,beneficiaires=a.beneficiaires.all(),
        initial={"debut": a.debut if a.fin and timezone.localdate() >= a.fin else max(a.debut, timezone.localdate()),
                 "beneficiaires": list(a.beneficiaires.values_list("pk", flat=True))}),"Enregistrer une admission — un séjour distinct par personne sélectionnée",lambda **d:h.admettre_individuellement(request.user,a,**d),a.accompagnement.menage, accompagnement=a.accompagnement, retour=reverse("suivi:accord_hebergement", args=[a.pk]))


@require_http_methods(["GET", "POST"])
@login_required
def periode(request, pk, absence=False):
    h.droit(request.user,"add_absence" if absence else "add_affectation")
    if not absence: h.exiger(request.user,"view_lieuhebergement")
    s=get_object_or_404(Sejour,pk=pk)
    form=(PeriodeForm if absence else AffectationForm)(request.POST or None,
        initial={"debut": max(s.debut, jour_hebergement(request, s.accord.accompagnement))})
    return traiter_hebergement(request,form,"Enregistrer une absence de tous les bénéficiaires" if absence else "Affecter tous les bénéficiaires à un lieu",lambda **d:h.ajouter_periode(request.user,s,absence=absence,**d),s.accord.accompagnement.menage, retour=retour_hebergement(request, s.accord_id), sejour=s)


@require_http_methods(["GET", "POST"])
@login_required
def terminer(request, pk, nature):
    h.droit(request.user,"change_"+nature)
    modele={"sejour":Sejour,"affectation":Affectation,"absence":Absence}[nature]
    objet=get_object_or_404(modele,pk=pk)
    s=objet if nature=="sejour" else objet.sejour
    action=h.sortir if nature=="sejour" else h.terminer_periode
    # La fin est exclue : proposer la date consultée (ou aujourd’hui)
    # seulement si elle suit le début. Une clôture le jour du début est invalide.
    debut = objet.debut
    jour = jour_hebergement(request, s.accord.accompagnement)
    initial = {"fin": jour} if debut < jour else {}
    return traiter_hebergement(request,ClotureForm(request.POST or None, initial=initial),"Enregistrer la sortie" if nature=="sejour" else "Enregistrer le retour d’absence" if nature=="absence" else "Clôturer l’affectation",lambda **d:action(request.user,objet,**d),s.accord.accompagnement.menage, retour=retour_hebergement(request, s.accord_id), sejour=s)


@require_http_methods(["GET", "POST"])
@login_required
def lieu(request):
    h.droit(request.user,"add_lieuhebergement")
    h.exiger(request.user,"view_lieuhebergement")
    from .vues_suivi import _uuid_valide
    identifiant = request.GET.get('accord', '')
    accord = get_object_or_404(AccordHebergement, pk=identifiant) if _uuid_valide(identifiant) else None
    retour = reverse('suivi:accord_hebergement', args=[accord.pk]) if accord else reverse('suivi:liste')
    return traiter_hebergement(request, LieuForm(request.POST if request.method == 'POST' else None),
        'Créer un lieu d’hébergement', lambda **d: h.creer_lieu(request.user, **d), accompagnement=accord.accompagnement if accord else None, retour=retour)



@require_http_methods(["GET", "POST"])
@login_required
def changer_lieu(request, pk):
    from .corrections import jeton
    from .forms_hebergement import ChangementLieuForm
    h.droit(request.user, "change_affectation")
    h.exiger(request.user, "add_affectation", "view_affectation", "view_lieuhebergement")
    objet = get_object_or_404(Affectation.objects.select_related("sejour__accord__accompagnement"), pk=pk)
    form = ChangementLieuForm(request.POST or None, initial={"debut": jour_hebergement(request, objet.sejour.accord.accompagnement), "attendu": jeton(objet)})
    return traiter_hebergement(request, form, "Changer de lieu pour tous les bénéficiaires du séjour",
        lambda **d: h.changer_lieu(request.user, objet, **d), objet.sejour.accord.accompagnement.menage,
        retour=retour_hebergement(request, objet.sejour.accord_id), sejour=objet.sejour)
