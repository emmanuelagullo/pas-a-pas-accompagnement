"""Exploration bornée de populations explicites ; aucun SQL ou chemin de champ libre."""
from collections import defaultdict
from decimal import Decimal,InvalidOperation,ROUND_HALF_UP
from itertools import product
from datetime import timedelta
from django.core.exceptions import ValidationError,PermissionDenied
from django.db.models import Q
from django.utils import timezone
from . import models as m,suivi,dossier_complet as dc

INCONNU='Non renseigné'
POPULATIONS=[('personnes','Personnes enregistrées — situation à la référence'),('menages','Ménages enregistrés — membres à la référence'),('prises','Prises en charge chevauchant la période'),('demandes','Demandes — dernière version chevauchant la période'),('sejours','Épisodes de séjour chevauchant la période'),('repas','Distributions effectives de repas'),('aides','Remises effectives des autres prestations'),('appels','Appels 115'),('ressources','Ressources déclarées applicables à la référence'),('dettes','Dettes déclarées applicables à la référence'),('couts','Composantes de coût — dernières versions'),('imputations','Imputations — dernières versions')]
BASE={'complement115':'Information complémentaire 115 déclarée','date_saisie':'Date de saisie de l’objet','date_version':'Date de saisie de la version affichée','appelant':'Appelant déclaré / répertoire','auteur':'Auteur de saisie initiale','auteur_version':'Auteur de la dernière version','quantite':'Quantité / montant porté par l’objet','phase':'Phase de calcul financier','financeur':'Financeur explicite','budget':'Budget / dispositif','prescripteur':'Prescripteur financier','signataire':'Signataire désigné','total':'Ensemble','mois':'Mois du fait / début','jour':'Jour du fait / début','heure':'Heure d’appel','type':'Type / service / activité déclarée','etat':'État déclaré','motif':'Motif principal / demande','secondaire':'Demandes secondaires 115','reponse':'Réponses 115','origine':'Lieu / origine déclaré','orientation':'Orientation déclarée','unite':'Unité de quantité','duree':'Durée de l’épisode clos (jours)','age':'Âge exact à la référence','precision_naissance':'Précision de naissance','entree_connue':'Première entrée connue / retour connu','adultes_declares':'Adultes déclarés par appel','enfants_declares':'Enfants déclarés par appel','grossesses_declarees':'Grossesses déclarées par appel'}
# Schémas déjà livrés ; les numéros administratifs et textes libres ne sont pas des axes.
GROUPES={
 'identite':(m.ComplementIdentite,('sexe_declare','naissance_lieu','naissance_ville','naissance_pays','nationalites','apatridie_declaree'),('view_complementidentite','view_revisioncomplementidentite')),
 'famille':(m.DeclarationFamiliale,('situation_familiale','rapports_parentaux','fratrie','enfants_a_charge','enfants_non_a_charge','grossesse'),('view_declarationfamiliale','view_revisiondeclarationfamiliale')),
 'administration':(m.SituationAdministrative,tuple(c for c in dc.ADMIN_CHAMPS if c not in ('numero_ss','numero_caf')),('view_situationadministrative','view_revisionsituationadministrative')),
 'coordonnees':(m.CoordonneesPersonnelles,('ville','pays','code_postal'),('view_coordonneespersonnelles','view_revisioncoordonneespersonnelles'))}
for code,r in dc.RUBRIQUES.items():
    champs=tuple(c for c in r.champs if c not in ('reference','identifiant','reference_decision','precision_portee','representant_personne','representant_intervenant','interlocuteur'))
    GROUPES[code]=(r.modele,champs,tuple(p.removeprefix('personnes.') for p in dc.droits_lecture(code)))
DIMENSIONS={**BASE,**{g+'.'+c:g.replace('_',' ').capitalize()+' — '+str(model._meta.get_field(c).verbose_name) for g,(model,cs,ps) in GROUPES.items() for c in cs},**{'social.'+c:label+' (histoire personnelle)' for c,label in m.SituationSociale.DIMENSIONS}}


def disponibles(acteur):
    suivi.exiger(acteur,'view_personne')
    return {k:v for k,v in DIMENSIONS.items() if '.' not in k or acteur.has_perms(['personnes.'+p for p in (('view_situationpersonnelle',) if k.startswith('social.') else GROUPES[k.split('.')[0]][2])])}


