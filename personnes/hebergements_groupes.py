"""Lecture compacte des séjours visibles ; aucune écriture ni agrégation métier."""
def presenter(sejours, selection=None):
    par_accord={}
    for s in sejours:par_accord.setdefault(s.accord_id,[]).append(s)
    groupes=[]; collectifs=set(); selection_collective=False
    for identifiant, enfants in par_accord.items():
        personnes={p.pk:p for s in enfants for p in s.beneficiaires.all()}
        collectif=len(enfants)>1 and len(personnes)>1
        if not collectif:
            groupes.extend({'collectif':False,'sejours':[s]} for s in enfants)
            continue
        collectifs.add(identifiant)
        selection_collective |= any(selection and s.pk==selection.pk for s in enfants)
        debuts={s.debut for s in enfants}; fins={s.fin for s in enfants}
        lieux=[getattr(s,'lieu_ouvert',None) for s in enfants]
        lieu_commun=lieux[0].lieu if lieux and all(x and x.lieu_id==lieux[0].lieu_id for x in lieux) else None
        groupes.append({'collectif':True,'accord':enfants[0].accord,'sejours':enfants,
            'personnes':list(personnes.values()),'apercu_personnes':list(personnes.values())[:3],'autres_personnes':max(0,len(personnes)-3),'debut':next(iter(debuts)) if len(debuts)==1 else None,
            'fin_commune':len(fins)==1,'fin':next(iter(fins)) if len(fins)==1 else None,
            'lieu':lieu_commun,'nombre':len(enfants)})
    return groupes, collectifs, selection_collective
