from django.contrib.auth.decorators import login_required
from django.core import signing
from django.http import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from . import frises


@never_cache
@require_POST
@login_required
def preference(request):
    try:
        d = signing.loads(request.POST.get('retour_frise'), salt=frises.SEL, max_age=86400)
        if d['compte'] != str(request.user.pk) or not d['retour'].startswith('/') or d['retour'].startswith('//'):
            raise ValueError
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        return HttpResponseBadRequest('Rechargez la page avant de changer de vue.')
    request.session[frises.SESSION] = request.POST.get('actif') == '1'
    if request.headers.get('X-Frises-Pref') == '1':
        return JsonResponse({'enregistre':True})
    return HttpResponseRedirect(d['retour'])