def categorie_valeur(objet,champ,valeur):
    field=objet._meta.get_field(champ)
    if field.choices:return str(getattr(objet,'get_'+champ+'_display')())
    if isinstance(valeur,bool):return 'Oui' if valeur else 'Non'
    return valeur if isinstance(valeur,(int,Decimal)) else str(valeur)


def selection_appels(acteur,d,personne=None,menage=None):
    from .vues_appels115 import visibles
    lignes=[]
    for a,v in visibles(acteur):
        if a.annule_le and not d.get('annules') or not d['debut']<=v.date<d['fin']:continue
        if personne and str(personne) not in {str(p.pk) for p in v.beneficiaires.all()}:continue
        if menage and str(v.menage_id)!=str(menage):continue
        if any(d.get(c) and getattr(v,c).casefold()!=d[c].casefold() for c in ('motif_principal','type_appelant','lieu_appel','etat_reponse')):continue
        if d.get('secondaire') and d['secondaire'].casefold() not in {x.casefold() for x in v.demandes_secondaires}:continue
        if d.get('reponse') and d['reponse'].casefold() not in {x.casefold() for x in v.reponses}:continue
        if d.get('heure_min') is not None and (v.heure is None or v.heure.hour<d['heure_min']):continue
        if d.get('heure_max') is not None and (v.heure is None or v.heure.hour>=d['heure_max']):continue
        texte=' '.join([v.appelant_libre,str(v.appelant_personne or v.appelant_intervenant or v.appelant_organisme or ''),v.motif_principal,v.lieu_appel,v.details,v.information_complementaire,v.telephone,' '.join(v.demandes_secondaires+v.reponses),str(v.orientation or v.orientation_declaree),*(str(p) for p in v.beneficiaires.all())]).casefold()
        if any(mot.casefold() not in texte for mot in d.get('q','').split()):continue
        lignes.append({'appel':a,'version':v})
    return sorted(lignes,key=lambda x:(x['version'].date,x['version'].heure.isoformat() if x['version'].heure else '',str(x['appel'].pk)),reverse=True)


def ligne(pk,date,ps,menages,*,saisie=None,version_saisie=None,**valeurs):
    return dict(id=str(pk),date=date,personnes={p.pk for p in ps},menages=set(menages),valeurs={'total':['Ensemble'],'mois':[date.strftime('%Y-%m')],'jour':[date.isoformat()],'date_saisie':[timezone.localdate(saisie).isoformat()] if saisie else [],'date_version':[timezone.localdate(version_saisie).isoformat()] if version_saisie else [],**valeurs},quantite=Decimal('0'),unite='sans quantité additive')


