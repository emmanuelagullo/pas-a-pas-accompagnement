"""Ne pas exposer les clés françaises ou les formulaires dans un diagnostic."""
import re
from django.views.debug import SafeExceptionReporterFilter


class FiltreSecurite(SafeExceptionReporterFilter):
    hidden_settings = re.compile(r"API|TOKEN|KEY|SECRET|PASS|SIGNATURE|HTTP_COOKIE|CLES|CLE_", re.I)

    def is_active(self, request):
        # Même le profil local fictif avec DEBUG ne doit pas afficher les champs
        # explicitement marqués sensibles par les vues d’authentification.
        return True
