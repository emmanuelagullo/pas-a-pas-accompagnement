"""Contexte de navigation signé, jamais une autorisation d'accès ou d'écriture."""
from urllib.parse import urlencode
from django.core import signing
from django.urls import reverse
from .retour_service import date_service

DROITS = ('personnes.view_personne', 'personnes.view_menage', 'personnes.view_accompagnement')
SEL = 'dossier-navigation-v1'


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
    return {'contexte_dossier': token, 'dossier_valeurs': valeurs,
            'retour_dossier': reverse('suivi:accompagnement', args=[accompagnement.pk]) + '?' + urlencode({'contexte_dossier': token})}


def creer(request, accompagnement, sejour, repas):
    precedent = lire(request, accompagnement).get('dossier_valeurs', {})
    valeurs = {'accompagnement': str(accompagnement.pk),
               'sejour': str(sejour.pk) if sejour else '', 'repas': str(repas.pk) if repas else '',
               'date_service': precedent.get('date_service') or date_service(request.GET.get('date_service')),
               'origine': precedent.get('origine') or ('jour' if request.GET.get('retour') == 'jour' else ''),
               'recherche': precedent.get('recherche', request.GET.get('q', '')[:160]),
               'page': precedent.get('page', request.GET.get('page', '1')[:8])}
    token = signing.dumps(valeurs, salt=SEL, compress=True)
    return {'contexte_dossier': token, 'dossier_valeurs': valeurs,
            'retour_dossier': reverse('suivi:accompagnement', args=[accompagnement.pk]) + '?' + urlencode({'contexte_dossier': token})}
