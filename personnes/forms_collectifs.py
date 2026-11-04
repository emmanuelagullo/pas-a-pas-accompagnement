from datetime import date
from decimal import Decimal
from django import forms
from django.utils import timezone
from django.db.models import Q
from .champs_saisie import FormulaireMetier
from . import models as m, collectifs as c

DATE=forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'})

class CompositionForm(FormulaireMetier):
    debut=forms.DateField(label='Composition à la date du',widget=DATE)
    reference=forms.ModelChoiceField(m.Personne.objects.none(),label='Personne de référence pour la collecte')
    identifies=forms.ModelMultipleChoiceField(m.Personne.objects.none(),label='Personnes identifiées comprises dans le groupe',widget=forms.CheckboxSelectMultiple,required=False)
    logement=forms.CharField(label='Logement du ménage',max_length=240,required=False)
    revenu=forms.DecimalField(label='Revenu mensuel du ménage',max_digits=14,decimal_places=2,min_value=0,required=False)
    dette=forms.DecimalField(label='Total de dettes du ménage',max_digits=14,decimal_places=2,min_value=0,required=False)
    devise=forms.RegexField('[A-Z]{3}',label='Devise',max_length=3,initial='EUR')
    telephone=forms.CharField(label='Téléphone commun',max_length=80,required=False)
    courriel=forms.EmailField(label='Courriel commun',required=False)
    projet=forms.CharField(label='Projet collectif',max_length=4000,widget=forms.Textarea(attrs={'rows':3}),required=False)
    source=forms.CharField(label='Source — facultative',max_length=160,required=False)
    actualiser=forms.BooleanField(label='Actualiser aussi la composition du ménage',required=False)
    attendu=forms.CharField(widget=forms.HiddenInput)

    def __init__(self,*args,objet,jour,**kwargs):
        self.objet=objet;self.cfg=c.profil(objet);self.jour=jour
        super().__init__(*args,**kwargs)
        q=objet.beneficiaires.all() if isinstance(objet,m.Accompagnement) else m.Personne.objects.filter(appartenances__menage=objet).distinct()
        self.fields['reference'].queryset=q;self.fields['identifies'].queryset=q
        ancienne=c.composition(objet,jour)
        self.initial.update(debut=jour,attendu=c.jeton(objet))
        if ancienne:
            self.initial.update({k:getattr(ancienne,k) for k in (*c.SOCIAUX,'devise','source')})
            self.initial.update(reference=ancienne.reference_id,identifies=list(ancienne.identifies.values_list('pk',flat=True)))
        elif q.count()==1:self.initial['reference']=q.first().pk
        if self.cfg['identification']=='reference':
            del self.fields['identifies']
        for k in c.SOCIAUX:
            if k not in self.cfg['rubriques']:del self.fields[k]
        if not isinstance(objet,m.Accompagnement):del self.fields['actualiser']
        self.composition_champs=[]
        for cat in ([*self.cfg['categories'],{'code':'inconnu','libelle':'Âge non précisé'}] if self.cfg['identification']!='tous' else []):
            nom='nombre_'+cat['code']
            self.fields[nom]=forms.IntegerField(label=cat['libelle']+' — personnes supplémentaires non identifiées',min_value=0,max_value=1000,initial=0)
            if ancienne:self.initial[nom]=sum(x['nombre'] for x in ancienne.complements if x['categorie']==cat['code'] and x['age'] is None and not x['naissance'])
            self.composition_champs.append(nom)
        ages=[x for x in ancienne.complements if x['age'] is not None or x['naissance']] if ancienne else []
        self.lignes_age=[]
        for i in (range(max(4,len(ages))) if self.cfg['identification']!='tous' else []):
            an='age_'+str(i);dn='naissance_'+str(i)
            self.fields[an]=forms.IntegerField(label='Âge déclaré',min_value=0,max_value=120,required=False)
            self.fields[dn]=forms.DateField(label='Ou date de naissance',widget=DATE,required=False)
            if i<len(ages):self.initial.update({an:ages[i]['age'],dn:ages[i]['naissance']})
            self.lignes_age.append((an,dn))
        self.saisie_periode=('debut',)

    def clean(self):
        d=super().clean()
        if self.cfg['identification']=='reference' and d.get('reference'):d['identifies']=[d['reference']]
        complements=[]
        for nom in self.composition_champs:
            n=d.pop(nom,0)
            if n:complements.append({'categorie':nom[7:],'nombre':n,'age':None,'naissance':''})
        # Les informations d'âge/naissance non individualisées sont des lignes datées.
        for an,dn in self.lignes_age:
            age=d.pop(an,None);naissance=d.pop(dn,None)
            if age is not None and naissance:self.add_error(an,'Renseignez un âge ou une naissance, pas les deux.')
            elif age is not None or naissance:complements.append({'categorie':'inconnu','nombre':1,'age':age,'naissance':naissance.isoformat() if naissance else ''})
        d['complements']=complements
        return d

    @property
    def champs_principaux(self):
        exclus={n for pair in self.lignes_age for n in pair}
        return [x for x in self if x.name not in exclus]
    @property
    def ages_complementaires(self):return [(self[a],self[n]) for a,n in self.lignes_age]


