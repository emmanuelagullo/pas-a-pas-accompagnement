from acteurs.contexte import service_metier
"""Modèles personnels : propriété, paramètres fermés et remplacement conditionnel."""
import hashlib
import json
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import OperationalError
from . import models as m, suivi

REVISION='_revision_modele'


class ConflitModele(ValidationError):
    pass


@service_metier
def exiger(acteur,modele):
    if modele.auteur_id!=acteur.pk:raise PermissionDenied
    if modele.parametres.get('analyse') or modele.parametres.get('assemblage'):
        suivi.exiger(acteur,'view_modelerapport','add_modelerapport')
    elif modele.parametres.get('_rapport_source'):
        from .catalogue_rapports import accessible
        suivi.exiger(acteur,'view_modelerapport','add_modelerapport')
        if not accessible(acteur,modele.parametres['_rapport_source']):raise PermissionDenied
    elif modele.parametres.get('exploration'):
        suivi.exiger(acteur,'view_modelerapport','add_modelerapport')
    else:
        suivi.exiger(acteur,'view_accompagnement','view_sejour','view_repasdistribue')


def etat(modele):
    return hashlib.sha256(json.dumps([modele.nom,modele.parametres,modele.description,modele.nature,modele.modele_source_id,modele.source_catalogue,modele.empreinte_source],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


@service_metier
def jeton(acteur,modele):
    exiger(acteur,modele)
    return signing.dumps(dict(acteur=str(acteur.pk),modele=str(modele.pk),etat=etat(modele)),salt='modele-personnel-v1',compress=True)


@service_metier
def verifier(acteur,modele,attendu):
    exiger(acteur,modele)
    try:p=signing.loads(attendu,salt='modele-personnel-v1',max_age=86400)
    except (signing.BadSignature,TypeError,ValueError):raise ConflitModele('Le formulaire du modèle n’est plus vérifiable ; rechargez avant de remplacer.')
    if p!=dict(acteur=str(acteur.pk),modele=str(modele.pk),etat=etat(modele)):
        raise ConflitModele('Le modèle a été modifié depuis ce formulaire. Vos paramètres saisis sont conservés ; rechargez le modèle avant de le remplacer.')


def nom_valide(nom):
    if not isinstance(nom,str) or not nom.strip() or len(nom)>100:raise ValidationError({'nom':'Indiquez un nom de 100 caractères au plus.'})
    return nom.strip()


@service_metier
def valider(acteur,params):
    if params.get('assemblage'):
        suivi.exiger(acteur,'view_modelerapport','add_modelerapport')
        from . import assemblages
        return assemblages.parametres(assemblages.valider(acteur,assemblages.lire(params)))
    if params.get('analyse'):
        suivi.exiger(acteur,'view_modelerapport','add_modelerapport')
        from . import analyses
        d=analyses.valider(acteur,analyses.lire(params))
        analyses.calculer(acteur,d)
        return analyses.parametres(d)
    if params.get('_rapport_source'):
        suivi.exiger(acteur,'view_modelerapport','add_modelerapport')
        from .vues_rapports import valider_source
        return valider_source(acteur,params)
    if params.get('exploration'):
        suivi.exiger(acteur,'view_modelerapport','add_modelerapport')
        from .modeles_echange import valider
        return valider(acteur,params)
    suivi.exiger(acteur,'view_accompagnement','view_sejour','view_repasdistribue')
    from .vues_statistiques import parametres_modele
    try:return parametres_modele(params)
    except (ValueError,TypeError):raise ValidationError('Paramètres du modèle de rapport invalides.')


@service_metier
def changer(acteur,modele,attendu,nom,params=None,*,description=None,export_prioritaire=None):
    verifier(acteur,modele,attendu)
    nouveau_nom=nom_valide(nom)
    if params is not None and bool(params.get('assemblage'))!=bool(modele.parametres.get('assemblage')):
        raise ValidationError('Conservez le type de modèle ; créez une nouvelle entrée pour un assemblage.')
    if params is not None and bool(params.get('analyse'))!=bool(modele.parametres.get('analyse')):
        raise ValidationError('Conservez le type de composition ; créez une variante séparée.')
    # Une simple modification du nom ne réinterprète pas un ancien modèle.
    if params is not None and bool(params.get('exploration'))!=bool(modele.parametres.get('exploration')):
        raise ValidationError('Conservez le type du modèle ; enregistrez une variante séparée pour une autre définition.')
    if params is not None and params.get('_rapport_source')!=modele.parametres.get('_rapport_source'):
        raise ValidationError('Conservez la définition source du rapport à remplacer.')
    nouveaux=modele.parametres.copy() if params is None else valider(acteur,params)
    if export_prioritaire is not None:
        from .presentation_exports import valider as valider_export
        nouveaux['export_prioritaire']=valider_export(export_prioritaire)
    revision=modele.parametres.get(REVISION,0)
    nouveaux[REVISION]=(revision if isinstance(revision,int) else 0)+1
    try:
        nombre=m.ModeleRapport.objects.filter(pk=modele.pk,auteur=acteur,nom=modele.nom,parametres=modele.parametres,description=modele.description,nature=modele.nature,modele_source_id=modele.modele_source_id,source_catalogue=modele.source_catalogue,empreinte_source=modele.empreinte_source).update(nom=nouveau_nom,parametres=nouveaux,description=modele.description if description is None else description)
    except OperationalError:raise ConflitModele('La modification n’a pas été confirmée. Rechargez le modèle avant de réessayer.')
    if nombre!=1:raise ConflitModele('Le modèle a changé pendant la confirmation ; aucun remplacement n’a été effectué.')
    modele.refresh_from_db()
    return modele


@service_metier
def dupliquer(acteur,modele,attendu,nom,*,export_prioritaire=None):
    verifier(acteur,modele,attendu)
    if m.ModeleRapport.objects.filter(auteur=acteur).count()>=30:raise ValidationError('Limite de 30 modèles personnels atteinte.')
    params=valider(acteur,modele.parametres);params.pop(REVISION,None)
    if export_prioritaire is not None:
        from .presentation_exports import valider as valider_export
        params['export_prioritaire']=valider_export(export_prioritaire)
    return m.ModeleRapport.objects.create(auteur=acteur,nom=nom_valide(nom),parametres=params,nature=modele.nature,description=modele.description,modele_source=modele.modele_source,source_catalogue=modele.source_catalogue,empreinte_source=modele.empreinte_source)


@service_metier
def supprimer(acteur,modele,attendu):
    from django.db import transaction
    verifier(acteur,modele,attendu)
    with transaction.atomic():
        nouveaux=modele.parametres.copy();revision=nouveaux.get(REVISION,0);nouveaux[REVISION]=(revision if isinstance(revision,int) else 0)+1
        if m.ModeleRapport.objects.filter(pk=modele.pk,auteur=acteur,nom=modele.nom,parametres=modele.parametres,description=modele.description,nature=modele.nature,modele_source_id=modele.modele_source_id,source_catalogue=modele.source_catalogue,empreinte_source=modele.empreinte_source).update(parametres=nouveaux)!=1:
            raise ConflitModele('Le rapport a changé ; rechargez avant de supprimer.')
        m.ModeleRapport.objects.filter(pk=modele.pk,auteur=acteur).delete()


@service_metier
def conserver_composition(acteur,cible,donnees,action,params):
    """Même contrat de conservation pour une analyse et un assemblage personnel."""
    from django.db import transaction
    suivi.exiger(acteur,'view_modelerapport','add_modelerapport')
    params=valider(acteur,params);nature=donnees['nature']
    if action=='remplacer':
        if cible is None or nature!=cible.nature:raise ValidationError('Conservez une nouvelle entrée pour changer de nature.')
        return changer(acteur,cible,donnees.get('attendu'),donnees['nom'],params,description=donnees.get('description',''))
    if action!='creer':raise ValidationError('Choisissez explicitement créer ou remplacer.')
    if cible:exiger(acteur,cible)
    parent=cible.modele_source if cible and cible.nature=='personnalisation' else cible
    if nature=='personnalisation':
        if parent is None:raise ValidationError('Ouvrez un modèle, ou conservez le modèle et sa personnalisation ensemble.')
        if params.get('analyse'):
            from .analyses import lire
            from .traduction_analyses import structure
            identique=structure(lire(params))==structure(lire(parent.parametres))
        else:
            from .assemblages import lire
            avant=lire(parent.parametres);apres=lire(params)
            identique=avant['parties']==apres['parties']
        if not identique:raise ValidationError('La définition du calcul a changé. Conservez un nouveau modèle, seul ou avec sa personnalisation.')
    with transaction.atomic():
        nombre=m.ModeleRapport.objects.filter(auteur=acteur).count()
        if nombre+(2 if nature=='ensemble' else 1)>30:raise ValidationError('Limite de 30 définitions personnelles atteinte.')
        if nature=='ensemble':
            parent=m.ModeleRapport.objects.create(auteur=acteur,nom=nom_valide(donnees.get('nom_modele')),description=donnees.get('description',''),parametres=params,nature='modele')
            nature='personnalisation'
        return m.ModeleRapport.objects.create(auteur=acteur,nom=nom_valide(donnees['nom']),description=donnees.get('description','') if nature=='modele' else '',nature=nature,parametres=params,modele_source=parent if nature=='personnalisation' else None,empreinte_source=etat(parent) if nature=='personnalisation' else '')
