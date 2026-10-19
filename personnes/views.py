from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_safe
from .forms import PersonneForm
from .models import Personne


@require_safe
@login_required
@permission_required("personnes.view_personne", raise_exception=True)
def liste(request):
    page = Paginator(Personne.objects.all(), 25).get_page(request.GET.get("page"))
    return render(request, "personnes/liste.html", {"page_obj": page})


@require_http_methods(["GET", "POST"])
@login_required
@permission_required(("personnes.add_personne", "personnes.view_personne"), raise_exception=True)
def creer(request):
    formulaire = PersonneForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and formulaire.is_valid():
        personne = formulaire.save(commit=False)
        personne.cree_par = request.user
        personne.save()
        return redirect("personnes:detail", pk=personne.pk)
    return render(request, "personnes/creer.html", {"form": formulaire})


@require_safe
@login_required
@permission_required("personnes.view_personne", raise_exception=True)
def detail(request, pk):
    personne = get_object_or_404(Personne, pk=pk)
    return render(request, "personnes/detail.html", {"personne": personne})


@never_cache
@require_safe
@login_required
@permission_required('personnes.view_personne', raise_exception=True)
def fiche_pdf(request, pk):
    from django.conf import settings
    from django.http import HttpResponse
    from .pdf import produire
    personne = get_object_or_404(Personne, pk=pk)
    try:
        contenu = produire(personne, navigateur=getattr(settings, 'MODE_PWA', False))
    except ValueError:
        return HttpResponse('La fiche ne peut pas être générée avec les caractères présents.', status=422)
    response = HttpResponse(contenu, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="fiche-personne-{personne.pk}.pdf"'
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
