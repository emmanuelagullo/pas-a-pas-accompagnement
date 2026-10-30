"""Résumés et ouverture locale : aucun état de calcul supplémentaire."""
from django.utils.choices import flatten_choices
from django import forms


def blocs(form, cle, action):
    resultat=[]
    def libelle(nom):
        f=form[nom]
        if isinstance(f.field,forms.BooleanField):return f.label
        return str(dict(flatten_choices(getattr(f.field,'choices',[]))).get(f.value(),f.value() or ''))
    for b in form.parties[cle]:
        prefixe=b['prefixe']
        champs=[form[k] for k in b['champs']]
        regles=[form[k] for k in b['regles'] if not form[k].is_hidden]
        filtres=[[form[k] for k in fs] for fs in b['filtres']]
        source=libelle(prefixe+'source')
        titre=(str(form[prefixe+'titre'].value() or '') if cle=='mesure' else '')
        calcul=libelle(prefixe+'mesure') if cle=='mesure' else libelle(prefixe+'mode')
        resume=source+' — '+calcul
        conditions=[' '.join(libelle(f.name) for f in fs if f.value()) for fs in filtres if fs[0].value()]
        if conditions:resume+=' · '+' ; '.join(conditions)
        if cle=='critere':resume+=' · '+libelle(prefixe+'relation')
        actives=[f for f in regles if f.value() not in ('',None,False,'False','false','0','chevauche','selection','tous')]
        if actives:resume+=' · '+' · '.join(libelle(f.name) for f in actives)
        erreurs=any(f.errors for f in champs+regles+[f for fs in filtres for f in fs])
        resultat.append({**b,'titre':titre or resume,'resume':resume if titre else '',
            'champs':champs,'regles':regles,'filtres':filtres,'erreurs':erreurs,
            'ouvert':erreurs or action.startswith(prefixe) or action=='actualiser-'+prefixe or action==cle and b is form.parties[cle][-1],
            'regles_ouvertes':any(f.errors for f in regles)})
    return resultat
