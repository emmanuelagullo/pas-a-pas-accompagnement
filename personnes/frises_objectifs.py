"""États déclarés des objectifs : lecture contrôlée, jamais score de progression."""
from collections import defaultdict
from datetime import timedelta
from urllib.parse import urlencode
from acteurs.contexte import perimetre
from django.db.models import Q
from . import models as m, parcours
from .frises import Echelle


def charger(acteur, items, nature, objet, jour, url, retour_signe=''):
    """Deux lectures groupées, après les mêmes droits/cibles que le bloc Projet."""
    for item in items:
        item.pop('frise_objectif',None)
    if not items or not acteur.has_perms(parcours.droits('objectifs')):
        return None
    with perimetre(acteur):
        ids = [i['fait'].element_id for i in items]
        racines = m.ObjectifParcours.objects.filter(pk__in=ids, annule_le__isnull=True)
        if nature == 'personne':
            racines = racines.filter(Q(personne=objet) | Q(beneficiaires=objet)).distinct()
        elif nature == 'menage':
            racines = racines.filter(menage=objet)
        else:
            return None
        if not acteur.has_perm('personnes.view_menage'):
            racines = racines.filter(menage__isnull=True)
        collectifs = dict(racines.values_list('pk','menage_id'))
        permis = set(collectifs)
        peut_modifier = acteur.has_perm('personnes.change_objectifparcours')
        groupes = defaultdict(list)
        for v in m.VersionObjectif.objects.filter(element_id__in=permis, debut__lte=jour).only(
                'element_id', 'debut', 'fin', 'etat', 'echeance', 'titre', 'source', 'enregistre_le').order_by('debut', 'pk'):
            groupes[v.element_id].append(v)
    if not groupes:
        return None
    debut = min([jour-timedelta(days=1)] + [v.debut for vs in groupes.values() for v in vs])
    echelle = Echelle(debut, jour, comprimee=False)
    for item in items:
        vs = groupes.get(item['fait'].element_id, [])
        if not vs:
            continue
        b = projeter(vs, echelle)
        for ligne in b['lignes']:
            v = ligne['fait']
            ligne['modifier'] = url('dossiers:parcours_corriger', 'objectifs', v.element_id, v.pk) if peut_modifier else ''
        b['source'] = item['url'] + ('&'+urlencode({'retour_frise_objectif':retour_signe}) if retour_signe else '')
        b['collectif'] = bool(collectifs.get(item['fait'].element_id))
        item['frise_objectif'] = b
    return {'debut': debut, 'fin':jour}


def projeter(versions, echelle):
    """Pas de raccord à travers un trou, pas de nouvelle réussite pour une révision."""
    marques, lignes = [], []
    precedent = None
    for v in versions:
        geo = echelle.intervalle(v.debut, v.fin)
        continu = precedent and precedent.fin == v.debut and precedent.etat == v.etat
        if v.etat in ('atteint', 'abandonne'):
            if not continu:
                marques.append({'x':f'{echelle.position(v.debut):.4f}', 'w':'0', 'type':v.etat, 'point':True})
        elif geo:
            if continu and marques and marques[-1]['type'] == v.etat and not marques[-1].get('point'):
                debut = float(marques[-1]['x'])
                marques[-1]['w'] = f'{float(geo["x"])+float(geo["w"])-debut:.4f}'
            else:
                marques.append({**geo, 'type':v.etat})
        elif v.debut == echelle.fin:
            marques.append({'x':'100', 'w':'0', 'type':v.etat, 'point':True})
        lignes.append({'fait':v, 'etat':v.get_etat_display(),
                       'fin_visible':v.fin if v.fin and v.fin <= echelle.fin else None})
        precedent = v
    condensee = len(marques) > 128
    if condensee:
        cases = defaultdict(set)
        for marque in marques:
            x=float(marque['x']); y=x+float(marque['w'])
            for i in range(min(63,int(x*.64)), min(63,int(max(x,y-1e-8)*.64))+1):
                cases[i].add(marque['type'])
        marques=[]
        for i,types in sorted(cases.items()):
            type_=next(iter(types)) if len(types)==1 else 'dense'
            point=type_ in ('atteint','abandonne')
            marques.append({'x':f'{(i+(.5 if point else 0))*100/64:.4f}',
                            'w':'0' if point else f'{100/64:.4f}', 'type':type_, 'point':point})
    return {'marques':marques, 'lignes':lignes[-80:], 'suite':len(lignes)>80,
            'condensee':condensee, 'debut':echelle.debut, 'fin':echelle.fin}
