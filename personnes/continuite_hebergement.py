"""Continuer un ancien séjour collectif par personne à une date confirmée.

L'histoire commune antérieure reste sur l'original. Les continuations ne sont
pas de nouvelles admissions. Aucun ancien séjour n'est converti par migration.
"""
from django.core import signing
from django.core.exceptions import ValidationError
from django.utils import timezone
from . import models as m, hebergement as h, hebergement_collectif as collectif
from .verrous_metier import serialiser


def jeton(sejour):
    sejour.refresh_from_db()
    return signing.dumps([str(sejour.pk),collectif.etat(sejour),sorted(str(p.pk) for p in sejour.beneficiaires.all())],salt='continuite-sejour')


@serialiser('sejour')
def individualiser(acteur,sejour,date,motif,attendu):
    h.droit(acteur,'add_sejour')
    h.exiger(acteur,'change_sejour','view_affectation','add_affectation','change_affectation','view_absence','add_absence','change_absence','add_continuitesejour','view_continuitesejour')
    s=m.Sejour.objects.select_related('accord__accompagnement').get(pk=sejour.pk)
    if attendu!=jeton(s):
        # Signed payloads contain timestamps; compare their authenticated contents.
        try:ancien=signing.loads(attendu,salt='continuite-sejour',max_age=86400);courant=signing.loads(jeton(s),salt='continuite-sejour')
        except (signing.BadSignature,TypeError):raise ValidationError('Formulaire non vérifiable ; rechargez.')
        if ancien!=courant:raise ValidationError('Le séjour a changé ; rechargez avant de confirmer.')
    ps=list(s.beneficiaires.order_by('pk'))
    if len(ps)<2 or s.fin or s.origine_collective_id or hasattr(s,'individualisation'):raise ValidationError('Cette action concerne un ancien séjour collectif ouvert, non encore individualisé.')
    if date<=s.debut or date>timezone.localdate() or not motif.strip() or len(motif)>240:raise ValidationError('Choisissez une date après l’admission, non future, et expliquez cette continuité.')
    periodes=[*s.affectations.all(),*s.absences.all()]
    if any(x.debut>=date or x.fin and x.fin>date for x in periodes):raise ValidationError('La continuité doit suivre les périodes déjà datées. Choisissez une date après les faits enregistrés ; leurs corrections restent distinctes.')
    avant={'debut':str(s.debut),'fin':None,'beneficiaires':[str(p.pk) for p in ps],
        'periodes':[{'modele':x._meta.model_name,'id':x.pk,'debut':str(x.debut),'fin':str(x.fin),'lieu':getattr(x,'lieu_id',None)} for x in periodes]}
    ouvertes=[x for x in periodes if x.fin is None]
    # All old periods are first checked; any later failure rolls back the split.
    h.sortir(acteur,s,date)
    m.OperationHebergement.objects.filter(sejour=s,action="Sortie effective",date_effet=date).update(action="Individualisation")
    enfants=[]
    for p in ps:
        x=m.Sejour.objects.create(accord=s.accord,origine_collective=s,debut=date,cree_par=acteur)
        x.beneficiaires.set([p]);enfants.append(x)
        for old in ouvertes:
            h.ajouter_periode(acteur,x,date,None,lieu=old.lieu if isinstance(old,m.Affectation) else None,absence=isinstance(old,m.Absence))
    m.ContinuiteSejour.objects.create(origine=s,date=date,motif=motif.strip(),avant=avant,
        apres=[{'sejour':str(x.pk),'beneficiaires':[str(p.pk) for p in x.beneficiaires.all()],'affectations':list(x.affectations.values_list('pk',flat=True)),'absences':list(x.absences.values_list('pk',flat=True))} for x in enfants],auteur=acteur)
    return s.accord


def episodes():
    """Épisodes initiaux pour les compteurs historiques ; fragments pour les nuitées."""
    for s in m.Sejour.objects.filter(origine_collective__isnull=True).select_related('accord__accompagnement').prefetch_related('continuations__beneficiaires','beneficiaires'):
        enfants=list(s.continuations.all())
        fin=(None if any(x.fin is None for x in enfants) else max(x.fin for x in enfants)) if enfants else s.fin
        yield s,fin


def jeton_coupure(sejour):
    sejour.refresh_from_db()
    return signing.dumps([str(sejour.pk),collectif.etat(sejour),str(sejour.individualisation.date),
        {str(s.pk):collectif.etat(s) for s in sejour.continuations.order_by('pk')}],salt='correction-continuite')


@serialiser('sejour')
def corriger_coupure(acteur,sejour,date,motif,attendu):
    h.droit(acteur,'change_continuitesejour');h.exiger(acteur,'view_continuitesejour','view_revisioncontinuite','change_sejour','change_affectation','change_absence')
    s=m.Sejour.objects.get(pk=sejour.pk)
    try:avant_token=signing.loads(attendu,salt='correction-continuite',max_age=86400);courant=signing.loads(jeton_coupure(s),salt='correction-continuite')
    except (signing.BadSignature,TypeError):raise ValidationError('Formulaire de correction périmé ; rechargez la continuité.')
    if avant_token!=courant:raise ValidationError('Un des fragments a changé ; rechargez la continuité.')
    c=s.individualisation
    if date==c.date or date<=s.debut or date>timezone.localdate() or not motif.strip() or len(motif)>240:raise ValidationError('Choisissez une date corrigée après l’admission, non future, et expliquez l’erreur.')
    periodes_origines={(x['modele'],x['id']) for x in c.avant['periodes'] if x['fin']=='None'}
    for x in [*s.affectations.all(),*s.absences.all()]:
        if (x._meta.model_name,x.pk) in periodes_origines:
            x.fin=date
        if x.debut>=date or x.fin is None or x.fin>date:raise ValidationError('La date corrigée traverserait un fait de la période commune.')
        x.full_clean();x.save(update_fields=['fin'])
    enfants={str(x.pk):x for x in s.continuations.all()}
    for photo in c.apres:
        x=enfants[photo['sejour']]
        if x.fin and x.fin<=date:raise ValidationError('La date corrigée traverserait un départ individuel.')
        for modele,cle in ((m.Affectation,'affectations'),(m.Absence,'absences')):
            copies=set(photo.get(cle,[]))
            for p in modele.objects.filter(sejour=x):
                if p.pk in copies:p.debut=date
                if p.debut<date or p.fin and p.fin<=p.debut:raise ValidationError('La date corrigée traverserait un mouvement individuel.')
                p.full_clean();p.save(update_fields=['debut'])
        x.debut=date;x.full_clean();x.save(update_fields=['debut'])
    ancien=c.date;s.fin=date;s.full_clean();s.save(update_fields=['fin']);c.date=date;c.save(update_fields=['date'])
    m.RevisionContinuite.objects.create(continuite=c,action='correction',avant=[{'date':str(ancien)}],apres=[{'date':str(date)}],motif=motif.strip(),auteur=acteur)
    return s.accord
