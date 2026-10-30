"""Éditeur progressif : les sources appartiennent aux critères et aux mesures."""
from copy import deepcopy
from django import forms
from .champs_saisie import FormulaireMetier
from .forms_exploration import ExplorationForm
from . import analyses as a, exploration as e


def aplatir(d):
    p={k:v for k,v in d.items() if k not in ('mesures','criteres','axes','classes','colonnes')}
    for cle,liste in [('mesure',d.get('mesures',[])),('critere',d.get('criteres',[]))]:
        p['nombre_'+cle]=len(liste)
        for i,partie in enumerate(liste,1):
            partie={**dict(mode='avec',relation='personne',mouvement='chevauche',portion='selection',cohorte='tous'),**partie}
            for c,v in partie.items():
                if c!='filtres':p[f'{cle}{i}_{c}']=v
            p[f'{cle}{i}_nombre_filtres']=len(partie.get('filtres',[]))
            for j,f in enumerate(partie.get('filtres',[]),1):
                for c,v in f.items():p[f'{cle}{i}_f{j}_{c}']=v
    for cle in ('axes','colonnes','classes'):
        p['nombre_'+cle]=len(d.get(cle,[]))
        for i,v in enumerate(d.get(cle,[]),1):p[cle+str(i)]=v
    return p