def population(acteur,d):
    debut,fin=d['debut'],d['fin'];ref=d['reference'];code=d['population'];lignes=[]
    suivi.exiger(acteur,'view_personne')
    if code not in ('personnes','ressources','dettes'):suivi.exiger(acteur,'view_menage')
    if code=='personnes':
        appartenances=defaultdict(list)
        if acteur.has_perm('personnes.view_menage'):
            for lien in m.Appartenance.objects.filter(debut__lte=ref).filter(Q(fin__isnull=True)|Q(fin__gt=ref)):appartenances[lien.personne_id].append(lien.menage_id)
        for p in m.Personne.objects.all():lignes.append(ligne(p.pk,ref,[p],appartenances[p.pk],saisie=p.cree_le))
    elif code=='menages':
        for menage in m.Menage.objects.prefetch_related('appartenances__personne'):
            ps={x.personne for x in menage.appartenances.all() if x.debut<=ref and (x.fin is None or x.fin>ref)}
            lignes.append(ligne(menage.pk,ref,ps,[menage.pk],saisie=menage.cree_le))
    elif code=='prises':
        suivi.exiger(acteur,'view_accompagnement')
        for a in m.Accompagnement.objects.filter(debut__lt=fin).filter(Q(fin__isnull=True)|Q(fin__gt=debut)).prefetch_related('beneficiaires','informations'):
            info=a.informations.first();ps=list(a.beneficiaires.all())
            x=ligne(a.pk,a.debut,ps,[a.menage_id],saisie=a.cree_le,version_saisie=info.enregistre_le if info else None,etat=['Close' if a.fin else 'Ouverte'],type=[info.get_activite_display() if info else INCONNU],origine=[info.provenance if info else INCONNU],orientation=[info.orientation_sortie if info else INCONNU],motif=[info.motif_entree if info else INCONNU]);lignes.append(x)
    elif code=='demandes':
        from .parcours import exiger
        exiger(acteur,'demandes')
        for a in m.DemandeAccueil.objects.filter(annule_le__isnull=True).prefetch_related('beneficiaires','versions'):
            v=a.versions.first()
            if v and v.debut<fin and (v.fin is None or v.fin>debut):lignes.append(ligne(a.pk,v.debut,a.beneficiaires.all(),[a.menage_id] if a.menage_id else [],saisie=a.cree_le,version_saisie=v.enregistre_le,etat=[v.get_etat_display()],motif=[v.motif_demande],origine=[v.provenance]))
    elif code=='sejours':
        suivi.exiger(acteur,'view_accompagnement','view_accordhebergement','view_sejour')
        from .continuite_hebergement import episodes
        premieres={}
        for a in m.Sejour.objects.filter(origine_collective__isnull=True).prefetch_related('beneficiaires'):
            for p in a.beneficiaires.all():premieres[p.pk]=min(premieres.get(p.pk,a.debut),a.debut)
        for a,f in episodes():
            if a.debut>=fin or f and f<=debut:continue
            ps=list(a.beneficiaires.all());x=ligne(a.pk,a.debut,ps,[a.accord.accompagnement.menage_id],saisie=a.cree_le,etat=['Clos' if f else 'En cours'],duree=[(f-a.debut).days] if f else [],entree_connue=list({'Première entrée connue' if premieres[p.pk]==a.debut else 'Retour connu' for p in ps}))
            x['_entrees']={p.pk:['Première entrée connue' if premieres[p.pk]==a.debut else 'Retour connu'] for p in ps}
            fragments=[a,*a.continuations.all()];x['quantite']=sum((Decimal(max(0,(min(s.fin or fin,fin)-max(s.debut,debut)).days)*s.beneficiaires.count()) for s in fragments),Decimal('0'));x['unite']='personne-nuit de séjour (absences non déduites)';lignes.append(x)
    elif code=='repas':
        from .repas import droit
        droit(acteur,'view_repasdistribue')
        for r in m.RepasDistribue.objects.filter(annule_le__isnull=True,date__gte=debut,date__lt=fin).select_related('accord__accompagnement','beneficiaire'):
            x=ligne(r.pk,r.date,[r.beneficiaire],[r.accord.accompagnement.menage_id],saisie=r.cree_le,type=[r.accord.get_service_display()],etat=[r.categorie_declaree],origine=[r.accord.prestataire]);x.update(quantite=Decimal(r.quantite),unite='repas');lignes.append(x)
    elif code=='aides':
        from .aides import droit
        droit(acteur)
        for r in m.RemiseAide.objects.filter(annule_le__isnull=True,accord__annule_le__isnull=True,date__gte=debut,date__lt=fin).select_related('accord__accompagnement').prefetch_related('beneficiaires'):
            x=ligne(r.pk,r.date,r.beneficiaires.all(),[r.accord.accompagnement.menage_id],saisie=r.enregistre_le,type=[r.accord.libelle],etat=[r.accord.get_nature_display()]);x.update(quantite=r.quantite,unite=r.accord.unite);lignes.append(x)
    elif code in ('ressources','dettes'):
        dc.exiger_lecture(acteur,code)
        for r in dc.a_date(code,m.Personne.objects.all(),ref).select_related('personne'):
            x=ligne(r.pk,ref,[r.personne],[],saisie=r.enregistre_le,type=[r.libelle] if code=='ressources' else [r.creancier],etat=[r.get_etat_display()])
            x['quantite']=r.montant
            x['unite']=r.devise+' / '+(r.periodicite or 'périodicité non renseignée') if code=='ressources' else r.devise+' / '+r.get_nature_display()
            for c in GROUPES[code][1]:
                v=getattr(r,c);x['valeurs'][code+'.'+c]=[categorie_valeur(r,c,v)] if v is not None and v!='' else []
            lignes.append(x)
    elif code in ('couts','imputations'):
        from . import financements
        financements.droit(acteur)
        from django.db.models import Max
        derniers=m.VersionFinancement.objects.values('financement_id').annotate(n=Max('version'))
        for dernier in derniers:
            v=m.VersionFinancement.objects.select_related('financement__hebergement__accompagnement','financement__repas__accompagnement','financement__aide__accompagnement','prescripteur','signataire').get(financement_id=dernier['financement_id'],version=dernier['n']);a=v.financement.accord;financements.droit(acteur,a)
            ps=list(a.beneficiaires.all())
            if a.annule_le:continue
            if code=='couts':sources=v.lignes.filter(date__gte=debut,date__lt=fin)
            else:sources=v.imputations.all() if v.debut<fin and (v.fin is None or v.fin>debut) else []
            for c in sources:
                x=ligne(c.pk,c.date if code=='couts' else v.debut,ps,[a.accompagnement.menage_id],saisie=v.enregistre_le,version_saisie=v.enregistre_le,phase=[c.get_phase_display()],type=[c.libelle if code=='couts' else {'hebergement':'Hébergement','repas':'Repas','aide':'Autre prestation'}[v.financement.nature]],etat=[c.categorie] if code=='couts' else [],prescripteur=[str(v.prescripteur or '')],signataire=[str(v.signataire or '')],financeur=[str(c.financeur)] if code=='imputations' else [],budget=[c.budget] if code=='imputations' else [])
                x.update(quantite=c.montant,unite=v.devise+' / '+c.phase);lignes.append(x)
    elif code=='appels':
        for r in selection_appels(acteur,{**d,'annules':False}):
            a,v=r['appel'],r['version'];lignes.append(ligne(a.pk,v.date,v.beneficiaires.all(),[v.menage_id] if v.menage_id else [],saisie=a.enregistre_le,version_saisie=v.enregistre_le,appelant=[str(v.appelant_personne or v.appelant_intervenant or v.appelant_organisme or v.appelant_libre)],auteur=[str(a.auteur)],auteur_version=[str(v.auteur)],complement115=[v.information_complementaire],heure=[v.heure.hour] if v.heure else [],type=[v.get_type_appelant_display()],etat=[v.get_etat_reponse_display()],motif=[v.motif_principal],secondaire=v.demandes_secondaires,reponse=v.reponses,origine=[v.lieu_appel],orientation=[str(v.orientation or v.orientation_declaree)],**{c:[getattr(v,c)] if getattr(v,c) is not None else [] for c in ('adultes_declares','enfants_declares','grossesses_declarees')}))
    if len(lignes)>10000:raise ValidationError('Plus de 10 000 objets dans cette sélection : réduisez la période ou choisissez les rapports métier spécialisés. Aucun résultat tronqué n’est affiché.')
    for x in lignes:
        x['valeurs']['unite']=[x['unite']]
        x['valeurs']['quantite']=[x['quantite']] if x['quantite'] is not None else []
    return lignes


