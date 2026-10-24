"""Retrouver des prises en charge par mission, à une date explicite."""
import csv
from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from .champs_saisie import FormulaireMetier
from .forms_hebergement import date_champ
from .models import AffectationIntervenant, Intervenant, Partenaire, FicheIntervenant
from . import interventions
from .exports import cellule_csv


class RechercheMissionsForm(FormulaireMetier):
    date = date_champ('Missions applicables au')
    intervenant = forms.ModelChoiceField(Intervenant.objects.all(),required=False,label='Professionnel')
    organisme = forms.ModelChoiceField(Partenaire.objects.all(),required=False,label='Organisme ou service',
        help_text='Mission de l’organisme ou du professionnel rattaché à cet organisme à la date choisie.')
    role = forms.ChoiceField(label='Rôle',choices=[('','Tous les rôles'),*AffectationIntervenant.ROLES],required=False)
    q = forms.CharField(label='Nom de dossier ou bénéficiaire',max_length=160,required=False)


@never_cache
@require_safe
@login_required
@permission_required(interventions.DROITS_LECTURE,raise_exception=True)
def rechercher(request):
    from .vues_partenaires import contexte
    _, nav = contexte(request)
    selection=request.GET.copy()
    if 'date' not in selection:selection['date']=timezone.localdate().isoformat()
    form=RechercheMissionsForm(selection)
    lignes=AffectationIntervenant.objects.none();nombre_prises=0
    if form.is_valid():
        d=form.cleaned_data;jour=d['date']
        lignes=AffectationIntervenant.objects.filter(annule_le__isnull=True,debut__lte=jour,
            accompagnement__debut__lte=jour).filter(Q(fin__isnull=True)|Q(fin__gt=jour)).filter(
            Q(accompagnement__fin__isnull=True)|Q(accompagnement__fin__gt=jour))
        if d['intervenant']:lignes=lignes.filter(intervenant=d['intervenant'])
        if d['organisme']:
            profils=FicheIntervenant.objects.filter(organisme=d['organisme'],debut__lte=jour).filter(Q(fin__isnull=True)|Q(fin__gt=jour))
            lignes=lignes.filter(Q(organisme=d['organisme'])|Q(intervenant_id__in=profils.values('intervenant_id')))
        if d['role']:lignes=lignes.filter(role=d['role'])
        for mot in d['q'].split():
            lignes=lignes.filter(Q(accompagnement__menage__libelle__icontains=mot)|Q(accompagnement__beneficiaires__designation__icontains=mot)|Q(accompagnement__beneficiaires__prenom__icontains=mot))
        lignes=lignes.distinct().select_related('intervenant','organisme','accompagnement__menage').order_by('accompagnement_id','role','pk')
        nombre_prises=lignes.values('accompagnement_id').distinct().count()
        if request.GET.get('format')=='csv':
            response=HttpResponse(content_type='text/csv; charset=utf-8')
            response['Content-Disposition']='attachment; filename="prises-par-intervenant.csv"'
            writer=csv.writer(response,delimiter=';');writer.writerow(['date_reference','prise_id','menage_id','menage','mission_id','role','professionnel_id','professionnel','organisme_id','organisme','debut_mission','fin_propre','fin_effective'])
            for x in lignes:
                fins=[v for v in (x.fin,x.accompagnement.fin) if v]
                writer.writerow([jour.isoformat(),x.accompagnement_id,x.accompagnement.menage_id,cellule_csv(x.accompagnement.menage),x.pk,x.get_role_display(),x.intervenant_id or '',cellule_csv(x.intervenant or ''),x.organisme_id or '',cellule_csv(x.organisme or ''),x.debut.isoformat(),x.fin.isoformat() if x.fin else '',min(fins).isoformat() if fins else ''])
            return response
    query=selection.copy();query.pop('format',None);query.pop('page',None)
    return render(request,'dossiers/recherche_intervenants.html',{'form':form,'page_obj':Paginator(lignes,50).get_page(request.GET.get('page')),
        **nav, 'nombre_missions':lignes.count(),'nombre_prises':nombre_prises,'query_rapport':query.urlencode()})
