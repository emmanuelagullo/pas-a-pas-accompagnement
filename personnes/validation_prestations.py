"""Diagnostic de période, partagé par la saisie et les écritures métier."""
from datetime import date, timedelta
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse


def verifier_periode_prise(prise, debut, fin, *, champ_fin='fin'):
    if debut < prise.debut:
        raise ValidationError({'debut': f'Le début saisi est le {debut:%d/%m/%Y}. La prise en charge commence le {prise.debut:%d/%m/%Y}.'})
    if prise.fin and debut >= prise.fin:
        raise ValidationError({'debut': f'Le début saisi est le {debut:%d/%m/%Y}. La prise en charge se termine le {prise.fin:%d/%m/%Y} (date exclue).'})
    if prise.fin and (fin is None or fin > prise.fin):
        demande = f'La fin saisie est le {fin:%d/%m/%Y}.' if fin else 'Vous n’avez indiqué aucune date de fin.'
        raise ValidationError({champ_fin: f'{demande} La prise en charge se termine le {prise.fin:%d/%m/%Y} (date exclue).'})


def reporter_erreur(form, erreur):
    if hasattr(erreur, 'error_dict'):
        for nom, messages in erreur.message_dict.items():
            form.add_error(nom if nom in form.fields else None, messages)
    else:
        form.add_error(None, erreur)


def borne_exclue(fin, fin_incluse):
    return fin + timedelta(days=1) if fin and fin_incluse and fin < date.max else fin


def diagnostic(form, prise, champ_fin='fin', *, fin_par_defaut=None, request=None, proposer_nouvelle_prise=False, fin_incluse=False):
    form.is_valid()
    if form.cleaned_data.get('debut') and not any(nom in form.errors for nom in (champ_fin, 'duree')):
        if request is not None:
            preparer_resolution(request, form, prise, champ_fin, fin_par_defaut=fin_par_defaut,
                                proposer_nouvelle_prise=proposer_nouvelle_prise, fin_incluse=fin_incluse)
        else:
            try:
                verifier_periode_prise(prise, form.cleaned_data['debut'],
                                      borne_exclue(form.cleaned_data.get(champ_fin, fin_par_defaut), fin_incluse), champ_fin=champ_fin)
            except ValidationError as erreur:
                reporter_erreur(form, erreur)
    erreurs = {nom: list(form.errors[nom]) for nom in ('debut', champ_fin, 'arrivee', 'admission', 'duree') if nom in form.errors}
    if getattr(form, 'debut_prise_resolution', None) and 'debut' not in erreurs:
        erreurs['debut'] = [f'La prise en charge commence le {prise.debut:%d/%m/%Y}.']
    if getattr(form, 'fin_prise_resolution', None) and champ_fin in form.fields and champ_fin not in erreurs:
        erreurs[champ_fin] = [f'La prise en charge se termine le {prise.fin:%d/%m/%Y} (date exclue).']
    reponse = {'erreurs': erreurs}
    if request is not None:
        from django.template.loader import render_to_string
        reponse['commandes'] = render_to_string(
            'dossiers/_prestation_validation.html', {'form': form, 'libelle_validation': 'Enregistrer'},
        )
    return JsonResponse(reponse)


def depassements(prise, debut, fin):
    return debut < prise.debut, bool(prise.fin and (debut >= prise.fin or fin is None or fin > prise.fin))


def peut_ajuster(acteur, prise):
    from acteurs.politique import exiger_objet

    if not acteur.has_perm('personnes.change_accompagnement'):
        return False
    try:
        exiger_objet(acteur, prise, ecriture=True)
    except PermissionDenied:
        return False
    return True


