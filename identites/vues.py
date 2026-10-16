import logging
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import DatabaseError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from pas_communs.authentification import sessions, totp
from . import double_facteur as facteur
from .configuration import disponible, service_indisponible
from .limites import autoriser

logger = logging.getLogger("identites.securite")
ATTENTE = "accompagnement_2fa_attente"
PREUVE = "accompagnement_2fa_revision"


def indisponible():
    return HttpResponse("La sécurité du compte est indisponible. Contactez la personne qui administre cet essai.", status=503)


def limite():
    reponse = HttpResponse("Trop de tentatives. Réessayez après la fin de la période de blocage.", status=429)
    reponse["Retry-After"] = str(settings.AUTH_FENETRE_SECONDES)
    return reponse


@method_decorator(never_cache, name="dispatch")
class Connexion(LoginView):
    redirect_authenticated_user = True
    template_name = "connexion.html"

    def dispatch(self, request, *args, **kwargs):
        if service_indisponible():
            return indisponible()
        if request.method == "GET":
            request.session.pop(ATTENTE, None)
        if request.method == "POST" and not autoriser(request, "connexion", request.POST.get("username", "")):
            return limite()
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        utilisateur = form.get_user()
        ligne = facteur.compte(utilisateur)
        if ligne and (ligne.inscrit or ligne.a_reinscrire) and not disponible():
            return indisponible()
        if ligne and ligne.inscrit:
            sessions.commencer_attente(self.request.session, utilisateur, cle=ATTENTE)
            self.request.session[ATTENTE].update(revision=str(ligne.revision), suivant=self.get_success_url())
            return redirect("connexion_verification")
        reponse = super().form_valid(form)
        logger.info("auth.connexion compte=%s", utilisateur.pk)
        return redirect("securite_compte") if facteur.requis(utilisateur) else reponse

    def form_invalid(self, form):
        logger.warning("auth.connexion_refusee")
        return super().form_invalid(form)


class CodeForm(forms.Form):
    code = forms.CharField(label="Code du téléphone ou code de secours", max_length=64,
        widget=forms.PasswordInput(attrs={"autocomplete":"one-time-code"}))


@sensitive_post_parameters()
@sensitive_variables()
@never_cache
@require_http_methods(["GET", "POST"])
def verification(request):
    utilisateur, attente = sessions.compte_en_attente(request.session, cle=ATTENTE)
    if not utilisateur:
        return redirect("connexion")
    if not disponible():
        request.session.pop(ATTENTE, None)
        return indisponible()
    form = CodeForm(request.POST if request.method == "POST" else None)
    if request.method == "POST":
        if not autoriser(request, "verification", utilisateur.pk):
            request.session.pop(ATTENTE, None)
            return limite()
        if form.is_valid():
            try:
                preuve = facteur.verifier(utilisateur, form.cleaned_data["code"], revision=attente.get("revision", ""))
            except DatabaseError:
                return indisponible()
            if preuve:
                suivant = attente.get("suivant")
                # Revalider la destination en plus du contrôle LoginView initial.
                from django.utils.http import url_has_allowed_host_and_scheme
                if not url_has_allowed_host_and_scheme(suivant, {request.get_host()}, require_https=request.is_secure()):
                    suivant = None
                request.session.pop(ATTENTE, None)
                login(request, utilisateur, backend=attente["backend"])
                request.session[PREUVE] = preuve.revision
                logger.info("auth.connexion_2fa compte=%s secours=%s", utilisateur.pk, preuve.secours)
                if preuve.secours:
                    messages.warning(request, "Un code de secours a été utilisé. Remplacez votre téléphone depuis la sécurité du compte si nécessaire.")
                return redirect(suivant or "accueil")
            logger.warning("auth.code_refuse compte=%s", utilisateur.pk)
            form.add_error("code", "Code incorrect ou expiré.")
    return render(request, "identites/verification.html", {"form":form})


class SecuriteForm(forms.Form):
    action = forms.ChoiceField(choices=[(a,a) for a in ("commencer", "confirmer", "regenerer", "remplacer", "retirer")], widget=forms.HiddenInput)
    mot_de_passe = forms.CharField(label="Mot de passe actuel", strip=False, max_length=1024,
        widget=forms.PasswordInput(attrs={"autocomplete":"current-password"}))
    code = forms.CharField(label="Code du téléphone ou code de secours", required=False, max_length=64,
        widget=forms.PasswordInput(attrs={"autocomplete":"one-time-code"}))


