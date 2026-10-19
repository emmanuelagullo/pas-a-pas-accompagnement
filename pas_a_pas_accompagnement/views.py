from django.contrib.auth.views import redirect_to_login
from django.db import connection
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from personnes.installation import disponible
from django.views.decorators.http import require_safe


@require_safe
def accueil(request):
    if disponible():
        return redirect("installation_locale")
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    return render(request, "accueil.html")


@require_safe
def health(request):
    """Contrôle HTTP et base ; ne révèle ni chemins, ni compte, ni contenu."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "indisponible"}, status=503)
    import os, re
    result = {"status": "ok"}
    revision = os.environ.get("ACCOMPAGNEMENT_REVISION", "")
    if re.fullmatch(r"[a-f0-9]{40}", revision):
        result["commit"] = revision
    return JsonResponse(result)
