"""Travail du jour : lecture filtrée par droits et distributions explicites."""
from datetime import timedelta
from collections import Counter
from django import forms
from .champs_saisie import FormulaireMetier, FormulaireModeleMetier
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import transaction, OperationalError
from django.db.models import Q
from django.forms import formset_factory
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from .models import AccordRepas, RepasDistribue, Sejour, Accompagnement, Personne, Transmission, ActionRelais, NotePartagee, Appel115
from .forms_social import ConsultationForm
from . import repas
from .retour_service import date_service, url_jour


def actifs(queryset, jour):
    return queryset.filter(debut__lte=jour).filter(Q(fin__isnull=True)|Q(fin__gt=jour))


class LigneRepas(FormulaireMetier):
    accord = forms.ModelChoiceField(AccordRepas.objects.none(), widget=forms.HiddenInput)
    beneficiaire = forms.ModelChoiceField(Personne.objects.none(), widget=forms.HiddenInput)
    quantite = forms.IntegerField(label="Repas distribués", min_value=1, max_value=32767, required=False)


LignesRepas = formset_factory(LigneRepas, extra=0, max_num=500, validate_max=True, absolute_max=500)


@require_http_methods(["GET", "POST"])
@login_required
@permission_required(("personnes.view_personne", "personnes.view_menage", "personnes.view_accompagnement"), raise_exception=True)
def jour(request):
    date_form = ConsultationForm(request.GET if request.GET else {"date": timezone.localdate()})
    date = date_form.cleaned_data["date"] if date_form.is_valid() else None
    lecture_repas = request.user.has_perms(["personnes.view_accordrepas", "personnes.view_repasdistribue"])
    ecriture = lecture_repas and request.user.has_perm("personnes.add_repasdistribue")
    if request.method == "POST":
        repas.droit(request.user, "add_repasdistribue")
        repas.droit(request.user, "view_repasdistribue")
    accords = AccordRepas.objects.none()
    lignes = []
    actifs_ids = set()
    if date and lecture_repas:
        accords = actifs(AccordRepas.objects.filter(annule_le__isnull=True).select_related("accompagnement__menage").prefetch_related("beneficiaires"), date)
        accords = accords.filter(accompagnement__debut__lte=date).filter(Q(accompagnement__fin__isnull=True)|Q(accompagnement__fin__gt=date))
        existants = {(r.accord_id,r.beneficiaire_id): r for r in RepasDistribue.objects.filter(date=date,annule_le__isnull=True,accord__in=accords).select_related("beneficiaire")}
        for accord in accords.order_by("service", "pk"):
            if accord.jours_semaine and date.weekday() not in accord.jours_semaine:continue
            for personne in accord.beneficiaires.all():
                cle = (accord.pk, personne.pk)
                actifs_ids.add(cle)
                lignes.append({"accord": accord, "personne": personne, "distribution": existants.get(cle)})
    accords_par_service = Counter((l['personne'].pk, l['accord'].service) for l in lignes)
    for ligne in lignes:
        ligne['plusieurs_accords'] = accords_par_service[(ligne['personne'].pk, ligne['accord'].service)] > 1
    # Pas de troncature silencieuse d’un lot trop grand.
    trop = len(lignes) > 500
    initial = [{"accord": l["accord"].pk, "beneficiaire": l["personne"].pk} for l in lignes] if not trop else []
    formset = LignesRepas(request.POST if request.method == "POST" else None, initial=initial, prefix="repas")
    for formulaire in formset:
        formulaire.fields["accord"].queryset = accords
        formulaire.fields["beneficiaire"].queryset = Personne.objects.filter(pk__in=[p for _,p in actifs_ids])
    erreur = None
    if request.method == "POST":
        if not date or date > timezone.localdate() or trop:
            erreur = "Choisissez une date valide, non future, et un lot de 500 lignes maximum."
        elif formset.is_valid():
            demandes = [f.cleaned_data for f in formset if f.cleaned_data.get("quantite")]
            try:
                if not demandes:
                    raise ValidationError("Renseignez au moins une quantité effectivement distribuée.")
                vus = set()
                realisations = []
                with transaction.atomic():
                    for d in sorted(demandes,key=lambda x:(str(x["accord"].accompagnement.menage_id),str(x["accord"].pk),str(x["beneficiaire"].pk))):
                        cle=(d["accord"].pk,d["beneficiaire"].pk)
                        if cle not in actifs_ids or cle in vus:
                            raise ValidationError("La sélection est invalide ou contient un doublon. Rechargez la page.")
                        vus.add(cle)
                        realisations.append(repas.distribuer(request.user,d["accord"],d["beneficiaire"],date,d["quantite"]))
            except ValidationError as exc:
                erreur = "Aucune ligne du lot n’a été enregistrée. " + " ".join(exc.messages)
            except OperationalError:
                erreur = "Écriture non confirmée. Rechargez le travail du jour avant de réessayer."
            else:
                for alerte in repas.avertissements(realisations):
                    messages.warning(request, alerte)
                messages.success(request, f"{len(demandes)} distribution(s) enregistrée(s).")
                return redirect(reverse("suivi:jour")+"?date="+date.isoformat())
    hebergements = []
    if date and request.user.has_perms(["personnes.view_accordhebergement", "personnes.view_sejour"]):
        sejours = actifs(Sejour.objects.non_annules().select_related("accord__accompagnement__menage").prefetch_related("beneficiaires", "affectations__lieu", "absences"), date)
        for s in sejours.order_by("debut", "pk"):
            lieux = [a for a in s.affectations.all() if a.debut<=date and (a.fin is None or a.fin>date)] if request.user.has_perms(["personnes.view_affectation","personnes.view_lieuhebergement"]) else None
            absences = [a for a in s.absences.all() if a.debut<=date and (a.fin is None or a.fin>date)] if request.user.has_perm("personnes.view_absence") else None
            hebergements.append({"affectation_deja_ouverte": any(a.fin is None for a in s.affectations.all()) if lieux is not None else False,
                "absence_deja_ouverte": any(a.fin is None for a in s.absences.all()) if absences is not None else False,
                "affectation_ouverte": next((a for a in (lieux or []) if a.fin is None), None),
                "absence_ouverte": next((a for a in (absences or []) if a.fin is None), None), "sejour":s,"lieux":lieux,"absences":absences,"accord_expire":s.accord.fin and s.accord.fin<=date})
    # Le cahier transversal est consultable sans exposer les notes individuelles.
    # Les dernières transmissions restent accessibles indépendamment de la date métier.
    transmissions_recentes = (list(Transmission.objects.filter(annulation__isnull=True).select_related("auteur")[:8])
                             if request.user.has_perm("personnes.view_transmission") else [])
    # Les échéances affichées sont celles des accords connus, pas des obligations
    # ou des tâches générées automatiquement. Les fins sont exclusives.
    echeances = []
    if date and request.user.has_perms(["personnes.view_accordhebergement", "personnes.view_sejour"]):
        for ligne in hebergements:
            fin = ligne["sejour"].accord.fin
            if fin and date <= fin <= date + timedelta(days=7):
                echeances.append({"menage": ligne["sejour"].accord.accompagnement.menage,
                                  "accord": ligne["sejour"].accord, "fin": fin})
    actions_relais = (ActionRelais.objects.filter(terminee_le__isnull=True,annule_le__isnull=True).select_related("auteur")
                     if request.user.has_perm("personnes.view_actionrelais") else ActionRelais.objects.none())
    aujourd_hui = timezone.localdate()
    actions_en_retard = actions_relais.filter(echeance__lt=aujourd_hui)
    actions_du_jour = actions_relais.filter(echeance=aujourd_hui)
    actions_autres = actions_relais.filter(Q(echeance__isnull=True) | Q(echeance__gt=aujourd_hui))
    return render(request,"suivi/jour.html",{"actions_relais": actions_relais, "actions_en_retard": actions_en_retard,
        "actions_du_jour": actions_du_jour, "actions_autres": actions_autres,
        "transmissions_recentes": transmissions_recentes,
        "echeances": echeances,"date_form":date_form,"date":date,"hebergements":hebergements,
        "lignes":list(zip(lignes,formset)) if not trop else [],"formset":formset,"erreur":erreur,
        "lecture_repas":lecture_repas,"ecriture":ecriture and date and date<=timezone.localdate(),"trop":trop,
        "date_service": date.isoformat() if date else ""})


