"""Quatre parties modifiables sans assistant ni état caché côté navigateur."""
CLES_AXES=['axe','croisement',*('axe'+str(i) for i in range(3,8))]
CLES_CLASSES=['classes','classes_croisement',*('classes'+str(i) for i in range(3,8))]


def deplacer(data,action):
    """Déplacer ensemble un axe et ses classes ; tous les autres critères restent intacts."""
    d=data.copy()
    try:
        position,sens=map(int,action.split(':'));n=min(7,max(2,int(d.get('niveaux') or 2)))
    except (ValueError,TypeError):return d
    origine=position-1;cible=origine+sens
    if sens not in (-1,1) or not 0<=origine<n or not 0<=cible<n:return d
    if not d.get(CLES_AXES[origine]) or not d.get(CLES_AXES[cible]):return d
    for cles in (CLES_AXES,CLES_CLASSES):
        a,b=cles[origine],cles[cible];d[a],d[b]=d.get(b,''),d.get(a,'')
    return d


def retirer(data,position):
    d=data.copy()
    try:n=min(7,max(2,int(d.get('niveaux') or 2)));index=int(position)-1
    except (ValueError,TypeError):return d
    if not 0<=index<n:return d
    for cles in (CLES_AXES,CLES_CLASSES):
        vals=[d.get(c,'') for c in cles[:n]];vals.pop(index);vals.append('')
        for c,v in zip(cles,vals):d[c]=v
    if not d.get('axe'):d['axe']='total'
    d['niveaux']=str(max(2,n-1))
    for i in range(max(2,n-1),7):
        for cles in (CLES_AXES,CLES_CLASSES):d.pop(cles[i],None)
    return d


def presenter(form,request):
    def nom(c):
        valeur=form[c].value()
        if valeur in (None,'') and c=='affichage':valeur='synthese'
        return str(dict(form.fields[c].choices).get(valeur,valeur or 'Aucun'))
    ouverts=request.GET.get('panneau','')
    if request.GET.get('ajouter_niveau') or request.GET.get('deplacer_niveau') or request.GET.get('retirer_niveau'):ouverts='classer'
    elif request.GET.get('ajouter_mesure'):ouverts='compter'
    elif request.GET.get('ajouter_colonne'):ouverts='afficher'
    elif request.GET.get('ajouter_filtre'):ouverts='retenir'
    parties=[dict(cle=c,titre=t,champs=[],ouvert=c==ouverts) for c,t in [('retenir','Retenir'),('afficher','Afficher'),('compter','Compter'),('classer','Classer')]]
    par_cle={x['cle']:x for x in parties}
    niveaux=[]
    for i,(axe,classes) in enumerate(zip(CLES_AXES,CLES_CLASSES),1):
        if axe not in form.fields:break
        niveaux.append(dict(position=i,axe=form[axe],classes=form[classes],monter=i>1 and bool(form[CLES_AXES[i-2]].value()),
            descendre=i<len(CLES_AXES) and CLES_AXES[i] in form.fields and bool(form[CLES_AXES[i]].value())))
    for f in form.visible_fields():
        if f.name in CLES_AXES or f.name in CLES_CLASSES:continue
        cle='compter' if f.name=='mesure' or f.name.startswith('mesure') else 'afficher' if f.name in ('affichage','lignes_vides') or f.name.startswith('colonne') else 'classer' if f.name=='sous_totaux' else 'retenir'
        par_cle[cle]['champs'].append(f)
        if f.errors:par_cle[cle]['ouvert']=True
    priorite={nom:i for i,nom in enumerate(('population','periode','debut','fin','reference_mode','reference','mouvement','portion','cohorte'))}
    par_cle['retenir']['champs'].sort(key=lambda champ:priorite.get(champ.name,len(priorite)))
    if form.non_field_errors():
        for p in parties:p['ouvert']=True
    for n in niveaux:
        if n['axe'].errors or n['classes'].errors:par_cle['classer']['ouvert']=True
    if form.errors and not any(p['ouvert'] for p in parties):
        for p in parties:p['ouvert']=True
    criteres=[]
    for i in range(1,21):
        champ='filtre'+str(i)
        if champ in form.fields and form[champ].value():
            criteres.append(nom(champ)+' '+nom('operation'+str(i))+' '+str(form['valeur'+str(i)].value() or ''))
    par_cle['retenir']['resume']=nom('population')+' · '+str(form['debut'].value())+' → '+str(form['fin'].value())+' (fin exclue)'+(' · '+' ; '.join(criteres[:3])+(' ; et '+str(len(criteres)-3)+' autres critères' if len(criteres)>3 else '') if criteres else ' · Sans filtre supplémentaire')
    par_cle['afficher']['resume']=nom('affichage')+' · '+str(sum(bool(form[c].value()) for c in form.fields if c.startswith('colonne')))+' colonnes choisies'
    par_cle['compter']['resume']=' · '.join(nom(c) for c in form.fields if c=='mesure' or c.startswith('mesure') and c[6:].isdigit() if form[c].value())
    par_cle['classer']['resume']=' → '.join(nom(c) for c in CLES_AXES if c in form.fields and form[c].value())+(' · Sous-totaux recalculés' if form['sous_totaux'].value() not in (None,'',False,'False','false','0') else '')
    return parties,niveaux