def _sessions_apres_changement(request, revision):
    sessions.fermer_sessions_compte(request.user)
    request.session.cycle_key()
    request.session[PREUVE] = revision


@sensitive_post_parameters()
@sensitive_variables()
@never_cache
@login_required
@require_http_methods(["GET", "POST"])
def securite(request):
    ligne = facteur.compte(request.user)
    contexte = {"disponible":disponible(), "inscrit":bool(ligne and ligne.inscrit),
        "obligatoire":facteur.requis(request.user),
        "peut_retirer":settings.DOUBLE_FACTEUR_POLITIQUE != "obligatoire"}
    form = SecuriteForm(initial={"action":"commencer" if not contexte["inscrit"] else "regenerer"})
    if request.method == "POST":
        if not disponible():
            return indisponible()
        if not autoriser(request, "gestion", request.user.pk):
            return limite()
        form = SecuriteForm(request.POST)
        if form.is_valid():
            utilisateur = authenticate(request, username=request.user.get_username(), password=form.cleaned_data["mot_de_passe"])
            if utilisateur is None or utilisateur.pk != request.user.pk:
                form.add_error("mot_de_passe", "Mot de passe incorrect.")
            else:
                action, code = form.cleaned_data["action"], form.cleaned_data["code"]
                try:
                    if action == "commencer":
                        ligne = facteur.commencer(request.user)
                        cle = totp.dechiffrer(ligne.cle_chiffree, cles=settings.DOUBLE_FACTEUR_CLES)
                        contexte.update(qr=totp.qr_svg(totp.uri_otpauth(request.user.get_username(), cle,
                            emetteur=settings.DOUBLE_FACTEUR_EMETTEUR)), cle=totp.cle_en_base32(cle))
                        form = SecuriteForm(initial={"action":"confirmer"})
                    elif action == "confirmer":
                        resultat = facteur.confirmer(request.user, code)
                        if not resultat:
                            raise ValidationError("Code incorrect ou expiré. Recommencez l’activation si nécessaire.")
                        revision, codes = resultat
                        _sessions_apres_changement(request, revision)
                        logger.info("auth.activation_2fa compte=%s", request.user.pk)
                        return render(request, "identites/secours.html", {"codes":codes})
                    else:
                        if action == "retirer" and settings.DOUBLE_FACTEUR_POLITIQUE == "obligatoire":
                            raise ValidationError("Le second facteur est obligatoire pour cet espace.")
                        preuve = facteur.verifier(request.user, code)
                        if not preuve:
                            raise ValidationError("Code incorrect ou expiré.")
                        if action == "regenerer":
                            revision, codes = facteur.regenerer(request.user, preuve)
                            _sessions_apres_changement(request, revision)
                            logger.info("auth.secours_regeneres compte=%s", request.user.pk)
                            return render(request, "identites/secours.html", {"codes":codes})
                        revision = facteur.reinitialiser(request.user, preuve=preuve, a_reinscrire=action == "remplacer")
                        _sessions_apres_changement(request, revision)
                        logger.info("auth.%s_2fa compte=%s", action, request.user.pk)
                        messages.success(request, "Réinscrivez votre nouveau téléphone." if action == "remplacer" else "Second facteur retiré.")
                        return redirect("securite_compte")
                except ValidationError as exc:
                    form.add_error(None, exc)
                except DatabaseError:
                    return indisponible()
    contexte["form"] = form
    return render(request, "identites/securite.html", contexte)


class ChangementForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for champ in self.fields.values():
            champ.validators.append(MaxLengthValidator(1024))
            champ.widget.attrs["maxlength"] = 1024


@method_decorator(never_cache, name="dispatch")
class ChangerMotDePasse(PasswordChangeView):
    form_class = ChangementForm
    template_name = "identites/mot_de_passe.html"
    success_url = reverse_lazy("securite_compte")

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST" and request.user.is_authenticated and not autoriser(request,"gestion",request.user.pk):
            return limite()
        return super().dispatch(request,*args,**kwargs)

    def form_valid(self, form):
        reponse = super().form_valid(form)
        logger.info("auth.mot_de_passe_change compte=%s", self.request.user.pk)
        messages.success(self.request, "Mot de passe changé. Les autres sessions devront se reconnecter.")
        return reponse
