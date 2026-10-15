from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_safe


@require_safe
@login_required
def accueil(request):
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
    return JsonResponse({"status": "ok"})
