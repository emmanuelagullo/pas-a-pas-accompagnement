"""Fenêtres fixes persistées, compteurs atomiques partagés entre processus."""
from datetime import datetime, timezone
import logging
import unicodedata
from django.conf import settings
from django.db import DatabaseError
from django.db.models import F
from django.utils.crypto import salted_hmac
from .models import LimiteAuthentification

logger = logging.getLogger("identites.securite")


def autoriser(request, usage, identifiant):
    import time
    duree = settings.AUTH_FENETRE_SECONDES
    fenetre = int(time.time()) // duree
    # Aucun X-Forwarded-For : profil actuel sans chaîne de proxy approuvée.
    ip = request.META.get("REMOTE_ADDR", "inconnue")
    limites = [("compte", unicodedata.normalize("NFKC", str(identifiant)).casefold(), settings.AUTH_TENTATIVES_COMPTE),
               ("ip", ip, settings.AUTH_TENTATIVES_IP)]
    permis = True
    try:
        for type_cle, valeur, plafond in limites:
            cle = salted_hmac("accompagnement.auth.limite",
                f"{usage}:{type_cle}:{valeur}:{fenetre}", algorithm="sha256").hexdigest()
            ligne, _ = LimiteAuthentification.objects.get_or_create(cle=cle, defaults={
                "expire_le": datetime.fromtimestamp((fenetre+1)*duree, timezone.utc)})
            consomme = LimiteAuthentification.objects.filter(pk=ligne.pk,
                tentatives__lt=plafond).update(tentatives=F("tentatives")+1)
            permis = bool(consomme) and permis
    except DatabaseError:
        logger.warning("auth.limite_indisponible")
        return False
    if not permis:
        logger.warning("auth.limite_atteinte usage=%s", usage)
    return permis