def enrichir(acteur,lignes,cles,ref):
    autorise=disponibles(acteur)
    if any(c not in autorise for c in cles if c):raise PermissionDenied
    ids={p for l in lignes for p in l['personnes']};personnes={p.pk:p for p in m.Personne.objects.filter(pk__in=ids)}
    cartes=defaultdict(lambda:defaultdict(list))
    for p in personnes.values():
        cartes[p.pk]['precision_naissance']=[p.get_precision_naissance_display() or INCONNU]
        cartes[p.pk]['age']=[]
        if p.precision_naissance=='exacte' and p.date_naissance and p.date_naissance<=ref:
            cartes[p.pk]['age']=[ref.year-p.date_naissance.year-((ref.month,ref.day)<(p.date_naissance.month,p.date_naissance.day))]
    groupes={c.split('.')[0] for c in cles if '.' in c}
    for g in groupes:
        if g=='social':
            for x in m.SituationPersonnelle.objects.filter(personne_id__in=ids,debut__lte=ref).filter(Q(fin__isnull=True)|Q(fin__gt=ref)):
                cartes[x.personne_id]['social.'+x.dimension].append(x.valeur)
            continue
        model,champs,droits=GROUPES[g];qs=model.objects.filter(personne_id__in=ids,debut__lte=ref).filter(Q(fin__isnull=True)|Q(fin__gt=ref))
        if any(f.name=='annule_le' for f in model._meta.fields):qs=qs.filter(annule_le__isnull=True)
        fks=[f.name for f in model._meta.fields if f.is_relation and f.name!='personne'];qs=qs.select_related(*fks)
        for x in qs:
            for c in champs:
                valeur=getattr(x,c);valeurs=valeur if isinstance(valeur,list) else [valeur]
                cartes[x.personne_id][g+'.'+c].extend(categorie_valeur(x,c,v) for v in valeurs if v not in (None,''))
    for x in lignes:
        propres=set(x['valeurs'])
        for c in cles:
            if (c in ('age','precision_naissance') or '.' in c) and c not in propres:x['valeurs'][c]=list({v for p in x['personnes'] for v in cartes[p][c]})
        x['_par_personne']={p:{**x['valeurs'],**{c:cartes[p][c] for c in cles if personnelle(c) and c not in propres},**({'entree_connue':x['_entrees'][p]} if p in x.get('_entrees',{}) else {})} for p in x['personnes']}


