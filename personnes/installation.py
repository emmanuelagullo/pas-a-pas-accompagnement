"""Premier compte local fictif : aucun rôle métier ni superutilisateur implicite."""
from django.conf import settings
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Permission
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from .demonstration import espace_metier_vide


class PremierCompteForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ["username"]
        labels = {"username": "Nom d’utilisateur"}


def disponible():
    return (getattr(settings, "MODE_LOCAL", False)
        and not get_user_model().objects.exists() and espace_metier_vide())


@sensitive_post_parameters()
@sensitive_variables()
@require_http_methods(["GET", "POST"])
def installer(request):
    if not disponible():
        raise Http404
    formulaire = PremierCompteForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and formulaire.is_valid():
        with transaction.atomic():
            # Le lanceur sérialise les requêtes et interdit deux ouvertures du paquet.
            if not disponible():
                raise Http404
            compte = formulaire.save()
            permissions = list(Permission.objects.filter(content_type__app_label="personnes",
                content_type__model="personne", codename__in=["view_personne", "add_personne"]))
            if len(permissions) != 2:
                raise RuntimeError("Les permissions du premier compte sont absentes.")
            compte.user_permissions.set(permissions)
        login(request, compte, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("personnes:liste")
    return render(request, "installation_locale.html", {"form": formulaire})
