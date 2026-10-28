"""Frises en place : projection des périodes accessibles, aucune écriture métier."""
from collections import defaultdict
from datetime import timedelta
from math import log1p
from urllib.parse import urlencode, urlsplit

from django.core import signing
from django.db.models import Prefetch
from django.urls import reverse
from django.utils import timezone
from acteurs.contexte import perimetre
from . import models as m, dossier, aides

SESSION = 'frises_visibles'
SEL = 'frises-retour-v1'


def preference(request):
    return bool(request.session.get(SESSION, False))


def commande(request):
    query = request.GET.copy()
    query.pop('fragment', None)
    retour = request.path + ('?' + query.urlencode() if query else '')
    return signing.dumps({'compte': str(request.user.pk), 'retour': retour}, salt=SEL, compress=True)


def anniversaire(jour, annees=1):
    try:
        return jour.replace(year=jour.year-annees)
    except ValueError:
        return jour.replace(year=jour.year-annees, day=28)


class Echelle:
    def __init__(self, debut, fin, *, comprimee=True):
        self.debut, self.fin = debut, max(fin, debut + timedelta(days=1))
        self.comprimee = comprimee
        self.annee = (self.fin - anniversaire(self.fin)).days
        self.total = self.distance((self.fin - self.debut).days)

    def distance(self, jours):
        return jours if not self.comprimee or jours <= self.annee else self.annee + 90 * log1p((jours - self.annee) / 90)

    def position(self, jour):
        age = (self.fin - min(max(jour, self.debut), self.fin)).days
        return 100 * (1 - self.distance(age) / self.total)

    def intervalle(self, debut, fin):
        fin = fin or self.fin
        if debut >= self.fin or fin <= self.debut or fin <= debut:
            return None
        x, y = self.position(debut), self.position(fin)
        return {'x': f'{x:.4f}', 'w': f'{max(0, y-x):.4f}'}

    def reperes(self):
        valeurs = [(self.fin, 'Aujourd’hui' if self.fin == timezone.localdate() else 'Fin de la prise')]
        if self.comprimee:
            for annees in (1, 2, 5, 10, 20, 50):
                if self.fin.year <= annees:
                    continue
                jour = anniversaire(self.fin, annees)
                if jour >= self.debut:
                    valeurs.append((jour, f'−{annees} an' + ('s' if annees > 1 else '')))
        else:
            valeurs.append((self.debut, 'Début de la prise'))
        return [{'x': f'{self.position(j):.4f}', 'label': f'{libelle} · {j:%d/%m/%Y}'} for j, libelle in valeurs]


def bande(echelle, prises, faits):
    """HTML borné : densité par cellules de piste, sans empiler de hauteur."""
    aujourd = timezone.localdate()
    segments = []
    for p in prises:
        geo = echelle.intervalle(p.debut, p.fin)
        if p.debut == echelle.fin == aujourd and (not p.fin or p.fin > aujourd):
            geo = {'x':'99.4', 'w':'0.6'}
        if geo:
            segments.append({**geo, 'type': 'prise', 'lane': 0})
    evenements = defaultdict(lambda: defaultdict(int))
    for f in faits:
        if f['annule'] or f['type'] in ('lieu', 'absence'):
            continue
        geo = echelle.intervalle(f['debut'], f['fin'])
        if f['debut'] == echelle.fin == aujourd and (not f['fin'] or f['fin'] > aujourd):
            geo = {'x':'99.4', 'w':'0.6'}
        if not geo:
            continue
        x = float(geo['x']); y = min(100, x + float(geo['w']))
        evenements[(f['lane'], f['type'])][x] += 1
        evenements[(f['lane'], f['type'])][y] -= 1
    dense = False
    marques = []
    for (lane, type_), events in sorted(evenements.items()):
        nombre = 0; precedent = None
        for point, delta in sorted(events.items()):
            if precedent is not None and point > precedent and nombre:
                marques.append({'x':f'{precedent:.4f}', 'w':f'{point-precedent:.4f}',
                                'lane':lane, 'type':type_, 'dense':nombre>1})
                dense |= nombre>1
            nombre += delta; precedent = point
    approximative = len(marques) > 128
    if approximative:
        # En forte densité seulement, représenter l'occupation de cellules,
        # explicitement annoncée comme une synthèse et non comme des bornes exactes.
        cases = set()
        for s in marques:
            x=float(s['x']);y=x+float(s['w'])
            for i in range(int(x*.64), min(63,int(y*.64-1e-8))+1):
                cases.add((s['lane'],s['type'],i))
        marques=[{'x':f'{i*100/64:.4f}','w':f'{100/64:.4f}','lane':l,'type':t,'dense':True} for l,t,i in sorted(cases)]
        dense=True
    segments.extend(marques)
    # L'orange signale seulement le recouvrement des prises accessibles.
    tri = sorted(prises, key=lambda p: p.debut)
    borne = None
    chevauchement = False
    for p in tri:
        if borne is not None and p.debut < borne:
            chevauchement = True
        borne = max(borne or p.debut, p.fin or aujourd)
    futurs = any(p.debut > aujourd or (p.fin and p.fin > aujourd) or (p.fin_prevue and p.fin_prevue > aujourd) for p in prises) or any((f['debut'] > aujourd or (f['fin'] and f['fin'] > aujourd)) and not f['annule'] for f in faits)
    details = []
    for f in sorted(faits, key=lambda x: (x['debut'], x['label'], str(x['id']))):
        geo = echelle.intervalle(f['debut'], f['fin'])
        details.append({**f, 'geo': geo})
    return {'segments': segments, 'reperes': echelle.reperes(), 'dense': dense, 'recouvrement': chevauchement,
            'approximative': approximative, 'futur': futurs, 'details': details[:80], 'suite': len(details) > 80,
            'description': ' ; '.join(f'{p.debut:%d/%m/%Y} → ' + (f'{p.fin:%d/%m/%Y}' if p.fin else 'clôture non enregistrée') + (f' ; fin prévue {p.fin_prevue:%d/%m/%Y}' if p.fin_prevue else '') for p in tri),
            'echelle': 'Dernière année linéaire ; passé plus ancien comprimé progressivement' if echelle.comprimee else 'Échelle linéaire de la prise',
            'debut': echelle.debut, 'fin': echelle.fin}