class PrestationForm(FormulaireMetier):
    debut=forms.DateField(label='Début',widget=DATE)
    fin_prevue=forms.DateField(label='Fin prévue — facultative',widget=DATE,required=False)
    arrivee=forms.DateField(label='Arrivée effective — vide si seulement prévu',widget=DATE,required=False)
    lieu=forms.ModelChoiceField(m.LieuHebergement.objects.none(),label='Chambre ou logement commun',required=False)
    petits_dejeuners=forms.BooleanField(label='Petits déjeuners associés',required=False)
    prestataire=forms.ModelChoiceField(m.Partenaire.objects.none(),label='Lieu / organisme de restauration',required=False)
    dejeuner=forms.BooleanField(label='Déjeuner',initial=True,required=False)
    diner=forms.BooleanField(label='Dîner',initial=True,required=False)
    premier=forms.ChoiceField(label='Premier repas',choices=[('dejeuner','Déjeuner'),('diner','Dîner')])
    dernier=forms.ChoiceField(label='Dernier repas',choices=[('dejeuner','Déjeuner'),('diner','Dîner')],initial='diner')
    devise=forms.RegexField('[A-Z]{3}',label='Devise',max_length=3,initial='EUR')
    attendu=forms.CharField(widget=forms.HiddenInput)

    def __init__(self,*args,prise,nature,comp,acteur,prestation=None,**kwargs):
        self.comp=comp;self.nature=nature;self.prestation=prestation;self.acteur=acteur
        super().__init__(*args,**kwargs)
        cfg=c.profil(prise);v=prestation.courante if prestation else None
        self.initial.update(debut=prise.debut,fin_prevue=prise.fin_prevue,arrivee=min(timezone.localdate(),max(prise.debut,timezone.localdate())),attendu=c.jeton(prestation or prise))
        if v:self.initial.update(c.valeurs_version(v))
        if nature=='hebergement':
            for k in ('prestataire','dejeuner','diner','premier','dernier'):del self.fields[k]
            if acteur.has_perm('personnes.view_lieuhebergement'):self.fields['lieu'].queryset=m.LieuHebergement.objects.all()
            else:del self.fields['lieu']
            if not cfg['petits_dejeuners']:del self.fields['petits_dejeuners']
            self.fields['fin_prevue'].label='Départ prévu — date exclue'
        else:
            for k in ('arrivee','lieu','petits_dejeuners'):del self.fields[k]
            self.fields['fin_prevue'].label='Dernier jour prévu — repas de fin compris'
            if acteur.has_perm('personnes.view_partenaire'):self.fields['prestataire'].queryset=m.Partenaire.objects.all()
            else:del self.fields['prestataire']
        self.couverts=[];self.tarifs={}
        nombres=c.effectifs(comp,comp.debut)
        anciennes={x.categorie:x for x in v.couverts.all()} if v else {}
        for cat in [*comp.categories,{'code':'inconnu','libelle':'Âge non précisé'}]:
            cle=cat['code'];n='couverts_'+cle;p='prix_'+cle
            self.fields[n]=forms.IntegerField(label=cat['libelle'],min_value=0,max_value=1000,initial=nombres.get(cle,0))
            self.fields[p]=forms.DecimalField(label='Prix par repas — '+cat['libelle'],min_value=0,max_digits=14,decimal_places=4,required=False)
            if cle in anciennes:self.initial.update({n:anciennes[cle].nombre,p:anciennes[cle].prix})
            self.couverts.append((cle,n,p))
        if nature=='hebergement' and not cfg['petits_dejeuners']:
            for _,n,p in self.couverts:
                del self.fields[n];del self.fields[p]
            self.couverts=[]
        self.prix_proposes={}
        if nature=='restauration' and acteur.has_perm('personnes.view_partenaire'):
            prestataires=list(self.fields['prestataire'].queryset)
            if not v and len(prestataires)==1:self.initial['prestataire']=prestataires[0].pk
            jour=self.initial.get('debut') or prise.debut
            if isinstance(jour,str):jour=date.fromisoformat(jour)
            for pr in prestataires:
                tarifs=c.tarifs_proposes(acteur,pr.pk,jour,comp.categories,self.initial.get('devise','EUR'))
                self.prix_proposes[str(pr.pk)]={cle:str(t.montant) for cle,t in tarifs.items()}
            if not v:
                for cle,_,p in self.couverts:
                    prix=self.prix_proposes.get(str(self.initial.get('prestataire','')),{}).get(cle)
                    if prix is not None:self.initial[p]=prix
        self.saisie_periode=('debut','fin_prevue')
        self.selection_champs=[]
        if cfg[nature]=='option' and not prestation:
            self.fields['restreindre']=forms.BooleanField(label='Cette prestation concerne certaines personnes identifiées seulement',required=False)
            self.fields['selection']=forms.ModelMultipleChoiceField(comp.identifies.all(),label='Personnes concernées',widget=forms.CheckboxSelectMultiple,required=False)
            self.fields['reference_selection']=forms.ModelChoiceField(comp.identifies.all(),label='Personne de référence de cette sélection',required=False)
            self.selection_champs=['restreindre','selection','reference_selection']

    @property
    def champs_principaux(self):
        exclus={n for _,a,b in self.couverts for n in (a,b)}|set(self.selection_champs)
        return [x for x in self if x.name not in exclus]

    @property
    def lignes_couverts(self):return [(cle,self[n],self[p]) for cle,n,p in self.couverts]

    @property
    def champs_selection(self):return [self[n] for n in self.selection_champs]

    def clean(self):
        d=super().clean();lignes=[]
        proposes=c.tarifs_proposes(self.acteur,getattr(d.get('prestataire'),'pk',None),d.get('debut') or self.comp.debut,self.comp.categories,d.get('devise','EUR')) if self.nature=='restauration' else {}
        for cle,n,p in self.couverts:
            nombre=d.pop(n,0);prix=d.pop(p,None)
            tarif=proposes.get(cle)
            lignes.append({'categorie':cle,'nombre':nombre,'prix':prix,'tarif':tarif if tarif and tarif.montant==prix else None})
        d['couverts']=lignes
        if self.selection_champs:
            restreindre=d.pop('restreindre',False)
            if not restreindre:
                d.pop('selection',None);d.pop('reference_selection',None)
            elif not d.get('selection') or not d.get('reference_selection'):
                self.add_error('selection','Choisissez les personnes et leur personne de référence.')
        if self.nature=='restauration':
            actifs=[x for x in ('dejeuner','diner') if d.get(x)]
            if len(actifs)==1:d['premier']=d['dernier']=actifs[0]
        return d


