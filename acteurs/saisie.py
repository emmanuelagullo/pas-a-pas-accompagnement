from django import forms
from personnes.models import Intervenant
from .contexte import courant
from . import politique as p
from .models import AppartenanceProfessionnelle


def preparer(form):
    ctx=courant()
    if not ctx or not ctx.creation or not p.active():return
    hs=p.habilitations(ctx.compte).filter(service_id=ctx.service_id)
    if ctx.creation=='dossier' and not hs.filter(tache='social').exists():return
    qs=Intervenant.objects.filter(pk__in=AppartenanceProfessionnelle.objects.filter(
        p.periode(),service_id=ctx.service_id).values('professionnel_id'))
    initial=None if ctx.creation=='prise' else p.professionnel(ctx.compte)
    form.fields['responsable_acteurs']=forms.ModelChoiceField(qs,required=False,initial=initial,
        label='Qui s’en occupera ?',empty_label='Reprendre les intervenants du dossier' if ctx.creation=='prise' else 'Moi-même',
        help_text='Proposition enregistrée avec la création, sans modifier les autres suivis. Les accès suivent la politique du service.')


def nettoyer(d):
    d.pop('responsable_acteurs',None)
    return d
