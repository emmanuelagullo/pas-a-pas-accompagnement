"""Périmètre de consultation transporté dans les liens, critères et exports."""
from contextlib import contextmanager
from django.core.exceptions import PermissionDenied
from . import politique as p
from .contexte import courant, perimetre

FILTRES={'tous':'accessibles','mes':'mes','service':'service_accessible','attente':'attente'}


def filtre(donnees):
    valeur=donnees.get('filtre','tous')
    return valeur if valeur in FILTRES else 'tous'


def parametres(donnees):
    resultat={'filtre':filtre(donnees)} if p.active() or 'filtre' in donnees else {}
    if donnees.get('portee_statistiques') in ('service','etablissement'):
        resultat['portee_statistiques']=donnees['portee_statistiques']
    return resultat


@contextmanager
def selection(compte,donnees,source=None):
    if not p.active():
        yield False
        return
    mode=FILTRES[filtre(donnees)]
    groupe=donnees.get('portee_statistiques')
    if groupe in ('service','etablissement'):
        if source!='statistiques' or donnees.get('rapport','synthese') not in ('synthese','hebergement','repas','mensuel'):
            raise PermissionDenied('Ce rapport ne permet pas cette portée de totaux.')
        ctx=courant()
        option='statistiques_service' if groupe=='service' else 'statistiques_etablissement'
        if not ctx or not p.habilitations(compte).filter(service_id=ctx.service_id,**{option:True}).exists():raise PermissionDenied
        mode=groupe
    with perimetre(compte,statistiques=mode):
        yield mode


from django.template.response import TemplateResponse


class ReponseBornee(TemplateResponse):
    """Le rendu différé conserve la sélection, après composition du rapport."""
    def render(self):
        if self._is_rendered:return self
        with selection(*self.selection_acteurs):
            return super().render()


def reponse_bornee(reponse,compte,donnees,source):
    if not isinstance(reponse,TemplateResponse) or reponse.is_rendered:return reponse
    resultat=ReponseBornee(reponse._request,reponse.template_name,reponse.context_data,
        status=reponse.status_code,using=reponse.using,headers=reponse.headers)
    resultat.cookies=reponse.cookies
    resultat._post_render_callbacks=list(reponse._post_render_callbacks)
    resultat.selection_acteurs=(compte,dict(donnees),source)
    return resultat