def charger(acteur, objets, nature, *, prise=None, navigations=None, retour_recherche=None):
    # Revalider les identités en un groupe, sans une requête de contrôle par carte.
    with perimetre(acteur):
        for o in objets:
            o.frise = None
        if nature not in ('personne', 'menage') or not acteur.has_perms(dossier.DROITS):
            return {}
        modele = m.Personne if nature == 'personne' else m.Menage
        permis = set(modele.objects.filter(pk__in=[o.pk for o in objets]).values_list('pk', flat=True))
        return _charger(acteur, [o for o in objets if o.pk in permis], nature,
                        prise=prise, navigations=navigations, retour_recherche=retour_recherche)


def _charger(acteur, objets, nature, *, prise=None, navigations=None, retour_recherche=None):
    """Gestionnaires contrôlés pour chaque modèle et bénéficiaire avant regroupement."""
    for o in objets:
        o.frise = None
    if not acteur.has_perms(dossier.DROITS):
        return {}
    objets = [o for o in objets if not getattr(o, 'identite_seule', False)]
    ids = {o.pk for o in objets}
    qs = m.Accompagnement.objects.filter(menage_id__in=ids) if nature == 'menage' else m.Accompagnement.objects.filter(beneficiaires__pk__in=ids).distinct()
    if prise:
        qs = qs.filter(pk=prise.pk)
    prises = {p.pk: p for p in qs.prefetch_related(Prefetch('beneficiaires', to_attr='frise_beneficiaires'))}
    if prise:
        prise = prises.get(prise.pk)
        if prise is None:
            return {}
    beneficiaires = {p.pk: {b.pk for b in p.frise_beneficiaires} for p in prises.values()}
    faits = []

    def ajouter(x, p_id, type_, label, url, personnes, lane, annule=False):
        if p_id not in prises:
            return
        faits.append({'id': str(x.pk), 'debut': x.debut, 'fin': x.fin, 'type': type_, 'label': label,
                      'url': url, 'prise_id': p_id, 'personnes': personnes, 'lane': lane, 'annule': annule, 'sejour_id': str(getattr(x, 'sejour_id', x.pk if type_=='sejour' else ''))})

    if acteur.has_perms(['personnes.view_accordhebergement', 'personnes.view_sejour']):
        hs = {h.pk: h for h in m.AccordHebergement.objects.filter(accompagnement_id__in=prises).prefetch_related(Prefetch('beneficiaires', to_attr='frise_beneficiaires'))}
        for h in hs.values():
            ajouter(h, h.accompagnement_id, 'autorisation', 'Hébergement autorisé', reverse('suivi:accord_hebergement', args=[h.pk]),
                    {p.pk for p in h.frise_beneficiaires}, 1, bool(h.annule_le))
        ss = {s.pk: s for s in m.Sejour.objects.non_annules().filter(accord_id__in=hs).prefetch_related(Prefetch('beneficiaires', to_attr='frise_beneficiaires'))}
        ps = {s.pk: {p.pk for p in s.frise_beneficiaires} for s in ss.values()}
        for s in ss.values():
            ajouter(s, hs[s.accord_id].accompagnement_id, 'sejour', 'Continuation individuelle' if s.origine_collective_id else 'Séjour enregistré',
                    reverse('suivi:accord_hebergement', args=[s.accord_id]) + '#sejour-' + str(s.pk), ps[s.pk], 0)
        if acteur.has_perms(['personnes.view_affectation', 'personnes.view_lieuhebergement']):
            xs = list(m.Affectation.objects.filter(sejour_id__in=ss))
            lieux = {l.pk: l.libelle for l in m.LieuHebergement.objects.filter(pk__in={x.lieu_id for x in xs})}
            for x in xs:
                if x.lieu_id in lieux:
                    s = ss[x.sejour_id]
                    ajouter(x, hs[s.accord_id].accompagnement_id, 'lieu', lieux[x.lieu_id], reverse('suivi:accord_hebergement', args=[s.accord_id])+'#affectation-'+str(x.pk), ps[s.pk], 0)
        if acteur.has_perm('personnes.view_absence'):
            for x in m.Absence.objects.filter(sejour_id__in=ss):
                s = ss[x.sejour_id]
                ajouter(x, hs[s.accord_id].accompagnement_id, 'absence', 'Absence (sans clôture du séjour)', reverse('suivi:accord_hebergement', args=[s.accord_id])+'#absence-'+str(x.pk), ps[s.pk], 0)
    if acteur.has_perms(['personnes.view_accordrepas', 'personnes.view_repasdistribue']):
        for x in m.AccordRepas.objects.filter(accompagnement_id__in=prises).prefetch_related(Prefetch('beneficiaires', to_attr='frise_beneficiaires')):
            ajouter(x, x.accompagnement_id, 'repas', x.get_service_display()+' accordé', reverse('suivi:accord_repas', args=[x.pk]), {p.pk for p in x.frise_beneficiaires}, 2, bool(x.annule_le))
    if acteur.has_perms(aides.LECTURE):
        for x in m.AccordAide.objects.filter(accompagnement_id__in=prises).prefetch_related(Prefetch('beneficiaires', to_attr='frise_beneficiaires')):
            ajouter(x, x.accompagnement_id, 'aide', x.libelle+' (autorisation)', reverse('dossiers:aide', args=[x.pk]), {p.pk for p in x.frise_beneficiaires}, 3, bool(x.annule_le))
    if nature == 'personne':
        faits = [f for f in faits if f['personnes'] & ids]
    if not prises:
        return {}
    aujourd = timezone.localdate()
    debut = min([aujourd - timedelta(days=365)] + [p.debut for p in prises.values()] + [f['debut'] for f in faits])
    if prise:
        echelle = Echelle(min([aujourd - timedelta(days=1), prise.debut] + [f['debut'] for f in faits]), min(prise.fin, aujourd) if prise.fin else aujourd, comprimee=False)
    else:
        echelle = Echelle(debut, aujourd)
    resultat = {}
    for o in objets:
        pp = [p for p in prises.values() if p.menage_id == o.pk] if nature == 'menage' else [p for p in prises.values() if o.pk in beneficiaires[p.pk]]
        pids = {p.pk for p in pp}
        ff = [dict(f) for f in faits if f['prise_id'] in pids and (nature == 'menage' or o.pk in f['personnes'])]
        def enrichir(b, cle):
            b['cle'] = cle
            b['titre'] = str(o) if cle.startswith(nature+'-') else ('Prise en charge' if cle.startswith('accompagnement-') else (b['details'][0]['label'] if b['details'] else 'Prestation'))
            for f in b['details']:
                nav = (navigations or {}).get(f['prise_id'])
                if retour_recherche is not None:
                    nav = dossier.pour_vue_params(prises[f['prise_id']], nature, o.pk, {**retour_recherche, 'ecran':'recherche'})
                if nav:
                    valeurs = signing.loads(nav['contexte_dossier'], salt=dossier.SEL)
                    valeurs['vue'] = {**valeurs['vue'], 'frise_ouverte':cle}
                    token = signing.dumps(valeurs, salt=dossier.SEL, compress=True)
                    url = urlsplit(f['url'])
                    f['url'] = url.path + '?' + urlencode({'contexte_dossier':token}) + ('#'+url.fragment if url.fragment else '')
            return b
        o.frise = enrichir(bande(echelle, pp, ff), nature+'-'+str(o.pk))
        for p in pp:
            fs = [f for f in ff if f['prise_id'] == p.pk]
            resultat[('accompagnement', str(p.pk))] = enrichir(bande(echelle, [p], fs), 'accompagnement-'+str(p.pk))
        for f in ff:
            # Les noms de modèles distinguent les UUID éventuellement semblables.
            cle = {'sejour':'sejour', 'autorisation':'accordhebergement', 'repas':'accordrepas', 'aide':'accordaide'}.get(f['type'])
            if cle:
                fils = [f] + [x for x in ff if x['sejour_id'] == f['id'] and x['type'] in ('lieu', 'absence') and f['type']=='sejour']
                resultat[(cle, f['id'])] = enrichir(bande(echelle, [], fils), cle+'-'+f['id'])
    return resultat
