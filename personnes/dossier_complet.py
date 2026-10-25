"""Données personnelles typées du dossier : aucun accord ni droit implicite.

Le registre fixe décrit sept schémas Django concrets partageant le même cycle
de déclaration. Il ne permet ni attributs configurables ni nouveaux types en base.
"""
from collections import namedtuple
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from . import models as m,bd6,suivi,series_personnelles

Rubrique=namedtuple('Rubrique','modele journal titre champs libelle groupe')
RUBRIQUES={
 'ressources':Rubrique(m.RessourcePersonnelle,m.RevisionRessourcePersonnelle,'Ressources',('etat','libelle','organisme','montant','devise','periodicite'),'libelle','economique'),
 'dettes':Rubrique(m.DettePersonnelle,m.RevisionDettePersonnelle,'Dettes',('etat','nature','creancier','organisme','reference','montant','devise','mensualite'),'creancier','economique'),
 'pieces':Rubrique(m.PieceAdministrative,m.RevisionPieceAdministrative,'Pièces présentées',('etat','type_document','reference','date_presentation','echeance_prevue'),'type_document','droits'),
 'couvertures':Rubrique(m.CouvertureSociale,m.RevisionCouvertureSociale,'Couvertures sociales',('etat','libelle','regime','organisme','identifiant','interlocuteur','echeance_prevue'),'libelle','droits'),
 'protections':Rubrique(m.ProtectionJuridique,m.RevisionProtectionJuridique,'Protections juridiques déclarées',('etat','mesure','domaine','precision_portee','reference_decision','date_decision','echeance_prevue','representant_personne','representant_intervenant','organisme','interlocuteur'),'mesure','droits')}
RUBRIQUES['besoins']=Rubrique(m.BesoinAccueil,m.RevisionBesoinAccueil,'Besoins pratiques d’accueil déclarés',('etat','categorie','libelle','adaptation'),'libelle','droits')
RUBRIQUES['antecedents']=Rubrique(m.AntecedentInstitutionnel,m.RevisionAntecedentInstitutionnel,'Antécédents institutionnels déclarés',('etat','libelle','organisme','periode_declaree','date_entree','date_sortie','precision_dates'),'libelle','histoire')
ADMIN_CHAMPS=('numero_ss','numero_caf','qualification','droit_sejour','echeance_sejour','sans_emploi_duree_declaree','sans_domicile_duree_declaree','sans_emploi_depuis','precision_sans_emploi','sans_domicile_depuis','precision_sans_domicile')
ADMIN_LECTURE=('personnes.view_personne','personnes.view_situationadministrative','personnes.view_revisionsituationadministrative')


def droits_lecture(code):
    r=RUBRIQUES[code]
    d=['personnes.view_personne','personnes.view_'+r.modele._meta.model_name,'personnes.view_'+r.journal._meta.model_name]
    if 'organisme' in r.champs:d+=['personnes.view_partenaire']
    if 'interlocuteur' in r.champs:d+=['personnes.view_intervenant','personnes.view_ficheintervenant']
    return tuple(d)


def exiger_lecture(acteur,code):
    from django.core.exceptions import PermissionDenied
    if not acteur.has_perms(droits_lecture(code)):raise PermissionDenied


def faits(code,personnes):
    r=RUBRIQUES[code]
    fk=[f.name for f in r.modele._meta.fields if f.is_relation]
    return r.modele.objects.filter(personne__in=personnes).select_related(*fk)


def applicables(q,jour):
    return q.filter(annule_le__isnull=True,debut__lte=jour).filter(Q(fin__isnull=True)|Q(fin__gt=jour))


def a_date(code,personnes,jour):return applicables(faits(code,personnes),jour)


def administration_a_date(personnes,jour):
    return m.SituationAdministrative.objects.filter(personne__in=personnes,debut__lte=jour).filter(Q(fin__isnull=True)|Q(fin__gt=jour))


def administration(acteur,personne,debut,source,attendu,motif='',correction=None,**valeurs):
    suivi.exiger(acteur,'view_personne','view_situationadministrative','view_revisionsituationadministrative','add_situationadministrative')
    return series_personnelles.enregistrer(acteur,personne,debut,source,attendu,motif,correction,valeurs,
        modele=m.SituationAdministrative,journal=m.RevisionSituationAdministrative,champs=ADMIN_CHAMPS,lien='situation')


def photo(code,x):
    return {'id':x.pk,'debut':x.debut.isoformat(),'fin':x.fin.isoformat() if x.fin else None,
        **{c:series_personnelles.valeur_journal(getattr(x,c)) for c in RUBRIQUES[code].champs},
        'source':x.source,'annule_le':x.annule_le.isoformat() if x.annule_le else None,'motif_annulation':x.motif_annulation}


