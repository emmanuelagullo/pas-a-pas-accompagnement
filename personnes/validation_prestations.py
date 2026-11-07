"""Diagnostic de période, partagé par la saisie et les écritures métier."""
from django.core.exceptions import ValidationError
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



def diagnostic(form, prise, champ_fin='fin', *, fin_par_defaut=None, request=None, proposer_nouvelle_prise=False):
    valide = form.is_valid()
    if valide and request is not None:
        preparer_resolution(request, form, prise, champ_fin, fin_par_defaut=fin_par_defaut, proposer_nouvelle_prise=proposer_nouvelle_prise)
    debut = form.cleaned_data.get('debut')
    if debut and champ_fin not in form.errors and not getattr(form, 'jeton_fin', None):
        fin = form.cleaned_data.get(champ_fin, fin_par_defaut)
        try:
            verifier_periode_prise(prise, debut, fin, champ_fin=champ_fin)
        except ValidationError as erreur:
            reporter_erreur(form, erreur)
    reponse = {'erreurs': {nom: list(form.errors[nom]) for nom in ('debut', champ_fin, 'arrivee', 'admission', 'duree') if nom in form.errors}}
    if request is not None:
        from django.template.loader import render_to_string
        reponse['commandes'] = render_to_string(
            'dossiers/_prestation_validation.html', {'form': form, 'libelle_validation': 'Enregistrer'}, request=request,
        )
    return JsonResponse(reponse)


def preparer_resolution(request, form, prise, champ_fin='fin', *, fin_par_defaut=None, proposer_nouvelle_prise=False):
    """Retourne l'état confirmé de la prise et prépare la même commande en aperçu."""
    from django.core import signing
    from django.utils import timezone

    debut = form.cleaned_data.get('debut')
    fin = form.cleaned_data.get(champ_fin, fin_par_defaut)
    if not debut or not prise.fin or debut < prise.debut or (fin and fin < debut):
        return None
    if debut < prise.fin and fin is not None and fin <= prise.fin:
        return None
    if proposer_nouvelle_prise:
        from .admission import peut_ouvrir_apres_interruption
        form.proposer_nouvelle_prise = peut_ouvrir_apres_interruption(request.user, prise, debut)
        if form.proposer_nouvelle_prise and request.POST.get('nouvelle_prise') and request.headers.get('X-Verifier-Prestation') != '1':
            return None
    if not request.user.has_perm('personnes.change_accompagnement'):
        return None
    form.accompagnement = prise
    form.fin_confirmation = fin
    form.nouvelle_fin = fin if fin and fin <= timezone.localdate() else None
    donnees = [str(prise.pk), str(prise.fin), prise.revision_sociale, str(debut), str(fin),
               request.path_info, request.GET.get('pk'), request.GET.get('nature')]
    try:
        confirme = signing.loads(request.POST.get('confirmation_fin', ''), salt='prestation-fin-prise', max_age=3600) == donnees
    except signing.BadSignature:
        confirme = False
    if confirme:
        return prise.fin, prise.revision_sociale
    form.jeton_fin = signing.dumps(donnees, salt='prestation-fin-prise')
    return None


def appliquer_resolution(acteur, prise, debut, fin, confirme):
    """À appeler sous la transaction et après les contrôles propres à la prestation."""
    from .admission import modifier_fin_prise
    from .social import verrouiller

    prise = verrouiller(prise)
    if (prise.fin, prise.revision_sociale - 1) != confirme:
        raise ValidationError('La prise en charge a changé. Rechargez le formulaire avant de confirmer.')
    modifier_fin_prise(acteur, prise, debut, fin)
    return prise
