from acteurs.contexte import service_metier
"""Contexte de navigation signé, jamais une autorisation d'accès ou d'écriture."""
from urllib.parse import urlencode
from django.core import signing
from django.urls import reverse
from .retour_service import date_service

DROITS = ('personnes.view_personne', 'personnes.view_menage', 'personnes.view_accompagnement')
SEL = 'dossier-navigation-v1'
CLES_SOCIALES = ('vue_sociale', 'date_sociale', 'presentation_sociale', 'origines_sociales')


def lire(request, accompagnement):
    if accompagnement is None or not request.user.has_perms(DROITS):
        return {}
    token = request.POST.get('contexte_dossier') or request.GET.get('contexte_dossier')
    try:
        valeurs = signing.loads(token, salt=SEL, max_age=86400)
        if not isinstance(valeurs, dict) or valeurs.get('accompagnement') != str(accompagnement.pk):
            return {}
    except (signing.BadSignature, TypeError, ValueError):
        return {}
    if valeurs.get('vue') and not vue_autorisee(request.user, accompagnement, valeurs['vue']):
        return {}
    return {'contexte_dossier': token, 'dossier_valeurs': valeurs,
            'retour_dossier': retour(accompagnement, valeurs, token)}


def creer(request, accompagnement, sejour, repas):
    precedent = lire(request, accompagnement).get('dossier_valeurs', {})
    valeurs = {'accompagnement': str(accompagnement.pk),
               'sejour': str(sejour.pk) if sejour else '', 'repas': str(repas.pk) if repas else '',
               'date_service': precedent.get('date_service') or date_service(request.GET.get('date_service')),
               'origine': precedent.get('origine') or ('jour' if request.GET.get('retour') == 'jour' else ''),
               'recherche': precedent.get('recherche', request.GET.get('q', '')[:160]),
               'page': precedent.get('page', request.GET.get('page', '1')[:8])}
    retour_stats=request.POST.get('retour_exploration') or request.GET.get('retour_exploration') or precedent.get('retour_exploration')
    if retour_stats:valeurs['retour_exploration']=retour_stats[:20000]
    if precedent.get('vue'):
        valeurs['vue'] = precedent['vue']
    token = signing.dumps(valeurs, salt=SEL, compress=True)
    return {'contexte_dossier': token, 'dossier_valeurs': valeurs,
            'retour_dossier': retour(accompagnement, valeurs, token)}


@service_metier
def vue_autorisee(acteur, accompagnement, vue):
    """Le jeton de retour ne remplace jamais la cible ni ses droits actuels."""
    if not isinstance(vue, dict) or not acteur.has_perms(DROITS):
        return False
    if vue.get('nature') == 'menage':
        return vue.get('pk') == str(accompagnement.menage_id)
    if vue.get('nature') == 'personne':
        return accompagnement.beneficiaires.filter(pk=vue.get('pk')).exists()
    return False


def retour(accompagnement, valeurs, token):
    vue = valeurs.get('vue')
    if vue:
        route = 'dossiers:prise' if accompagnement and vue.get('ecran') == 'prise' and vue.get('prise') == str(accompagnement.pk) else 'dossiers:detail'
        args = [vue['nature'], vue['pk']] + ([accompagnement.pk] if route == 'dossiers:prise' else [])
        return reverse(route, args=args) + '?' + urlencode({'contexte_dossier': token}) + (('#hebergement-prevu-' + vue['prevision'] if route == 'dossiers:prise' else '#prises') if vue.get('prevision') else '')
    return reverse('suivi:accompagnement', args=[accompagnement.pk]) + '?' + urlencode({'contexte_dossier': token})


def pour_vue(request, accompagnement, nature, pk, params):
    valeurs = creer(request, accompagnement, None, None)['dossier_valeurs']
    valeurs.update({k: params.get(k, valeurs.get(k, '')) for k in ('sejour', 'repas')})
    if params.get('date_service'):
        valeurs['date_service'] = date_service(params['date_service'])
    valeurs['vue'] = {'nature': nature, 'pk': str(pk), **{k: params.get(k, '') for k in
        ('q', 'mode', 'page', 'sejour', 'repas', 'origine_menage', 'origine_sejour', 'origine_repas', 'prise', 'ecran', 'date_service', 'prevision', 'retour_exploration', *CLES_SOCIALES)}}
    token = signing.dumps(valeurs, salt=SEL, compress=True)
    return {'contexte_dossier': token, 'dossier_valeurs': valeurs,
            'retour_dossier': retour(accompagnement, valeurs, token)}


def valeurs_vue(request, nature, pk):
    token = request.GET.get('contexte_dossier')
    try:
        valeurs = signing.loads(token, salt=SEL, max_age=86400)
        vue = valeurs.get('vue', {})
        if vue.get('nature') == nature and vue.get('pk') == str(pk):
            return {**{k: vue.get(k, '') for k in ('q', 'mode', 'page', 'sejour', 'repas', 'origine_menage', 'origine_sejour', 'origine_repas', 'prise', 'ecran', 'prevision', 'retour_exploration', *CLES_SOCIALES)}, 'date_service': valeurs.get('date_service') or vue.get('date_service', '')}
    except (signing.BadSignature, TypeError, ValueError, AttributeError):
        pass
    return {}


def pour_personne(pk, params):
    vue = {'nature': 'personne', 'pk': str(pk), **{k: params.get(k, '') for k in
        ('q', 'mode', 'page', 'sejour', 'repas', 'origine_menage', 'origine_sejour', 'origine_repas', 'prise', 'ecran', 'date_service', 'prevision', 'retour_exploration', *CLES_SOCIALES)}}
    valeurs = {'vue': vue}
    token = signing.dumps(valeurs, salt=SEL, compress=True)
    return {'contexte_dossier': token, 'dossier_valeurs': valeurs, 'retour_dossier': retour(None, valeurs, token)}


def lire_personne(request, pk):
    if not request.user.has_perm('personnes.view_personne'):
        return {}
    token = request.POST.get('contexte_dossier') or request.GET.get('contexte_dossier')
    try:
        valeurs = signing.loads(token, salt=SEL, max_age=86400)
        vue = valeurs.get('vue', {})
        if vue.get('nature') == 'personne' and vue.get('pk') == str(pk):
            return {'contexte_dossier': token, 'dossier_valeurs': valeurs, 'retour_dossier': retour(None, valeurs, token)}
    except (signing.BadSignature, TypeError, ValueError, AttributeError):
        pass
    return {}


def pour_prise(request, accompagnement, nature, pk, params):
    return pour_vue(request, accompagnement, nature, pk, {**params, 'prise': str(accompagnement.pk), 'ecran': 'prise'})