def _memes_postes(code,voisins,x):
    if code=='ressources':clés=('libelle','organisme','devise','periodicite')
    elif code=='dettes':clés=('nature','devise') if x.nature=='total' else ('nature','creancier','organisme','reference','devise')
    elif code=='pieces':clés=('type_document','reference')
    elif code=='antecedents':clés=('libelle','organisme','periode_declaree','date_entree','date_sortie')
    elif code=='besoins':clés=('categorie','libelle')
    elif code=='couvertures':clés=('libelle','regime','organisme','identifiant')
    else:clés=('mesure','domaine','reference_decision','representant_personne','representant_intervenant','organisme')
    for c in clés:
        v=getattr(x,c);f=x._meta.get_field(c)
        voisins=voisins.filter(**{c+('__iexact' if f.get_internal_type()=='CharField' else ''):v})
    return voisins


def enregistrer(acteur,code,personne,debut,fin,source,attendu,motif='',correction=None,remplace=None,cloture=False,remplacer_ensemble=False,**valeurs):
    r=RUBRIQUES[code];exiger_lecture(acteur,code)
    suivi.exiger(acteur,'add_'+r.modele._meta.model_name)
    if correction is not None or remplace is not None or remplacer_ensemble:suivi.exiger(acteur,'change_'+r.modele._meta.model_name)
    return _enregistrer(acteur,code,personne,debut,fin,source,attendu,motif,correction,remplace,cloture,remplacer_ensemble,valeurs)


@transaction.atomic
def _enregistrer(acteur,code,personne,debut,fin,source,attendu,motif,correction,remplace,cloture,ensemble,valeurs):
    r=RUBRIQUES[code];bd6.reserver(personne,attendu)
    if set(valeurs)!=set(r.champs):raise ValidationError('Précisez toutes les rubriques de cette déclaration, y compris les valeurs inconnues.')
    if debut>timezone.localdate() or fin and fin>timezone.localdate():raise ValidationError('Une déclaration effective ne peut pas être future. Utilisez les échéances prévues pour une prévision.')
    if not source.strip() or len(source)>160:raise ValidationError({'source':'Indiquez une source (160 caractères maximum).'})
    if len(motif)>240:raise ValidationError({'motif':'Le motif est limité à 240 caractères.'})
    if sum((correction is not None,remplace is not None,bool(ensemble)))>1 or cloture and correction is None:raise ValidationError('Choisissez une seule opération.')
    q=faits(code,[personne]);actifs=q.filter(annule_le__isnull=True)
    x=r.modele(personne=personne,auteur=acteur);avant=[];modifies=[];action='ajout'
    pk=correction if correction is not None else remplace
    if pk is not None:
        try:ancien=actifs.get(pk=pk)
        except r.modele.DoesNotExist:raise ValidationError('Cette déclaration active ne correspond pas à cette personne.')
        avant=[photo(code,ancien)]
        original=(ancien.debut,ancien.fin,ancien.source,{c:getattr(ancien,c) for c in r.champs})
        if correction is not None:
            x=ancien;action='cloture' if cloture else 'correction'
            if not motif.strip():raise ValidationError({'motif':'Expliquez la fin effective ou la correction.'})
            if cloture and (ancien.fin is not None or fin is None or debut!=ancien.debut or source!=ancien.source or any(getattr(ancien,c)!=valeurs[c] for c in r.champs)):
                raise ValidationError('Une fin effective conserve les autres renseignements.')
        else:
            if ancien.fin is not None or debut<=ancien.debut:raise ValidationError({'debut':'Le changement termine une déclaration ouverte après son début ; corriger traite une erreur.'})
            ancien.fin=debut;ancien.full_clean();ancien.save(update_fields=['fin']);modifies=[ancien];action='changement'
    elif ensemble:
        if valeurs['etat']=='detail':raise ValidationError('Le remplacement d’ensemble concerne seulement une absence ou une information non connue explicitement déclarée.')
        modifies=list(applicables(q,debut))
        if any(a.debut>=debut for a in modifies):raise ValidationError('Une déclaration existe déjà à cette date ; corrigez-la ou choisissez la date du changement.')
        avant=[photo(code,a) for a in modifies]
        for a in modifies:a.fin=debut;a.full_clean();a.save(update_fields=['fin'])
        action='changement'
    for c,v in valeurs.items():setattr(x,c,v)
    x.debut,x.fin,x.source=debut,fin,source.strip();x.full_clean()
    voisins=actifs.exclude(pk=x.pk).exclude(pk__in=[a.pk for a in modifies])
    recouvrants=voisins.filter(Q(fin__isnull=True)|Q(fin__gt=debut))
    if fin:recouvrants=recouvrants.filter(debut__lt=fin)
    if x.etat!='detail':conflit=recouvrants.exists()
    else:conflit=recouvrants.exclude(etat='detail').exists() or _memes_postes(code,recouvrants,x).exists()
    if conflit:raise ValidationError('Cette période recouvre une déclaration incompatible ou le même poste. Utilisez un changement explicite, une correction ou terminez la période concernée.')
    if correction is None and actifs.filter(debut__gt=debut).exists():
        action='insertion'
        suivi.exiger(acteur,'change_'+r.modele._meta.model_name)
        if not motif.strip():raise ValidationError({'motif':'Expliquez le fait antérieur oublié.'})
    if correction is not None and (x.debut,x.fin,x.source,{c:getattr(x,c) for c in r.champs})==original:raise ValidationError('Aucune modification.')
    x.save();r.journal.objects.create(fait=x,action=action,avant=avant,apres=[photo(code,a) for a in modifies]+[photo(code,x)],motif=motif.strip(),auteur=acteur)
    return x


