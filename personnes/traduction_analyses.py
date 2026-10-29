"""Traductions fermées ; un rapport non représentable reste spécialisé."""
from django.core.exceptions import ValidationError
from . import analyses as a


def structure(d):
    """Une personnalisation change les paramètres, pas les faits et calculs."""
    from copy import deepcopy
    structure={k:deepcopy(v) for k,v in d.items() if k not in ('debut','fin','reference','periode','decalage_debut','decalage_fin','filtre','export_prioritaire')}
    for partie in [*structure.get('criteres',[]),*structure.get('mesures',[])]:
        for f in partie.get('filtres',[]):f.pop('valeur',None)
    return structure



def depuis_exploration(acteur,p):
    if not p.get('exploration') or p.get('schema')!=1:raise ValidationError('Cette définition n’est pas un modèle composable historique.')
    from .modeles_echange import valider
    p=valider(acteur,p)
    d=a.defaut()
    for k in ('debut','fin','reference','reference_mode','periode','decalage_debut','decalage_fin','affichage','sous_totaux','filtre','export_prioritaire'):
        if k in p:d[k]=p[k]
    # Les booléens historiques sont sérialisés sous forme de chaînes.
    d['sous_totaux']=p.get('sous_totaux') in (True,'True','1')
    d['affichage']=p.get('affichage') or 'synthese'
    d['reference_mode']=p.get('reference_mode') or 'commune'
    d['lignes']=p['population']
    d['axes']=[p['axe'],*([p['croisement']] if p.get('croisement') else []),*[p['axe'+str(i)] for i in range(3,8) if p.get('axe'+str(i))]]
    d['classes']=[p.get('classes',''),*([p.get('classes_croisement','')] if p.get('croisement') else []),*[p.get('classes'+str(i),'') for i in range(3,8) if p.get('axe'+str(i))]]
    d['colonnes']=[p['colonne'+str(i)] for i in range(1,12) if p.get('colonne'+str(i))] or [p['axe'],*([p['croisement']] if p.get('croisement') else [])]
    commun=dict(source=p['population'],mouvement=p.get('mouvement','chevauche'),portion=p.get('portion','selection'),cohorte=p.get('cohorte','tous'),lignes_vides=p.get('lignes_vides') in (True,'True','1'),filtres=[dict(champ=p['filtre'+str(i)],operation=p['operation'+str(i)],valeur=p.get('valeur'+str(i),'')) for i in range(1,int(p.get('filtres') or 2)+1) if p.get('filtre'+str(i))])
    codes=list(dict.fromkeys([p['mesure'],*[p['mesure'+str(i)] for i in range(2,10) if p.get('mesure'+str(i))]]))
    d['mesures']=[{**commun,'mesure':code} for code in codes]
    return a.valider(acteur,d)


def depuis_rapport(acteur,source,params):
    from .personnalisation_rapports import adapter
    if source=='statistiques' and params.get('rapport')=='mouvements' and params.get('comparer')!='1':
        from .vues_statistiques import parametres_modele
        from .rapports_metier import LIBELLES_MOUVEMENTS
        p=parametres_modele(params);d=a.defaut()
        for k in ('debut','fin','periode','decalage_debut','decalage_fin','filtre','export_prioritaire'):
            if k in p:d[k]=p[k]
        from datetime import date,timedelta
        d['reference']=(date.fromisoformat(p['fin'])-timedelta(days=1)).isoformat()
        codes=[('admissions_sejours','objets','entrees'),('sorties_sejours','objets','sorties'),('beneficiaires_admissions','participations','entrees'),('beneficiaires_sorties','participations','sorties'),('personnes_admises_distinctes','personnes','entrees'),('personnes_sorties_distinctes','personnes','sorties'),('nuits_sejours_clos_total','durees_total','sorties'),('nuits_sejours_clos_min','durees_min','sorties'),('nuits_sejours_clos_max','durees_max','sorties'),('nuits_sejours_clos_moyenne','durees_moyenne','sorties')]
        # Dix indicateurs ; le modèle d'analyse ne doit pas supprimer le dixième.
        d['mesures']=[dict(source='sejours',mesure=mesure,mouvement=mouvement,portion='integrale' if mesure.startswith('durees_') else 'selection',titre=LIBELLES_MOUVEMENTS[code]) for code,mesure,mouvement in codes]
        return a.valider(acteur,d)
    if source=='statistiques' and params.get('rapport') in ('hebergement','synthese','ages') and params.get('comparer')!='1':
        from .vues_statistiques import parametres_modele
        from datetime import date,timedelta
        from .suivi import exiger
        exiger(acteur,'view_accompagnement','view_sejour','view_repasdistribue')
        p=parametres_modele(params);d=a.defaut()
        for k in ('debut','fin','periode','decalage_debut','decalage_fin','filtre','export_prioritaire'):
            if k in p:d[k]=p[k]
        d['reference']=(date.fromisoformat(p['fin'])-timedelta(days=1)).isoformat()
        if p['rapport']=='ages':
            d.update(axes=['age','qualite_naissance'],mesures=[dict(source='fragments_sejour',mesure='personnes',titre='Âges calculables et précision des naissances')])
        else:
            d['mesures']=[dict(source='fragments_sejour',mesure='personnes',titre='Personnes distinctes avec séjour'),dict(source='sejours',mesure='objets',titre='Épisodes de séjour'),dict(source='sejours',mesure='objets',mouvement='entrees',titre='Admissions'),dict(source='sejours',mesure='objets',mouvement='sorties',titre='Sorties'),dict(source='fragments_sejour',mesure='quantite',titre='Nuitées théoriques'),dict(source='fragments_sejour',mesure='nuits_distinctes',titre='Nuits distinctes par personne'),dict(source='fragments_sejour',mesure='nuits_hors_absences',titre='Nuits distinctes hors absences déclarées')]
            if p['rapport']=='synthese':d['mesures']=[dict(source='prises',mesure='menages',titre='Ménages accompagnés'),dict(source='prises',mesure='objets',titre='Prises en charge'),*d['mesures'],dict(source='repas',mesure='quantite',titre='Repas distribués')]
        return a.valider(acteur,d)
    p=adapter(acteur,source,params);p.update(exploration=True,schema=1)
    return depuis_exploration(acteur,p)
