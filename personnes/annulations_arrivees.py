from acteurs.contexte import service_metier
"""Retirer un fait d'arrivée erroné sans supprimer son histoire ou ses dépendances."""
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F,Q
from django.utils import timezone
from . import models as m,hebergement as h,corrections


def racine(s):return s.origine_collective or s


def fragments(s):
    return list(m.Sejour.objects.filter(Q(pk=s.pk)|Q(origine_collective=s)).order_by('pk'))


def photographie(s):
    return [dict(id=str(x.pk),accord=str(x.accord_id),debut=str(x.debut),fin=str(x.fin),revision=x.revision,annule=str(x.annule_le),
        beneficiaires=sorted(str(p.pk) for p in x.beneficiaires.all()),
        lieux=list(x.affectations.order_by('pk').values('id','lieu_id','debut','fin')),
        absences=list(x.absences.order_by('pk').values('id','debut','fin'))) for x in fragments(s)]


def jeton(s):
    # signing uses JSON; normalize the civil dates before comparing snapshots.
    import json
    from django.core.serializers.json import DjangoJSONEncoder
    return signing.dumps(json.loads(json.dumps(photographie(racine(s)),cls=DjangoJSONEncoder)),salt='annulation-arrivee-v1')


@service_metier
def droits(acteur,ecriture=False):
    h.droit(acteur,'view_annulationarrivee');h.exiger(acteur,'view_affectation','view_absence')
    if ecriture:h.exiger(acteur,'annuler_sejour','add_annulationarrivee')


def documents_actifs(s):
    return m.DocumentFinancement.objects.filter(version__financement__hebergement=s.accord,annulation__isnull=True)


@service_metier
def annuler(acteur,sejour,attendu,motif,*,accord_correct=None,beneficiaires=(),reprendre_mouvements=False):
    droits(acteur,ecriture=True);motif=corrections.motif_valide(motif)
    if accord_correct is not None:
        h.droit(acteur,'add_sejour')
        if reprendre_mouvements:h.exiger(acteur,'add_affectation','add_absence','view_lieuhebergement')
    elif beneficiaires or reprendre_mouvements:raise ValidationError('La reprise de mouvements et les bénéficiaires exigent un accord de remplacement.')
    source=racine(sejour)
    parents={source.accord.accompagnement.menage_id}
    if accord_correct:parents.add(accord_correct.accompagnement.menage_id)
    with transaction.atomic():
        # Reserve every household in a stable order before reading mutable facts.
        for pk in sorted(parents,key=str):m.Menage.objects.filter(pk=pk).update(revision=F('revision')+1)
        s=m.Sejour.objects.select_related('accord__accompagnement').get(pk=source.pk)
        try:ancien=signing.loads(attendu,salt='annulation-arrivee-v1',max_age=86400);courant=signing.loads(jeton(s),salt='annulation-arrivee-v1')
        except (signing.BadSignature,TypeError,ValueError):raise ValidationError('Formulaire non vérifiable ou expiré ; rechargez cette arrivée.')
        if ancien!=courant:raise ValidationError('Un séjour ou mouvement a changé ; rechargez avant de confirmer.')
        xs=fragments(s)
        if any(x.annule_le for x in xs):raise ValidationError('Cette arrivée est déjà annulée ; son historique reste consultable.')
        if documents_actifs(s).exists():raise ValidationError('Un document financier émis actif dépend de cet accord. Faites-le vérifier et annuler avec les droits nécessaires avant de retirer cette arrivée. Aucun document n’est modifié ici.')
        if accord_correct is not None and len(xs)>1:raise ValidationError('Cette arrivée possède des continuations individuelles. Annulez l’ensemble après vérification, puis enregistrez les arrivées exactes ; leurs périodes ne sont pas fusionnées automatiquement.')
        avant=ancien;nouveaux=[]
        if accord_correct is not None:
            a=m.AccordHebergement.objects.select_related('accompagnement').get(pk=accord_correct.pk)
            if a.accompagnement.fin and (s.fin is None or s.fin>a.accompagnement.fin):raise ValidationError('Le séjour repris doit être entièrement compris dans la prise en charge de destination ; ses dates ne sont pas modifiées automatiquement.')
            ps=list(beneficiaires);ids={p.pk for p in ps}
            if not ids or not ids.issubset(set(a.beneficiaires.values_list('pk',flat=True))):raise ValidationError('Choisissez les bénéficiaires explicites du bon accord.')
            if m.Sejour.objects.non_annules().filter(accord=a,beneficiaires__in=ps).exclude(pk__in=[x.pk for x in xs]).exists():raise ValidationError('Une arrivée existe déjà sous cet accord pour une personne choisie.')
            # Standard services revalidate authorizations, dates and household scope.
            nouveaux=h.admettre_individuellement(acteur,a,ps,s.debut)
            for nouveau in nouveaux:
                nouveau.remplace_sejour=s;nouveau.save(update_fields=['remplace_sejour'])
                if reprendre_mouvements:
                    for p in s.affectations.select_related('lieu'):h.ajouter_periode(acteur,nouveau,p.debut,p.fin,p.lieu)
                    for p in s.absences.all():h.ajouter_periode(acteur,nouveau,p.debut,p.fin,absence=True)
                if s.fin:h.sortir(acteur,nouveau,s.fin)
        instant=timezone.now()
        m.Sejour.objects.filter(pk__in=[x.pk for x in xs],annule_le__isnull=True).update(annule_le=instant,annule_par=acteur,motif_annulation=motif,revision=F('revision')+1)
        m.AccordHebergement.objects.filter(pk=s.accord_id).update(revision=F('revision')+1)
        for x in xs:h.audit(acteur,x.accord,'Arrivée annulée pour erreur',x.debut,sejour=x)
        return m.AnnulationArrivee.objects.create(origine=s,motif=motif,avant=avant,apres=[{'sejour':str(x.pk),'accord':str(x.accord_id),'beneficiaires':sorted(str(p.pk) for p in x.beneficiaires.all()),'mouvements_repris':reprendre_mouvements} for x in nouveaux],auteur=acteur)
