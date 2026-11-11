from . import dossier, bd6, departs_logement
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_safe
from .models import Accompagnement, Sejour


@never_cache
@require_safe
@login_required
@permission_required(('personnes.view_personne', 'personnes.view_menage', 'personnes.view_accompagnement'), raise_exception=True)
def resume(request, pk):
    a = get_object_or_404(Accompagnement.objects.select_related('menage').prefetch_related('beneficiaires'), pk=pk)
    from . import contacts_menage
    contact_entree = contacts_menage.a_date([a.menage], a.debut).first() if request.user.has_perms(contacts_menage.DROITS_LECTURE) else None
    from . import interventions
    interventions_entree = interventions.presentation(request.user, a, a.debut) if request.user.has_perms(interventions.DROITS_LECTURE) else []
    lecture_repas = request.user.has_perms(['personnes.view_accordrepas', 'personnes.view_repasdistribue'])
    lecture_sejours = request.user.has_perms(['personnes.view_accordhebergement', 'personnes.view_sejour'])
    return render(request, 'suivi/resume.html', {**dossier.lire(request, a), 'etat_entree': bd6.etat(request.user, a.beneficiaires.all(), a.debut),
        'commentaire': a.commentaires_dossier.first() if request.user.has_perm('personnes.view_commentairedossier') else None,
        'accompagnement': a, 'edite_le': timezone.localtime(), 'contact_entree': contact_entree, 'interventions_entree': interventions_entree,
        'information': a.informations.select_related('auteur').first() if request.user.has_perm('personnes.view_informationsaccompagnement') else None,
        'accords_repas': a.accords_repas.filter(annule_le__isnull=True).prefetch_related('beneficiaires') if lecture_repas else [],
        'sejours': Sejour.objects.non_annules().filter(accord__accompagnement=a).select_related('accord').prefetch_related(
            'beneficiaires', 'affectations__lieu', 'absences') if lecture_sejours else [],
        'departs_logement': departs_logement.par_prise(request.user, [a.pk], timezone.localdate()).get(a.pk, ()),
        'lecture_repas': lecture_repas, 'lecture_sejours': lecture_sejours})


@never_cache
@require_http_methods(['GET', 'HEAD', 'POST'])
@login_required
def ahi(request, pk):
    from django.core.exceptions import PermissionDenied, ValidationError
    from django.http import Http404
    from django.shortcuts import redirect
    from django.urls import reverse
    from . import fiche_ahi, informations_suivi, textes_riches
    from .forms_ahi import ReleveAHIForm

    a = get_object_or_404(Accompagnement.objects.select_related('menage').prefetch_related('beneficiaires'), pk=pk)
    if not fiche_ahi.disponible(request.user, a):
        raise Http404
    navigation = dossier.lire(request, a)
    retour = navigation.get('retour_dossier') or reverse('dossiers:prise', args=['menage', a.menage_id, a.pk])
    contexte = fiche_ahi.preparer(request.user, a)
    precedente = contexte['informations']
    edition = request.method == 'POST' or request.GET.get('modifier') == '1'
    peut_modifier = request.user.has_perm('personnes.add_informationsaccompagnement')
    form = None
    if edition:
        if not peut_modifier:
            raise PermissionDenied
        form = ReleveAHIForm(
            request.POST if request.method == 'POST' else None,
            adultes=contexte['adultes'], reference=contexte['reference'], sortie=contexte['sortie'],
            releve=contexte['releve'], attendu=informations_suivi.jeton(a, precedente),
        )
        if request.method == 'POST' and form.is_valid():
            donnees = {champ: getattr(precedente, champ, '') for champ in informations_suivi.CHAMPS}
            if precedente:
                for champ in ('objectifs_courts', 'objectifs_longs'):
                    donnees[champ] = textes_riches.lire_objet(precedente, champ)
            try:
                informations_suivi.enregistrer(request.user, a, form.cleaned_data['attendu'], '',
                                               releve_ahi=form.releve(), **donnees)
            except ValidationError as erreur:
                form.add_error(None, erreur)
            else:
                parametres = request.GET.copy()
                parametres.pop('modifier', None)
                return redirect(request.path + ('?' + parametres.urlencode() if parametres else ''))
    return render(request, 'suivi/fiche_ahi.html', {
        'prise': a, 'retour': retour, 'form': form, 'peut_modifier': peut_modifier,
        'parametres': request.GET.urlencode(), **contexte,
    })