def personnelle(c):return c in ('age','precision_naissance','entree_connue') or '.' in c


def classes(texte):
    groupes=[]
    for ligne in texte.splitlines():
        if not ligne.strip():continue
        try:
            nom,mini,maxi=ligne.split('|');a=Decimal(mini.strip()) if mini.strip() else None;b=Decimal(maxi.strip()) if maxi.strip() else None
        except (ValueError,InvalidOperation):raise ValidationError('Classes : une ligne « nom | minimum inclus | maximum exclu ».')
        if not nom.strip() or len(nom)>80 or a is not None and not a.is_finite() or b is not None and not b.is_finite() or a is not None and b is not None and b<=a:raise ValidationError('Classe vide, borne non finie ou intervalle invalide.')
        for _,c,e in groupes:
            if (b is None or c is None or c<b) and (e is None or a is None or a<e):raise ValidationError('Les classes numériques ne doivent pas se chevaucher.')
        groupes.append((nom.strip(),a,b))
    if len(groupes)>20 or len({g[0] for g in groupes})!=len(groupes):raise ValidationError('Au plus 20 classes aux noms distincts.')
    return groupes


def valeurs(x,c):return list({v for v in x['valeurs'].get(c,[]) if v not in ('',None)}) or [INCONNU]


def accepte(x,c,op,val):
    if not c:return True
    vs=valeurs(x,c)
    if op=='inconnu':return vs==[INCONNU]
    if op in ('depuis','avant'):
        from datetime import date
        try:limite=date.fromisoformat(val)
        except ValueError:raise ValidationError('Le filtre de date exige AAAA-MM-JJ.')
        dates=[]
        for v in vs:
            if v==INCONNU:continue
            try:dates.append(date.fromisoformat(str(v)))
            except ValueError:raise ValidationError('Cette condition exige une dimension de date.')
        return any(v>=limite if op=='depuis' else v<limite for v in dates)
    if op in ('gte','lt'):
        try:n=Decimal(val)
        except InvalidOperation:raise ValidationError('Le filtre numérique exige un nombre.')
        if not n.is_finite():raise ValidationError('Le filtre numérique doit être fini.')
        return any(isinstance(v,(int,Decimal)) and (v>=n if op=='gte' else v<n) for v in vs)
    if op=='un_de':return any(str(v).casefold() in {s.strip().casefold() for s in val.split(';') if s.strip()} for v in vs)
    if op=='different':return vs!=[INCONNU] and all(str(v).casefold()!=val.casefold() for v in vs)
    if op=='contient':return any(val.casefold() in str(v).casefold() for v in vs)
    return any(str(v).casefold()==val.casefold() for v in vs)