def preparer_resolution(request, form, prise, champ_fin='fin', *, fin_par_defaut=None, proposer_nouvelle_prise=False, fin_incluse=False):
    from django.core import signing
    from django.utils import timezone
    from .admission import peut_ouvrir_apres_interruption

    debut = form.cleaned_data.get('debut')
    fin_saisie = form.cleaned_data.get(champ_fin, fin_par_defaut)
    fin = borne_exclue(fin_saisie, fin_incluse)
    if not debut:
        return None
    if fin and fin <= debut:
        form.add_error(champ_fin, 'La fin doit suivre le début de la prestation.')
        return None
    avant, apres = depassements(prise, debut, fin)
    form.conflit_periode = avant or apres
    if not form.conflit_periode:
        if request.POST.get('nouvelle_prise') or request.POST.get('confirmation_fin'):
            form.add_error(None, 'Les dates ont changé. Vérifiez la période avant d’enregistrer.')
        return None
    form.debut_demande = debut
    form.fin_confirmation = fin_saisie
    form.fin_nouvelle_prise = fin
    form.debut_prise_resolution = prise.debut if avant else None
    form.fin_prise_resolution = prise.fin if apres else None
    form.nouvelle_fin = fin if apres and fin and fin <= timezone.localdate() else None
    form.interruption = (fin and fin < prise.debut) or (prise.fin and debut > prise.fin)
    form.proposer_nouvelle_prise = proposer_nouvelle_prise and peut_ouvrir_apres_interruption(request.user, prise, debut, fin)
    etat = (prise.fin, prise.revision_sociale)
    donnees = [str(prise.pk), str(prise.debut), str(prise.fin), prise.revision_sociale, str(debut), str(fin),
               request.path_info, request.GET.get('pk'), request.GET.get('nature'), form.cleaned_data.get('attendu', '')]
    apercu = request.headers.get('X-Verifier-Prestation') == '1'
    commande = 'nouvelle_prise' if request.POST.get('nouvelle_prise') else 'confirmation_fin'
    try:
        confirme = not apercu and signing.loads(request.POST.get(commande, ''), salt='prestation-periode-prise', max_age=3600) == [commande, donnees]
    except signing.BadSignature:
        confirme = False
    if form.proposer_nouvelle_prise:
        if confirme and commande == 'nouvelle_prise':
            form.nouvelle_prise_confirmee = etat
            return None
        form.jeton_nouvelle_prise = signing.dumps(['nouvelle_prise', donnees], salt='prestation-periode-prise')
    if peut_ajuster(request.user, prise) and not getattr(form, 'ajustement_prise_interdit', False):
        if confirme and commande == 'confirmation_fin':
            return etat
        form.jeton_fin = signing.dumps(['confirmation_fin', donnees], salt='prestation-periode-prise')
    if not apercu and request.POST.get(commande) and not confirme:
        form.add_error(None, 'Les dates ou la prise en charge ont changé. Vérifiez les options affichées avant de confirmer.')
    if not getattr(form, 'jeton_fin', None) and not form.proposer_nouvelle_prise:
        try:
            verifier_periode_prise(prise, debut, fin, champ_fin=champ_fin)
        except ValidationError as erreur:
            reporter_erreur(form, erreur)
    return None


def autoriser_enregistrement(request, form, prise, **options):
    form.prise_confirmee = preparer_resolution(request, form, prise, **options)
    return not form.errors and (
        not getattr(form, 'conflit_periode', False) or form.prise_confirmee
        or getattr(form, 'nouvelle_prise_confirmee', False)
    )


def appliquer_resolution(acteur, prise, debut, fin, confirme, *, verrouille=False):
    """Applique les bornes sous la transaction de la prestation."""
    from .admission import modifier_fin_prise
    from .corrections import enregistrer
    from .social import verrouiller
    from .suivi import exiger

    if not verrouille:
        prise = verrouiller(prise)
    if (prise.fin, prise.revision_sociale - 1) != confirme:
        raise ValidationError('La prise en charge a changé. Rechargez le formulaire avant de confirmer.')
    if debut < prise.debut:
        exiger(acteur, 'change_accompagnement')
        ancienne = (prise.debut, prise.fin, '')
        prise.debut = debut
        prise.full_clean()
        prise.save(update_fields=['debut'])
        enregistrer(acteur, prise, ancienne, '')
    if depassements(prise, debut, fin)[1]:
        modifier_fin_prise(acteur, prise, debut, fin)
    return prise