def annuler(acteur,code,personne,fait,motif,attendu):
    exiger_lecture(acteur,code);suivi.exiger(acteur,'annuler_'+RUBRIQUES[code].modele._meta.model_name)
    return _annuler(acteur,code,personne,fait,motif,attendu)


@transaction.atomic
def _annuler(acteur,code,personne,fait,motif,attendu):
    r=RUBRIQUES[code];bd6.reserver(personne,attendu)
    try:x=faits(code,[personne]).get(pk=fait.pk)
    except r.modele.DoesNotExist:raise ValidationError('Déclaration étrangère à cette personne.')
    if x.annule_le or not motif.strip() or len(motif)>240:raise ValidationError('Déclaration déjà annulée ou motif manquant/invalide.')
    avant=[photo(code,x)];x.annule_le=timezone.now();x.annule_par=acteur;x.motif_annulation=motif.strip()
    x.full_clean();x.save(update_fields=['annule_le','annule_par','motif_annulation'])
    r.journal.objects.create(fait=x,action='annulation',avant=avant,apres=[photo(code,x)],motif=motif.strip(),auteur=acteur)


def totaux(code,lignes):
    """Totaux comparables seulement ; un total déclaré n'est jamais ajouté aux détails."""
    comptes={}
    for x in lignes:
        if x.etat!='detail':continue
        cle=(x.devise,'mensuelles connues' if code=='ressources' else 'total déclaré' if x.nature=='total' else 'détails connus')
        if code=='ressources' and x.periodicite!='mensuelle':continue
        if x.montant is not None:comptes[cle]=comptes.get(cle,Decimal('0'))+x.montant
    return sorted((devise,nature,montant) for (devise,nature),montant in comptes.items())


def syntheses(acteur,personnes,jour):
    """Lectures groupées par rubrique ; aucune donnée d'une autre rubrique sans droit."""
    personnes=list(personnes);resultat={p.pk:[] for p in personnes}
    if acteur.has_perms(ADMIN_LECTURE):
        admins={x.personne_id:x for x in administration_a_date(personnes,jour)}
        for p in personnes:
            x=admins.get(p.pk)
            resultat[p.pk].append({'code':'administration','titre':'Situation administrative','groupe':'droits',
                'texte':(' · '.join(v for v in (x.qualification,x.droit_sejour) if v) or 'Déclaration enregistrée') if x else 'Non renseignée'})
    for code,r in RUBRIQUES.items():
        if not acteur.has_perms(droits_lecture(code)):continue
        par_personne={p.pk:[] for p in personnes}
        for x in a_date(code,personnes,jour):par_personne[x.personne_id].append(x)
        for p in personnes:
            xs=par_personne[p.pk]
            if not xs:texte='Non renseigné'
            elif xs[0].etat!='detail':texte=xs[0].get_etat_display()
            else:
                texte=str(len(xs))+' déclaration(s)'
                if code in ('ressources','dettes'):
                    ts=totaux(code,xs)
                    if ts:texte+=' · '+' ; '.join(nature+' : '+str(total)+' '+devise for devise,nature,total in ts)+' (montants connus seulement)'
                elif code=='protections':texte=' ; '.join(x.mesure for x in xs)
                elif code=='couvertures':texte=' ; '.join(x.libelle for x in xs)
            resultat[p.pk].append({'code':code,'titre':r.titre,'groupe':r.groupe,'texte':texte,'valeur_sociale':({'aucun':'sans_ressources','inconnu':'inconnu','detail':'ressources_declarees'}[xs[0].etat] if code=='ressources' and xs else None),
                'sources':' ; '.join(dict.fromkeys(x.source for x in xs))})
    for v in resultat.values():v.sort(key=lambda d:{"economique":0,"droits":1,"histoire":2}[d["groupe"]])
    return resultat