class ActionForm(FormulaireMetier):
    attendu=forms.CharField(widget=forms.HiddenInput)
    date=forms.DateField(widget=DATE,required=False)
    motif=forms.CharField(label='Précision — facultative',max_length=240,required=False)
    def __init__(self,*args,prestation,action,**kwargs):
        super().__init__(*args,**kwargs)
        self.initial['attendu']=c.jeton(prestation)
        if action=='annulation':
            del self.fields['date'];self.fields['motif'].required=True;self.fields['motif'].label='Motif d’annulation'
        else:
            self.fields['date'].required=True
            self.fields['date'].label='Nouvelle fin prévue' if action=='prolongation' else 'Départ effectif'
            self.initial['date']=timezone.localdate()


class MouvementForm(FormulaireMetier):
    attendu=forms.CharField(widget=forms.HiddenInput)
    debut=forms.DateField(label='Date du changement',widget=DATE)
    fin=forms.DateField(label='Retour prévu / fin exclue — facultative',widget=DATE,required=False)
    lieu=forms.ModelChoiceField(m.LieuHebergement.objects.none(),label='Nouveau lieu commun',required=False)
    def __init__(self,*args,prestation,action,acteur,**kwargs):
        super().__init__(*args,**kwargs);self.initial.update(attendu=c.jeton(prestation),debut=timezone.localdate())
        if action=='lieu':
            del self.fields['fin'];self.fields['lieu'].required=True
            if acteur.has_perm('personnes.view_lieuhebergement'):self.fields['lieu'].queryset=m.LieuHebergement.objects.all()
        else:del self.fields['lieu']