class AnalyseForm(FormulaireMetier):
    def __init__(self,*args,acteur,**kw):
        super().__init__(*args,**kw)
        data=self.data or self.initial
        ancien=ExplorationForm(acteur=acteur)
        self.groupes={k:[] for k in ('retenir','afficher','compter','classer')}
        self.parties={'critere':[],'mesure':[]}
        def choix_contextuels(champ, compatibles, valeur):
            # Ne jamais effacer un paramètre repris : il reste visible et validé
            # par le moteur, même lorsqu'il ne correspond plus au contexte.
            choix=list(champ.choices)
            courants=[(k,v) for k,v in choix if compatibles(k)]
            conserves=[(k,v) for k,v in choix if k==valeur and not compatibles(k)]
            champ.choices=courants+([('Choix conservé — à vérifier',conserves)] if conserves else [])
        def dimensions(champ,sources,valeur):
            choix_contextuels(champ,lambda k:not k or all(e.dimension_compatible(src,k) for src in sources),valeur)
            # Les dimensions personnelles restent disponibles, rangées par domaine.
            directs=[];domaines={}
            for k,v in list(champ.choices):
                if isinstance(v,list):directs.append((k,v))
                elif '.' in k:domaines.setdefault(k.split('.')[0],[]).append((k,v))
                else:directs.append((k,v))
            noms={'social':'Situation personnelle à la référence','mission':'Missions dans la prise en charge','relation':'Liens personnels','identite':'Identité','famille':'Déclarations familiales','coordonnees':'Coordonnées','administration':'Situation administrative'}
            champ.choices=directs+[(noms.get(g,vs[0][1].split(' — ')[0]),vs) for g,vs in domaines.items()]

        def ajouter(nom,champ,groupe):
            self.fields[nom]=champ;self.groupes[groupe].append(nom)
        for nom in ('periode','debut','fin','decalage_debut','decalage_fin','reference','reference_mode'):
            champ=deepcopy(ancien.fields[nom])
            if nom.startswith('decalage') and data.get('periode') not in ('jours_relatifs','date_relative'):champ.widget=forms.HiddenInput()
            ajouter(nom,champ,'retenir')
        ajouter('combinaison',forms.ChoiceField(label='Retenir si',choices=[('toutes','Toutes les conditions sont remplies (ET)'),('une','Au moins une condition est remplie (OU)')]),'retenir')
        from acteurs import politique
        if politique.active():ajouter('filtre',forms.ChoiceField(label='Dossiers',choices=[('tous','Tous les dossiers accessibles'),('mes','Mes dossiers'),('service','Mon service'),('attente','En attente')]),'retenir')
        def nombre(cle,mini,maxi,defaut):
            try:n=int(data.get('nombre_'+cle,defaut))
            except (ValueError,TypeError):n=defaut
            self.fields['nombre_'+cle]=forms.IntegerField(min_value=mini,max_value=maxi,initial=n,widget=forms.HiddenInput)
            return max(mini,min(n,maxi))
        for cle,groupe,maximum in [('critere','retenir',20),('mesure','compter',12)]:
            n=nombre(cle,0 if cle=='critere' else 1,maximum,0 if cle=='critere' else 1)
            for i in range(1,n+1):
                prefixe=f'{cle}{i}_';noms=[]
                def champ(c,f):self.fields[prefixe+c]=f;noms.append(prefixe+c)
                if cle=='mesure':champ('titre',forms.CharField(label='Nom de la mesure (facultatif)',max_length=160,required=False))
                champ('source',forms.ChoiceField(label='Faits à examiner' if cle=='critere' else 'Éléments à compter',choices=e.POPULATIONS))
                source=data.get(prefixe+'source','repas')
                if cle=='mesure':
                    mesure=deepcopy(ancien.fields['mesure']);mesure.label='Calcul'
                    choix_contextuels(mesure,lambda code:mesure_compatible(source,code),data.get(prefixe+'mesure'))
                    champ('mesure',mesure)
                else:
                    champ('mode',forms.ChoiceField(label='Condition',choices=[('avec','Avec au moins un fait répondant aux conditions'),('sans','Sans aucun fait répondant aux conditions')]))
                    champ('relation',forms.ChoiceField(label='Sur',choices=[('personne','La même personne bénéficiaire'),('prise','La même prise en charge'),('menage','Le même ménage explicite')],help_text='Les conditions de ce bloc portent sur un même fait. Deux blocs peuvent porter sur deux faits différents. Sans identité connue, une absence de fait ne peut pas être affirmée.'))
                regles=[]
                for c in ('mouvement','portion')+ (('cohorte','lignes_vides') if cle=='mesure' else ()):
                    f=deepcopy(ancien.fields[c])
                    if not regle_pertinente(c,source,data.get(prefixe+'mesure'),data):
                        defaut={'mouvement':'chevauche','portion':'selection','cohorte':'tous','lignes_vides':False}[c]
                        if data.get(prefixe+c,defaut) in (None,'',defaut,False) or c=='lignes_vides' and data.get(prefixe+c) in ('False','false','0'):f.widget=forms.HiddenInput()
                    champ(c,f);regles.append(prefixe+c)
                try:nf=int(data.get(prefixe+'nombre_filtres',0))
                except (ValueError,TypeError):nf=0
                self.fields[prefixe+'nombre_filtres']=forms.IntegerField(min_value=0,max_value=20,initial=nf,widget=forms.HiddenInput)
                filtres=[]
                for j in range(1,max(0,min(nf,20))+1):
                    fs=[]
                    for c,nom in [('champ','filtre1'),('operation','operation1'),('valeur','valeur1')]:
                        k=f'{prefixe}f{j}_{c}';self.fields[k]=deepcopy(ancien.fields[nom]);fs.append(k)
                        if c=='champ':dimensions(self.fields[k],[source],data.get(k))
                    filtres.append(fs)
                self.parties[cle].append(dict(index=i,prefixe=prefixe,champs=[k for k in noms if k not in regles],regles=regles,filtres=filtres,nombre_filtres=prefixe+'nombre_filtres'))
        for nom in ('affichage','export_prioritaire'):ajouter(nom,deepcopy(ancien.fields[nom]),'afficher')
        ajouter('lignes',forms.ChoiceField(label='Une ligne détaillée par',choices=e.POPULATIONS,help_text='Ce choix organise les lignes détaillées ; il ne limite pas les faits utilisés par les mesures. Sur une ligne de personne : ses faits ; sur une ligne de ménage : les faits de ce ménage ; sur une ligne de prestation : les faits de sa prise en charge exacte.'),'afficher')
        if data.get('affichage')!='detail':self.fields['lignes'].widget=forms.HiddenInput()
        dims=list(e.disponibles(acteur).items())
        sources=[data.get(f'mesure{i}_source','repas') for i in range(1,len(self.parties['mesure'])+1)]
        for cle,groupe,maxi,mini in [('colonnes','afficher',11,0),('axes','classer',7,1)]:
            for i in range(1,nombre(cle,mini,maxi,1)+1):
                f=forms.ChoiceField(label=('Information affichée ' if cle=='colonnes' else 'Niveau de classement ')+str(i),choices=list(e.disponibles(acteur,informations=True).items()) if cle=='colonnes' else dims)
                dimensions(f,[data.get('lignes','personnes')] if cle=='colonnes' else sources,data.get(cle+str(i)))
                ajouter(cle+str(i),f,groupe)
        ajouter('sous_totaux',deepcopy(ancien.fields['sous_totaux']),'classer')
        # Les classes reprises d'un modèle restent éditables et attachées au niveau.
        for i in range(1,int(data.get('nombre_axes',1) or 1)+1 if str(data.get('nombre_axes',1)).isdigit() and int(data.get('nombre_axes',1))<=7 else 2):
            ajouter('classes'+str(i),forms.CharField(label='Classes du niveau '+str(i)+' (facultatives)',required=False,max_length=3000,widget=forms.Textarea(attrs={'rows':2}),help_text=ancien.fields['classes'].help_text),'classer')

        for i in range(1,min(7,max(1,int(self.fields['nombre_axes'].initial)))+1):
            cle='classes'+str(i)
            if cle not in self.fields:continue
            if not data.get(cle) and not numerique(data.get('axes'+str(i))):self.fields[cle].widget=forms.HiddenInput()


    def clean(self):
        d=super().clean()
        for cle in ('critere','mesure'):
            for b in self.parties[cle]:
                p=b['prefixe'];source=d.get(p+'source')
                if cle=='mesure' and d.get(p+'mesure') and not mesure_compatible(source,d[p+'mesure']):
                    self.add_error(p+'mesure','Ce calcul ne correspond pas aux éléments choisis. Choisissez un calcul compatible ou rétablissez les éléments précédents.')
                for fs in b['filtres']:
                    champ,operation,valeur=fs
                    if d.get(champ) and not e.dimension_compatible(source,d[champ]):self.add_error(champ,'Ce filtre ne correspond pas aux faits de ce bloc.')
                    if d.get(champ) and d.get(operation)!='inconnu' and not d.get(valeur):self.add_error(valeur,'Indiquez la valeur du filtre.')
        sources=[d.get(b['prefixe']+'source') for b in self.parties['mesure']]
        for cle in self.groupes['classer']:
            if cle.startswith('axes') and d.get(cle) and any(not e.dimension_compatible(src,d[cle]) for src in sources):
                self.add_error(cle,'Ce classement ne convient pas à toutes les mesures. Choisissez un classement commun ou utilisez des analyses séparées dans un assemblage.')
            if cle.startswith('classes'):
                try:e.classes(d.get(cle,''))
                except forms.ValidationError as exc:self.add_error(cle,exc)
        for cle in self.groupes['afficher']:
            if cle.startswith('colonnes') and d.get(cle) and not e.dimension_compatible(d.get('lignes'),d[cle]):self.add_error(cle,'Cette information ne correspond pas aux lignes détaillées choisies.')
        return d

    def definition(self):
        d=self.cleaned_data
        resultat={k:v for k,v in d.items() if k in ('debut','fin','reference','periode','decalage_debut','decalage_fin','reference_mode','affichage','lignes','combinaison','sous_totaux','filtre','export_prioritaire')}
        for cle in ('axes','colonnes'):
            resultat[cle]=[d[cle+str(i)] for i in range(1,d['nombre_'+cle]+1)]
        resultat['classes']=[d.get('classes'+str(i),'') for i in range(1,d['nombre_axes']+1)]
        for cle,dest in [('critere','criteres'),('mesure','mesures')]:
            resultat[dest]=[]
            for i in range(1,d['nombre_'+cle]+1):
                prefixe=f'{cle}{i}_'
                partie={k[len(prefixe):]:v for k,v in d.items() if k.startswith(prefixe) and not k[len(prefixe):].startswith(('f','nombre_'))}
                partie['filtres']=[{c:d[f'{prefixe}f{j}_{c}'] for c in ('champ','operation','valeur')} for j in range(1,d[prefixe+'nombre_filtres']+1) if d.get(f'{prefixe}f{j}_champ')]
                resultat[dest].append(partie)
        return jsonable(resultat)