def calculer(acteur,d):
    if d['mesure']=='menages':suivi.exiger(acteur,'view_menage')
    communs={'date_saisie','date_version','total','mois','jour','age','precision_naissance','unite'}
    propres={'personnes':set(),'menages':set(),'prises':{'type','etat','origine','orientation','motif'},'demandes':{'etat','motif','origine'},'sejours':{'etat','duree','entree_connue','quantite'},'repas':{'type','etat','origine','quantite'},'aides':{'type','etat','quantite'},'appels':{'complement115','appelant','auteur','auteur_version','heure','type','etat','motif','secondaire','reponse','origine','orientation','adultes_declares','enfants_declares','grossesses_declarees'},'ressources':{'type','etat','quantite'},'dettes':{'type','etat','quantite'},'couts':{'phase','type','etat','prescripteur','signataire','quantite'},'imputations':{'phase','type','prescripteur','signataire','financeur','budget','quantite'}}
    choisies=[d['axe'],d['croisement'],*[d['filtre'+str(i)] for i in range(1,(d.get('filtres') or 2)+1)]]
    if any(c and '.' not in c and c not in communs|propres[d['population']] for c in choisies):raise ValidationError('Un axe ou filtre ne correspond pas à cette population. Choisissez la population concernée, ou une dimension de situation personnelle.')
    n=d.get('filtres') or 2;cles=[d['axe'],d['croisement'],*[d['filtre'+str(i)] for i in range(1,n+1)]];lignes=population(acteur,d);enrichir(acteur,lignes,cles,d['reference'])
    selection=[]
    for x in lignes:
        criteres=[(d['filtre'+str(i)],d['operation'+str(i)],d['valeur'+str(i)]) for i in range(1,n+1)]
        if not all(accepte(x,c,op,v) for c,op,v in criteres if not personnelle(c)):continue
        personnels=[(c,op,v) for c,op,v in criteres if personnelle(c)]
        if personnels:
            membres={p for p,carte in x['_par_personne'].items() if all(accepte({'valeurs':carte},c,op,v) for c,op,v in personnels)}
            if not membres:
                if x['personnes'] or not all(accepte(x,c,op,v) for c,op,v in personnels):continue
            x['personnes']=membres
        selection.append(x)
    lignes=selection
    groupes=classes(d['classes']);groupes_croises=classes(d.get('classes_croisement',''));ventilation=defaultdict(dict)
    def categoriser(vs,groupes):
        if not groupes:return vs
        resultat=[]
        for v in vs:
            if v==INCONNU:resultat.append(INCONNU);continue
            if not isinstance(v,(int,Decimal)):raise ValidationError('Les classes min/max exigent une dimension numérique.')
            resultat.append(next((nom for nom,a,b in groupes if (a is None or v>=a) and (b is None or v<b)),'Hors classes'))
        return list(set(resultat))
    for x in lignes:
        cartes=[(p,{'valeurs':x['_par_personne'][p]}) for p in x['personnes']] if (personnelle(d['axe']) or personnelle(d['croisement'])) and x['personnes'] else [(None,x)]
        cellules=defaultdict(set)
        for p,carte in cartes:
            vs=categoriser(valeurs(carte,d['axe']),groupes)
            croises=categoriser(valeurs(carte,d['croisement']),groupes_croises) if d['croisement'] else ['Ensemble']
            for a,b in product(vs,croises):
                cle=(str(a),str(b),x['unite'] if d['mesure'] in ('quantite','minimum','maximum','moyenne') else '')
                cellules[cle].update([p] if p is not None else x['personnes'])
        for cle,personnes_cellule in cellules.items():ventilation[cle][x['id']]={**x,'personnes':personnes_cellule}
    def mesure(xs):
        xs=list(xs)
        if d['mesure'] in ('adultes_declares','enfants_declares','grossesses_declarees'):
            connus=[v for x in xs for v in x['valeurs'].get(d['mesure'],[])];return sum(connus) if connus else None
        if d['mesure']=='objets':return len(xs)
        if d['mesure'] in ('personnes','menages'):return len({p for x in xs for p in x[d['mesure']]})
        nombres=[x['quantite'] for x in xs if x['quantite'] is not None]
        if not nombres:return None
        if d['mesure']=='minimum':return min(nombres)
        if d['mesure']=='maximum':return max(nombres)
        if d['mesure']=='moyenne':return (sum(nombres)/len(nombres)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        return sum(nombres,Decimal('0'))
    if d['mesure'] in ('adultes_declares','enfants_declares','grossesses_declarees') and d['population']!='appels':raise ValidationError('Les effectifs déclarés par appel ne concernent que la population des appels.')
    if d['mesure'] in ('quantite','minimum','maximum','moyenne') and d['population'] not in ('sejours','repas','aides','ressources','dettes','couts','imputations'):raise ValidationError('Cette population n’a pas de quantité additive ; choisissez objets ou personnes/ménages distincts.')
    resultats=[{'axe':a,'croisement':b,'unite':u if d['mesure'] in ('quantite','minimum','maximum','moyenne') else d['mesure'],'valeur':mesure(xs.values())} for (a,b,u),xs in sorted(ventilation.items())]
    if len(resultats)>2000:raise ValidationError('Plus de 2 000 cellules : choisissez des axes ou filtres plus précis. Aucune cellule supprimée silencieusement.')
    totaux={u:mesure(x for x in lignes if x['unite']==u) for u in {x['unite'] for x in lignes}} if d['mesure'] in ('quantite','minimum','maximum','moyenne') else {d['mesure']:mesure(lignes)}
    return resultats,totaux,lignes
