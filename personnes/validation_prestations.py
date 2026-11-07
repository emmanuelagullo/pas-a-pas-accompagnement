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



def diagnostic(form, prise, champ_fin='fin', *, fin_par_defaut=None):
    form.is_valid()
    debut = form.cleaned_data.get('debut')
    if debut and champ_fin not in form.errors:
        fin = form.cleaned_data.get(champ_fin, fin_par_defaut)
        try:
            verifier_periode_prise(prise, debut, fin, champ_fin=champ_fin)
        except ValidationError as erreur:
            reporter_erreur(form, erreur)
    return JsonResponse({'erreurs': {nom: list(form.errors[nom]) for nom in ('debut', champ_fin, 'arrivee', 'admission') if nom in form.errors}})
