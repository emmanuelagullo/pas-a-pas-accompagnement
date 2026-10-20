"""Outils du propriétaire du programme, comme la coque PWA et les commandes CLI."""
from pathlib import Path
import shutil
import tempfile

from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from pas_communs.paquets import creer_sauvegarde, lire_resultat
from .paquets import PROFIL, verifier, neutraliser_copie, restauration


@never_cache
@require_http_methods(["GET", "POST"])
def copies(request):
    # Le serveur et la PWA n'exposent jamais cet outil de fichiers natifs.
    if not getattr(settings, "OUTILS_COPIES_BUREAU", False):
        raise Http404
    paquet = Path(settings.LOCAL_DIR)
    if request.method == "POST" and restauration.attente() is None:
        action = request.POST.get("action")
        if action == "annuler":
            restauration.annuler()
            return redirect("copies_locales")
        if action == "sauvegarder":
            fichier = tempfile.TemporaryFile(dir=paquet.parent)
            try:
                creer_sauvegarde(paquet, fichier, profil=PROFIL)
                fichier.seek(0)
                return FileResponse(fichier, as_attachment=True,
                    filename="pas-a-pas-sauvegarde.zip", content_type="application/zip")
            except BaseException:
                fichier.close()
                raise
        if action == "confirmer":
            try:
                restauration.confirmer()
            except ValueError as erreur:
                messages.error(request, str(erreur))
            return redirect("copies_locales")
        if action == "restaurer" and restauration.preparation() is None:
            preparation = None
            try:
                source = request.FILES.get("archive")
                if source is None:
                    raise ValueError("Choisissez un ZIP de sauvegarde.")
                preparation = verifier(source, paquet.parent, paquet.name)
                neutraliser_copie(preparation.etape)
                restauration.retenir(preparation)
            except Exception as erreur:
                if preparation is not None:
                    shutil.rmtree(preparation.etape)
                messages.error(request, "Sauvegarde refusée : " + str(erreur))
            return redirect("copies_locales")
    return render(request, "copies_locales.html", {
        "preparation": restauration.preparation() or restauration.attente(),
        "confirmee": restauration.attente() is not None,
        "paquet": paquet, "resultat": lire_resultat(paquet),
    })
