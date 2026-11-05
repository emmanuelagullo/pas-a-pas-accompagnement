from copy import deepcopy
from django import forms
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.shortcuts import get_object_or_404
from django.urls import reverse
from personnes.champs_saisie import FormulaireMetier
from .models import Service
from . import services as s, collecte as c
from .profils_collectifs import categories_defaut
from .views import formulaire

class CollecteForm(FormulaireMetier):
    attendu=forms.CharField(widget=forms.HiddenInput)
    confirmer_collecte = forms.BooleanField(label="Confirmer le changement de collecte", required=False)
    profil=forms.ChoiceField(label='Partir d’un profil',choices=[('detail','Suivi personnel détaillé'),('menage','Informations communes au ménage'),('adultes','Informations personnelles des adultes')],required=False)
    def __init__(self,*args,service,regles=None,**kw):
        super().__init__(*args,**kw)
        self.service=service
        self.initial['attendu']=s.jeton(service)
        self.initial['profil']='detail'
        regles=regles or service.collecte_rubriques or c.profil('detail')
        populations=c.POPULATIONS+ [('categorie:'+x['code'],x['libelle']) for x in service.profil_collectif.get('categories',categories_defaut())]
        self.lignes=[]
        for code,(titre,champs) in c.RUBRIQUES.items():
            regle = regles[code]
            possibles = ('menage',) if code == 'projet' else (
                ('personne', 'menage', 'deux') if champs else ('personne',)
            )
            portees = [(valeur, libelle) for valeur, libelle in c.PORTEES if valeur in possibles]
            self.fields[code+'_active'] = forms.BooleanField(
                label=titre+' — demander cette information', required=False,
                initial=regle['portee'] != 'non', disabled=code == 'identite',
            )
            self.fields[code+'_portee'] = forms.ChoiceField(
                label=titre+' — où enregistrer l’information ?', choices=portees,
                initial=regle.get('portee_preferee', possibles[0]) if regle['portee'] == 'non' else regle['portee'],
                disabled=code == 'identite',
            )
            self.fields[code+'_population'] = forms.ChoiceField(
                label=titre+' — quelles personnes sont concernées ?',
                choices=c.POPULATIONS[:1] if code == 'identite' else populations,
                initial=regle['population'], required=False, disabled=code == 'identite',
            )
            self.lignes.append((titre, code))

    @property
    def lignes_collecte(self):
        return [
            (titre, self[code+'_active'], self[code+'_portee'], self[code+'_population'], code == 'identite')
            for titre, code in self.lignes
        ]

    def clean(self):
        d = super().clean()
        if self.errors:
            return d
        regles = {}
        for code in c.RUBRIQUES:
            active = d.pop(code+'_active')
            portee = d.pop(code+'_portee')
            regle = {'portee': portee if active else 'non', 'population': d.pop(code+'_population') or 'tous'}
            if not active:
                regle['portee_preferee'] = portee
            regles[code] = regle
        c.verifier(regles,self.service.profil_collectif.get('categories',categories_defaut()))
        avant = self.service.collecte_rubriques or c.profil('detail')
        impacts = [
            c.RUBRIQUES[code][0] for code, regle in regles.items()
            if (regle['portee'], regle['population'] if regle['portee'] in ('personne', 'deux') else None)
            != (avant[code]['portee'], avant[code]['population'] if avant[code]['portee'] in ('personne', 'deux') else None)
        ]
        confirmation = d.pop('confirmer_collecte')
        if impacts and not confirmation:
            self.add_error('confirmer_collecte', 'Confirmez les changements pour ' + ', '.join(impacts) + '.')
        d.pop('profil',None);d['regles']=regles
        return d

@never_cache
@login_required
@require_http_methods(['GET','POST'])
def configurer(request,service_pk):
    s.exiger_gestion(request.user)
    service=get_object_or_404(Service,pk=service_pk)
    profil_charge = request.method == 'POST' and 'appliquer_profil' in request.POST
    if profil_charge:
        choix=request.POST.get('profil','detail')
        choix=choix if choix in ('menage','adultes','detail') else 'detail'
        f=CollecteForm(service=service,regles=c.profil(choix))
        f.initial['profil']=choix
    else:f=CollecteForm(request.POST if request.method=='POST' else None,service=service)
    def sauver(attendu,regles):
        s.reserver(service,attendu)
        c.verifier(regles,service.profil_collectif.get('categories',categories_defaut()))
        avant=deepcopy(service.collecte_rubriques)
        service.collecte_rubriques=regles;service.save(update_fields=['collecte_rubriques'])
        s.journal(request.user,service,'collecte_rubriques',avant,regles)
    return formulaire(request, f, 'Situation sociale et projet', sauver,
                      reverse('acteurs:service', args=[service.pk]) + f'#service-{service.pk}-rubriques',
                      service=service, profil_charge=profil_charge)
