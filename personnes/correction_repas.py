from django.core import signing
from django.core.exceptions import ValidationError
from . import repas as service, models as m
from .verrous_metier import serialiser


def etat(r):return [str(r.pk),r.quantite,r.categorie_declaree,str(r.annule_le)]
def jeton(r):return signing.dumps(etat(r),salt='correction-repas-c')


@serialiser('repas')
def corriger(acteur,repas,quantite,categorie_declaree,motif,attendu):
    service.droit(acteur,'change_repasdistribue');service.exiger(acteur,'view_repasdistribue','view_revisionrepas')
    r=m.RepasDistribue.objects.get(pk=repas.pk)
    try:ancien=signing.loads(attendu,salt='correction-repas-c',max_age=86400)
    except (signing.BadSignature,TypeError):raise ValidationError('Formulaire périmé ; rechargez la distribution.')
    if ancien!=etat(r) or r.annule_le:raise ValidationError('Cette distribution a changé ou est annulée.')
    if not motif.strip() or len(motif)>240:raise ValidationError({'motif':'Expliquez la correction (240 caractères au plus).'})
    avant=[{'date':str(r.date),'beneficiaire':{'id':str(r.beneficiaire_id),'libelle':str(r.beneficiaire)},'quantite':r.quantite,'categorie_declaree':r.categorie_declaree}]
    r.quantite=quantite;r.categorie_declaree=categorie_declaree;r.full_clean()
    apres=[{**avant[0],'quantite':r.quantite,'categorie_declaree':r.categorie_declaree}]
    if avant==apres:raise ValidationError('Aucune modification.')
    r.save(update_fields=['quantite','categorie_declaree'])
    m.RevisionRepas.objects.create(repas=r,action='correction',avant=avant,apres=apres,motif=motif.strip(),auteur=acteur)
    return r.accord


@serialiser('accord')
def corriger_service(acteur,accord,jours_semaine,prestataire,motif,attendu):
    from . import accords
    from django.db.models import F
    service.droit(acteur,'change_accordrepas');service.exiger(acteur,'view_revisionservicerepas','view_repasdistribue')
    a=m.AccordRepas.objects.select_related('accompagnement').get(pk=accord.pk);accords.exiger_actif(a);accords.verifier(a,attendu)
    if not motif.strip() or len(motif)>240:raise ValidationError('Expliquez la correction du service.')
    avant=[{'jours_semaine':a.jours_semaine,'prestataire':a.prestataire}]
    a.jours_semaine=jours_semaine;a.prestataire=prestataire.strip();a.full_clean()
    if a.jours_semaine and any(r.date.weekday() not in a.jours_semaine for r in a.realisations.filter(annule_le__isnull=True)):
        raise ValidationError('Des distributions actives ne seraient plus autorisées par ces jours ; corrigez les faits erronés avant l’autorisation.')
    apres=[{'jours_semaine':a.jours_semaine,'prestataire':a.prestataire}]
    if avant==apres:raise ValidationError('Aucune modification.')
    a.revision+=1;a.save(update_fields=['jours_semaine','prestataire','revision'])
    m.RevisionServiceRepas.objects.create(accord=a,action='correction',avant=avant,apres=apres,motif=motif.strip(),auteur=acteur)
    return a
