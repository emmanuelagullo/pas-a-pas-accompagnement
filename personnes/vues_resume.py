from . import dossier
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe
from .models import Accompagnement, Sejour


@never_cache
@require_safe
@login_required
@permission_required(('personnes.view_personne', 'personnes.view_menage', 'personnes.view_accompagnement'), raise_exception=True)
def resume(request, pk):
    a = get_object_or_404(Accompagnement.objects.select_related('menage').prefetch_related('beneficiaires'), pk=pk)
    lecture_repas = request.user.has_perms(['personnes.view_accordrepas', 'personnes.view_repasdistribue'])
    lecture_sejours = request.user.has_perms(['personnes.view_accordhebergement', 'personnes.view_sejour'])
    return render(request, 'suivi/resume.html', {**dossier.lire(request, a), 'accompagnement': a, 'edite_le': timezone.localtime(),
        'information': a.informations.select_related('auteur').first() if request.user.has_perm('personnes.view_informationsaccompagnement') else None,
        'accords_repas': a.accords_repas.filter(annule_le__isnull=True).prefetch_related('beneficiaires') if lecture_repas else [],
        'sejours': Sejour.objects.filter(accord__accompagnement=a).select_related('accord').prefetch_related(
            'beneficiaires', 'affectations__lieu', 'absences') if lecture_sejours else [],
        'lecture_repas': lecture_repas, 'lecture_sejours': lecture_sejours})
