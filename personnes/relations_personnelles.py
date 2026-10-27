from acteurs.contexte import service_metier
"""Liens déclarés indépendants des ménages ; verrouillage de la paire ordonnée."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q,F
from django.utils import timezone
from . import bd6,suivi
from .models import Personne,RelationPersonnelle,RevisionRelationPersonnelle

DROITS_LECTURE=('personnes.view_personne','personnes.view_relationpersonnelle','personnes.view_revisionrelationpersonnelle')
ROLES=[('parent','Parent déclaré de l’autre personne'),('enfant','Enfant déclaré de l’autre personne'),
    ('couple','Lien de couple'),('fratrie','Fratrie'),('proche','Proche'),
    ('contact','Désigne l’autre personne comme personne à contacter'),('contact_de','Est une personne à contacter pour l’autre')]


def scope(personne):
    return Q(personne_a=personne)|Q(personne_b=personne)


def faits(personne):
    return RelationPersonnelle.objects.filter(scope(personne)).select_related('personne_a','personne_b','auteur')


def a_date(personne,jour):
    return faits(personne).filter(debut__lte=jour,annule_le__isnull=True).filter(Q(fin__isnull=True)|Q(fin__gt=jour))


def reserver(personne,autre,attendu):
    if not isinstance(autre,Personne) or personne.pk==autre.pk:
        raise ValidationError({'autre':'Choisissez une autre personne connue ; aucune identité n’est créée par ce lien.'})
    # Toutes les écritures d'une paire prennent les personnes dans le même
    # ordre. Ne prendre ensuite aucun verrou de ménage, prise ou répertoire.
    for p in sorted((personne,autre),key=lambda p:p.pk):
        if p.pk==personne.pk:bd6.reserver(personne,attendu)
        else:
            if Personne.objects.filter(pk=p.pk).update(revision_sociale=F('revision_sociale')+1)!=1:
                raise ValidationError('Personne liée introuvable.')
            p.refresh_from_db()


def photo(x):
    return {'id':x.pk,'personne_a':{'id':str(x.personne_a_id),'libelle':str(x.personne_a)},
        'personne_b':{'id':str(x.personne_b_id),'libelle':str(x.personne_b)},'nature':x.nature,
        'libelle':x.get_nature_display(),'description':x.libelle_depuis(x.personne_a),'debut':x.debut.isoformat(),'fin':x.fin.isoformat() if x.fin else None,
        'precision':x.precision,'source':x.source,'annule_le':x.annule_le.isoformat() if x.annule_le else None,
        'motif_annulation':x.motif_annulation}


@service_metier
def enregistrer(acteur,personne,autre,debut,fin,role,precision,source,attendu,motif='',correction=None,remplace=None,cloture=False):
    suivi.exiger(acteur,'view_personne','view_relationpersonnelle','view_revisionrelationpersonnelle','add_relationpersonnelle')
    if correction is not None or remplace is not None:suivi.exiger(acteur,'change_relationpersonnelle')
    return _enregistrer(acteur,personne,autre,debut,fin,role,precision,source,attendu,motif,correction,remplace,cloture)


@service_metier
@transaction.atomic
def _enregistrer(acteur,personne,autre,debut,fin,role,precision,source,attendu,motif,correction,remplace,cloture):
    reserver(personne,autre,attendu)
    if debut>timezone.localdate() or fin and fin>timezone.localdate():raise ValidationError('Un lien déclaré effectif ne peut pas être futur.')
    if role not in dict(ROLES):raise ValidationError({'role':'Choisissez le sens du lien depuis cette personne.'})
    if len(source)>160:raise ValidationError({'source':'Indiquez une source (160 caractères maximum).'})
    if len(motif)>240:raise ValidationError({'motif':'Le motif est limité à 240 caractères.'})
    if correction is not None and remplace is not None or cloture and correction is None:
        raise ValidationError('Choisissez une seule opération sur le lien.')
    a,b=sorted((personne,autre),key=lambda p:p.pk)
    cote_a=personne.pk==a.pk
    nature={'parent':'parent_a' if cote_a else 'parent_b','enfant':'parent_b' if cote_a else 'parent_a',
        'contact':'contact_a' if cote_a else 'contact_b','contact_de':'contact_b' if cote_a else 'contact_a'}.get(role,role)
    voisins=RelationPersonnelle.objects.filter(personne_a=a,personne_b=b,annule_le__isnull=True)
    x=RelationPersonnelle(personne_a=a,personne_b=b,auteur=acteur)
    avant=[];action='ajout';ancien=None
    pk=correction if correction is not None else remplace
    if pk is not None:
        try:ancien=voisins.get(pk=pk)
        except RelationPersonnelle.DoesNotExist:raise ValidationError('Ce lien actif ne correspond pas à ces deux personnes.')
        avant=[photo(ancien)]
        if correction is not None:
            x=ancien;action='cloture' if cloture else 'correction'
            if cloture and not motif.strip():raise ValidationError({'motif':'Expliquez cette fin de lien.'})
            if cloture and (x.fin is not None or fin is None or debut!=x.debut or nature!=x.nature or precision!=x.precision or source!=x.source):
                raise ValidationError('Terminer le lien conserve son début, sa nature, sa précision et sa source.')
        else:
            action='changement'
            if ancien.fin is not None or debut<=ancien.debut:
                raise ValidationError({'debut':'Le changement termine un lien ouvert après son début ; pour une erreur, utilisez Corriger.'})
            ancien.fin=debut;ancien.full_clean();ancien.save(update_fields=['fin'])
    elif voisins.filter(nature=nature,debut__gt=debut).exists():
        action='insertion'
    x.debut,x.fin,x.nature,x.precision,x.source=debut,fin,nature,precision.strip(),source.strip()
    x.full_clean()
    concurrents=voisins.exclude(pk=x.pk)
    if remplace is not None:concurrents=concurrents.exclude(pk=remplace)
    # Deux filiations inverses sur la même paire ne sont pas deux co-liens.
    concurrents=concurrents.filter(nature__in=['parent_a','parent_b'] if nature.startswith('parent_') else [nature])
    concurrents=concurrents.filter(Q(fin__isnull=True)|Q(fin__gt=debut))
    if fin:concurrents=concurrents.filter(debut__lt=fin)
    if concurrents.exists():raise ValidationError('Ce lien recouvre déjà une déclaration de même nature entre ces personnes.')
    if correction is not None and [photo(x)]==avant:raise ValidationError('Aucune modification.')
    x.save()
    apres=([photo(ancien)] if remplace is not None else [])+[photo(x)]
    RevisionRelationPersonnelle.objects.create(relation=x,action=action,avant=avant,apres=apres,motif=motif.strip(),auteur=acteur)
    return x


@service_metier
def annuler(acteur,personne,relation,motif,attendu):
    suivi.exiger(acteur,'view_personne','view_relationpersonnelle','view_revisionrelationpersonnelle','annuler_relationpersonnelle')
    if personne.pk not in (relation.personne_a_id,relation.personne_b_id):raise ValidationError('Lien étranger à cette personne.')
    return _annuler(acteur,personne,relation,motif,attendu)


@service_metier
@transaction.atomic
def _annuler(acteur,personne,relation,motif,attendu):
    reserver(personne,relation.autre(personne),attendu)
    x=faits(personne).get(pk=relation.pk)
    if x.annule_le or not motif.strip() or len(motif)>240:raise ValidationError('Lien déjà annulé ou motif manquant/invalide.')
    avant=[photo(x)];x.annule_le=timezone.now();x.annule_par=acteur;x.motif_annulation=motif.strip()
    x.full_clean();x.save(update_fields=['annule_le','annule_par','motif_annulation'])
    RevisionRelationPersonnelle.objects.create(relation=x,action='annulation',avant=avant,apres=[photo(x)],motif=motif.strip(),auteur=acteur)
