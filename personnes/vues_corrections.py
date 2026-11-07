from copy import deepcopy
from . import textes_riches as tr
from . import dossier
from django import forms
from .champs_saisie import FormulaireMetier
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_safe
from . import corrections as c
from .forms_hebergement import date_champ
from .vues_hebergement import traiter_hebergement
from .models import Accompagnement, CorrectionPeriode, RevisionTexteSocial
from .suivi import exiger


class PeriodeForm(FormulaireMetier):
    debut = date_champ('Début inclus')
    fin = date_champ('Fin non comprise',False)
    source = forms.CharField(max_length=160,required=False,label='Source de l’information')
    motif = forms.CharField(max_length=240,label='Précision sur la correction (facultative)',required=False)
    attendu = forms.CharField(widget=forms.HiddenInput)


class TexteForm(FormulaireMetier):
    date_effet = date_champ('Date d’effet')
    texte = forms.CharField(max_length=2000,widget=forms.Textarea)
    source = forms.CharField(max_length=160,required=False,label='Source de l’information')
    motif = forms.CharField(max_length=240,label='Précision sur la correction (facultative)',required=False)
    attendu = forms.CharField(widget=forms.HiddenInput)


@require_http_methods(['GET','POST'])
@login_required
def corriger(request,nature,pk):
    registre={**{nom:val[0] for nom,val in c.PERIODES.items()},**c.TEXTES}
    if nature not in registre:raise Http404
    c.droits(request.user,nature)
    objet=get_object_or_404(registre[nature],pk=pk)
    if getattr(objet, 'annule_le', None) is not None:
        from django.http import HttpResponse
        return HttpResponse('Cet accord est annulé ; ses dates restent conservées dans l’historique.', status=409)
    a=c.suivi_de(objet)
    retour=reverse('suivi:accompagnement',args=[a.pk]) if a else reverse('suivi:detail',args=[objet.menage_id])
    simple = False
    if nature in c.TEXTES:
        initial={'date_effet':objet.date_effet,'texte':objet.texte,'source':getattr(objet,'source',''),'attendu':c.jeton(objet)}
        form=TexteForm(request.POST if request.method=='POST' else None,initial=initial)
        if nature=='evenementsocial':
            form.fields['texte'].max_length=500
            form.fields['source'].required=True
            form.fields['date_effet'].help_text='Un fait de l’histoire antérieure peut précéder le début du suivi ; sa source et le motif restent requis.'
        else:
            del form.fields['source']
            form.fields['texte'] = tr.ChampTexte(label='Bilan court', max_length=2000)
            form.initial['texte'] = tr.lire_objet(objet, 'texte')
        action=lambda **d:c.texte(request.user,objet,**d)
    else:
        initial={'debut':objet.debut,'fin':objet.fin,'source':getattr(objet,'source',''),'attendu':c.jeton(objet)}
        form=PeriodeForm(request.POST if request.method=='POST' else None,initial=initial)
        if nature=='situationsociale':
            form.fields['fin'].disabled=True;form.fields['source'].required=True
        else:
            del form.fields['source']
        from acteurs.profils_collectifs import parcours_simple
        simple = nature == 'sejour' and parcours_simple(a, 'hebergement')
        if simple:
            from .vues_admission import AdmissionGuideeForm

            if objet.fin is None:
                initial['fin'] = objet.accord.fin
            initial['beneficiaires'] = list(objet.beneficiaires.values_list('pk', flat=True))
            form = AdmissionGuideeForm(
                request.POST if request.method == 'POST' else None,
                initial=initial, acteur=request.user, simple=True,
                accompagnement=a, sejour=objet, beneficiaires=(
                    a.beneficiaires.all() if request.user.has_perm('personnes.change_accordhebergement')
                    else objet.accord.beneficiaires.all()
                ),
            )
            form.fields['motif'] = deepcopy(PeriodeForm.base_fields['motif'])
            if objet.fin is None and request.user.has_perms((
                'personnes.change_sejour', 'personnes.change_affectation', 'personnes.change_absence',
            )):
                from .vues_informations import champ_destination
                destination = champ_destination(a)
                if destination is not None:
                    form.fields['destination_sortie'] = destination
        if nature == 'accordrepas':
            from .forms_repas import AccordForm

            form = AccordForm(
                request.POST if request.method == 'POST' else None,
                accompagnement=a, instance=objet, initial=initial,
            )
            form.fields['attendu'] = forms.CharField(widget=forms.HiddenInput)
            form.fields['motif'] = deepcopy(PeriodeForm.base_fields['motif'])
            for champ in ('beneficiaires', 'service', 'prestataire', 'jours_semaine'):
                form.fields[champ].disabled = True

        def action(**donnees):
            if nature == 'accordrepas':
                for champ in ('beneficiaires', 'service', 'prestataire', 'jours_semaine'):
                    donnees.pop(champ, None)
            prise_confirmee = (a.fin, a.revision_sociale) if simple and form.conflit_fin else getattr(form, "prise_confirmee", None)
            return c.periode(request.user, objet, depart_sejour=simple, prise_confirmee=prise_confirmee, **donnees)
    if nature == 'accordrepas':
        form.objet_periode = 'la période de repas'
    if request.method == 'POST' and request.headers.get('X-Verifier-Prestation') == '1':
        if nature not in ('sejour', 'accordrepas'):
            raise Http404
        if simple:
            from .vues_admission import verifier_saisie_sejour
            return verifier_saisie_sejour(request, form)
        from .validation_prestations import diagnostic
        return diagnostic(form, a, request=request if nature == "accordrepas" else None)
    def avant_enregistrement():
        if simple:
            return form.enregistrement_autorise(request.user)
        if nature == 'accordrepas':
            from .validation_prestations import preparer_resolution
            form.prise_confirmee = preparer_resolution(request, form, a)
            return not getattr(form, 'jeton_fin', None)
        return True

    form.resolution_periode = nature == 'accordrepas'
    return traiter_hebergement(request,form,'Modifier le séjour' if nature == 'sejour' else 'Corriger une saisie — '+objet._meta.verbose_name,action,c.menage_de(objet),accompagnement=a,retour=retour,
        avant_enregistrement=avant_enregistrement)


@require_safe
@login_required
def historique(request,pk):
    exiger(request.user,'view_personne','view_menage','view_accompagnement')
    a=get_object_or_404(Accompagnement.objects.select_related('menage'),pk=pk)
    periodes=[];textes=[]
    if request.user.has_perm('personnes.view_correctionperiode'):
        natures=[nom for nom in c.PERIODES if request.user.has_perm('personnes.view_'+nom)]
        periodes=a.corrections_periodes.filter(nature__in=natures).select_related('auteur')
    if request.user.has_perm('personnes.view_revisiontextesocial'):
        q=RevisionTexteSocial.objects.none()
        if request.user.has_perm('personnes.view_evenementsocial'):q=a.revisions_textes.filter(evenement__isnull=False)
        if request.user.has_perm('personnes.view_bilansocial'):q=q|a.revisions_textes.filter(bilan__isnull=False)
        textes=q.select_related('auteur').order_by('enregistre_le','pk')
    if not (request.user.has_perm('personnes.view_correctionperiode') or request.user.has_perm('personnes.view_revisiontextesocial')):
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    return render(request,'suivi/corrections.html',{**dossier.lire(request, a),'accompagnement':a,'periodes':periodes,'textes':textes})
