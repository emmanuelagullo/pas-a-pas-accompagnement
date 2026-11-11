"""Application de la collecte : jamais de copie ménage/personne ni droit implicite."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from acteurs.contexte import courant
from acteurs.models import Service
from acteurs.collecte import RUBRIQUES, verifier
from . import models as m

MODELES={'ComplementIdentite':'complements','DeclarationFamiliale':'famille','CoordonneesPersonnelles':'coordonnees','SituationAdministrative':'administration','RessourcePersonnelle':'ressources','DettePersonnelle':'dettes','PieceAdministrative':'pieces','CouvertureSociale':'couvertures','ProtectionJuridique':'protections','BesoinAccueil':'besoins','AntecedentInstitutionnel':'antecedents','AncrageTerritorial':'territoires','EvolutionPersonnelleDeclaree':'evolutions','RelationPersonnelle':'relations'}

def service(objet=None):
    from . import collectifs
    ctx=courant()
    if ctx and ctx.memo.get('collecte_objet') and not isinstance(objet,(m.Accompagnement,m.Menage)):
        objet=ctx.memo['collecte_objet']
    # La prise et le ménage explicites constituent la portée métier de la page.
    if isinstance(objet,(m.Accompagnement,m.Menage)):
        try:return collectifs.service_objet(objet)
        except ValidationError:return None
    if ctx and ctx.service_id:return Service.objects.filter(pk=ctx.service_id).first()
    if objet:
        from acteurs.portees import existante
        origine=existante(objet)
        if origine:return origine.service
    return None

def regles(objet=None):
    s=service(objet)
    if not s or not s.collecte_rubriques:return None
    from acteurs.profils_collectifs import categories_defaut
    verifier(s.collecte_rubriques,s.profil_collectif.get('categories',categories_defaut()))
    return s.collecte_rubriques

def rubrique(code):
    return {'ressources-globales': 'ressources', 'motifs_logement': 'logement'}.get(code, code)

def concerne(personne,regle,jour,objet=None):
    if regle['portee'] not in ('personne','deux'):return False
    pop=regle['population']
    if pop=='tous':return True
    from . import collectifs
    if pop=='reference':
        if isinstance(objet,m.Personne) or objet is None:
            s=service(objet)
            q=m.CompositionCollective.objects.filter(service=s,reference=personne,debut__lte=jour,annule_le__isnull=True,pour_prestation=False)
            # Chaque ménage garde seulement sa dernière déclaration à cette date.
            for comp in q:
                cible=comp.accompagnement or comp.menage
                actuel=collectifs.composition(cible,jour)
                if actuel and actuel.reference_id==personne.pk:return True
            return False
        comp=collectifs.composition(objet,jour)
        return bool(comp and comp.reference_id==personne.pk)
    # Une année seule ou une catégorie déclarée n'invente pas une date de naissance.
    age=collectifs.age_exact(personne.date_naissance,jour) if personne.date_naissance and personne.precision_naissance=='exacte' else None
    if pop=='adultes':return age is not None and age>=18
    if age is None:return False
    s=service(objet);from acteurs.profils_collectifs import categories_defaut
    categories=s.profil_collectif.get('categories',categories_defaut()) if s else categories_defaut()
    return collectifs.categorie_age(age,categories)==pop.removeprefix('categorie:')

def exiger(personne,code,jour=None,objet=None):
    ctx=courant()
    objet=objet or (ctx.memo.get('collecte_objet') if ctx else None) or personne
    r=regles(objet);code=rubrique(code)
    if r and code in r and not concerne(personne,r[code],jour or timezone.localdate(),objet or personne):
        raise PermissionDenied('Cette information n’est pas demandée pour cette personne dans ce service.')

def exiger_modele(personne,modele,jour):
    code=MODELES.get(modele.__name__)
    if code:exiger(personne,code,jour)

def presentation(resultats,objet,jour):
    r=regles(objet)
    if not r:return False
    for p in resultats.values():
        for g in p['groupes']:
            code=rubrique(g['code']);demande=code not in r or concerne(p['personne'],r[code],jour,objet)
            g['hors_collecte']=not demande
            if not demande:
                g['ajouter']=''
                for fiche in g['fiches']:
                    for cle in ('changer','corriger','retirer'):fiche[cle]=''
        p['groupes']=[g for g in p['groupes'] if not g['hors_collecte'] or g['fiches']]
    return True

def verifier_appel(f,valeurs):
    """Avant l'entrée dans les transactions d'écriture, pour HTTP et appels Python."""
    module=f.__module__;nom=f.__name__
    personne=valeurs.get('personne');jour=valeurs.get('debut') or timezone.localdate()
    code=None
    if module=='personnes.series_personnelles' and nom=='enregistrer':
        modele=valeurs.get('modele');code=MODELES.get(modele.__name__) if modele else None
    elif module=='personnes.bd6' and nom=='renseigner':code=valeurs.get('dimension')
    elif module=='personnes.dossier_complet' and nom=='enregistrer':code=valeurs.get('code')
    elif module=='personnes.relations_personnelles' and nom=='enregistrer':code='relations'
    elif module=='personnes.social' and nom in ('renseigner','corriger'):
        x=valeurs.get('situation');personne=valeurs.get('beneficiaire') or (x.beneficiaire if x else None)
        code=valeurs.get('dimension') or (x.dimension if x else None)
        if personne:exiger(personne,code,jour,valeurs.get('accompagnement') or (x.accompagnement if x else None))
        return
    if personne and code:exiger(personne,code,jour)

def verifier_route(request,match):
    """Les formulaires GET et fragments suivent les mêmes règles que les écritures."""
    nom=match.view_name;kw=match.kwargs
    fixes={'dossiers:coordonnees_nouvelles':'coordonnees','dossiers:coordonnees_corriger':'coordonnees','dossiers:famille_nouvelle':'famille','dossiers:famille_corriger':'famille','dossiers:complements_identite_nouveaux':'complements','dossiers:complements_identite_corriger':'complements','dossiers:administration_nouvelle':'administration','dossiers:administration_corriger':'administration','dossiers:relation_nouvelle':'relations','dossiers:relation_corriger':'relations','dossiers:relation_changer':'relations'}
    code=fixes.get(nom)
    if nom in ('dossiers:social_nouveau','dossiers:social_corriger'):code=kw.get('dimension')
    if nom in ('dossiers:fait_a_nouveau','dossiers:fait_a_absence','dossiers:fait_a_changer','dossiers:fait_a_corriger'):code=kw.get('code')
    if not code:return
    personne=m.Personne.objects.filter(pk=kw.get('pk')).first()
    if personne:
        parent=request.GET.get('contexte_prise')
        if parent:
            from django import forms
            try:parent=forms.UUIDField().clean(parent)
            except ValidationError:raise PermissionDenied
            prise=m.Accompagnement.objects.filter(pk=parent,beneficiaires=personne).first()
            if not prise:raise PermissionDenied
            if courant():courant().memo['collecte_objet']=prise
        from django import forms
        try:jour=forms.DateField().clean(request.POST.get('debut') or request.GET.get('date') or timezone.localdate())
        except ValidationError:jour=timezone.localdate()
        exiger(personne,code,jour)
