from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.http import Http404
from django.shortcuts import get_object_or_404,render
from django.utils import timezone
from django.views.decorators.http import require_safe,require_http_methods
from .models import Accompagnement,SituationSociale
from .forms_social import SituationForm,CorrectionForm,EvenementForm,BilanForm,ConsultationForm
from .vues_hebergement import traiter_hebergement
from . import social


@require_safe
@login_required
def detail(request,pk):
    social.droit(request.user,"view_situationsociale")
    a=get_object_or_404(Accompagnement,pk=pk)
    jour=timezone.localdate()
    form=ConsultationForm(request.GET if request.GET else None,initial={"date":jour})
    if request.GET:
        jour=form.cleaned_data["date"] if form.is_valid() else None
    valeurs=social.etat_date(a,jour) if jour else []
    histoire=[]
    for s in a.situations_sociales.select_related("beneficiaire","cree_par"):
        histoire.append({"date":s.debut,"enregistre":s.cree_le,"type":"Situation","objet":s})
    if request.user.has_perm("personnes.view_evenementsocial"):
        for e in a.evenements_sociaux.select_related("beneficiaire","cree_par"):
            histoire.append({"date":e.date_effet,"enregistre":e.cree_le,"type":"Événement","objet":e})
    if request.user.has_perm("personnes.view_bilansocial"):
        for b in a.bilans_sociaux.select_related("cree_par"):
            histoire.append({"date":b.date_effet,"enregistre":b.cree_le,"type":"Bilan","objet":b})
    if request.user.has_perms(["personnes.view_accordrepas", "personnes.view_repasdistribue"]):
        from .models import RepasDistribue
        for repas in RepasDistribue.objects.filter(accord__accompagnement=a).select_related("beneficiaire", "cree_par", "accord"):
            histoire.append({"date":repas.date,"enregistre":repas.cree_le,"type":"Repas","objet":repas})
    if request.user.has_perms(["personnes.view_accordhebergement", "personnes.view_sejour"]):
        from .models import Sejour
        for sejour in Sejour.objects.filter(accord__accompagnement=a).select_related("cree_par").prefetch_related("beneficiaires"):
            histoire.append({"date":sejour.debut,"enregistre":sejour.cree_le,"type":"Séjour","objet":sejour})
    histoire.sort(key=lambda x:(x["date"],x["enregistre"]))
    return render(request,"social/detail.html",{"accompagnement":a,"form":form,"valeurs":valeurs,"histoire":histoire,
        "dimensions":SituationSociale.DIMENSIONS,"jour":jour,
        "operations":a.operations_sociales.select_related("auteur") if request.user.has_perm("personnes.view_operationsociale") else []})


@require_http_methods(["GET","POST"])
@login_required
def renseigner(request,pk,dimension):
    social.droit(request.user,"add_situationsociale");social.droit(request.user,"view_situationsociale")
    if dimension not in SituationSociale.VALEURS: raise Http404
    a=get_object_or_404(Accompagnement,pk=pk)
    form=SituationForm(request.POST or None,accompagnement=a,dimension=dimension)
    return traiter_hebergement(request,form,"Renseigner : "+dict(SituationSociale.DIMENSIONS)[dimension],lambda **d:social.renseigner(request.user,a,dimension=dimension,**d),a.menage, retour=reverse("suivi:social", args=[a.pk]))


@require_http_methods(["GET","POST"])
@login_required
def corriger(request,pk):
    social.droit(request.user,"change_situationsociale");social.droit(request.user,"view_situationsociale")
    s=get_object_or_404(SituationSociale.objects.select_related("accompagnement__menage"),pk=pk)
    form=CorrectionForm(request.POST or None,dimension=s.dimension)
    return traiter_hebergement(request,form,"Corriger une valeur sans changer sa date",lambda **d:social.corriger(request.user,s,**d),s.accompagnement.menage, retour=reverse("suivi:social", args=[s.accompagnement_id]))


@require_http_methods(["GET","POST"])
@login_required
def ecrire(request,pk,nature):
    social.droit(request.user,"add_"+("evenementsocial" if nature=="evenement" else "bilansocial"))
    social.droit(request.user,"view_"+("evenementsocial" if nature=="evenement" else "bilansocial"))
    a=get_object_or_404(Accompagnement,pk=pk)
    form=EvenementForm(request.POST or None,accompagnement=a) if nature=="evenement" else BilanForm(request.POST or None)
    action=social.evenement if nature=="evenement" else social.bilan
    return traiter_hebergement(request,form,"Enregistrer un événement" if nature=="evenement" else "Enregistrer un bilan court",lambda **d:action(request.user,a,**d),a.menage, retour=reverse("suivi:social", args=[a.pk]))