def jsonable(d):
    import json
    return json.loads(a.encoder(d))


def mesure_compatible(source,code):
    if code in ('quantite','minimum','maximum','moyenne'):return source in ('sejours','fragments_sejour','affectations','repas','aides','ressources','dettes','couts','imputations')
    if code in (*e.mesures.DUREES,'participations'):return source=='sejours'
    if code in e.mesures.NUITS_DISTINCTES:return source in ('sejours','fragments_sejour')
    if code in e.mesures.NUITEES:return source in ('sejours','affectations')
    if code in ('adultes_declares','enfants_declares','grossesses_declarees'):return source=='appels'
    return True


def regle_pertinente(cle,source,mesure,data):
    if cle=='mouvement':return source in ('prises','sejours','accords_hebergement','accords_repas')
    if cle=='portion':return source=='sejours'
    if cle=='cohorte':
        from .cohortes_exploration import POPULATIONS,MESURES
        return source in POPULATIONS and mesure in MESURES
    if cle=='lignes_vides':
        axes=[v for k,v in data.items() if k.startswith('axes') and v not in ('','total')]
        return source=='repas' and bool(axes) and set(axes)<={'mois','type'}
    return True


def numerique(cle):
    if cle in ('age','quantite','duree','duree_selection','adultes_declares','enfants_declares','grossesses_declarees','quantite_facturee','prix_unitaire'):return True
    if not cle or '.' not in cle:return False
    groupe,champ=cle.split('.',1)
    if groupe not in e.GROUPES:return False
    from django.db import models
    from django.core.exceptions import FieldDoesNotExist
    try:return isinstance(e.GROUPES[groupe][0]._meta.get_field(champ),(models.IntegerField,models.DecimalField,models.FloatField))
    except FieldDoesNotExist:return False