class ActionRelaisForm(FormulaireModeleMetier):
    class Meta:
        model = ActionRelais
        fields = ("libelle", "echeance")
        labels = {"libelle": "Action à reprendre", "echeance": "Échéance connue (facultative)"}
        widgets = {"echeance": forms.DateInput(attrs={"type": "date"})}


@require_http_methods(["GET", "POST"])
@login_required
@permission_required("personnes.view_actionrelais", raise_exception=True)
def actions(request):
    peut_creer = request.user.has_perm("personnes.add_actionrelais")
    form = ActionRelaisForm(request.POST if request.method == "POST" else None) if peut_creer else None
    if request.method == "POST":
        if not peut_creer:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        if form.is_valid():
            from . import releve
            from django.http import Http404
            contexte={}
            for nom,model in [('transmission',Transmission),('note',NotePartagee),('appel',Appel115)]:
                valeur=request.GET.get(nom)
                if valeur:
                    try:pk=(forms.UUIDField() if nom=='appel' else forms.IntegerField(min_value=1)).clean(valeur)
                    except forms.ValidationError:raise Http404
                    contexte[nom]=get_object_or_404(model,pk=pk)
            try:action=releve.creer_action(request.user,**form.cleaned_data,**contexte)
            except (ValidationError,OperationalError) as erreur:
                form.add_error(None,erreur if isinstance(erreur,ValidationError) else 'Écriture non confirmée ; rechargez avant de réessayer.')
            else:
                if contexte.get('appel') and request.POST.get('retour')!='jour':
                    from .vues_appels115 import url,navigation
                    from urllib.parse import urlencode
                    return redirect(url(contexte['appel'],urlencode(navigation(request))))
                if request.POST.get("retour") == "jour":return redirect(url_jour(request.POST.get("date_service")))
                return redirect("suivi:actions_relais")
    ouvertes = ActionRelais.objects.filter(terminee_le__isnull=True,annule_le__isnull=True).select_related("auteur")
    aujourd_hui = timezone.localdate()
    return render(request, "suivi/actions_relais.html", {"form": form,
        "terminees":ActionRelais.objects.filter(Q(terminee_le__isnull=False)|Q(annule_le__isnull=False)).prefetch_related("revisions__auteur")[:50],
        "actions_en_retard": ouvertes.filter(echeance__lt=aujourd_hui),
        "actions_du_jour": ouvertes.filter(echeance=aujourd_hui),
        "actions_autres": ouvertes.filter(Q(echeance__isnull=True) | Q(echeance__gt=aujourd_hui)),
        "retour_jour": request.GET.get("retour") == "jour" or request.POST.get("retour") == "jour",
        "date_service": date_service(
            request.POST.get("date_service") or request.GET.get("date_service"))})


@require_http_methods(["POST"])
@login_required
@permission_required("personnes.change_actionrelais", raise_exception=True)
def terminer_action(request, pk):
    from . import releve
    action=get_object_or_404(ActionRelais,pk=pk)
    try:releve.terminer(request.user,action,request.POST.get('attendu'))
    except (ValidationError,OperationalError):
        from django.http import HttpResponse
        return HttpResponse('Action modifiée ou écriture non confirmée ; rechargez avant de réessayer.',status=409)
    if request.POST.get("retour") == "jour":
        return redirect(url_jour(request.POST.get("date_service")))
    return redirect("suivi:actions_relais")
