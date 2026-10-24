"""Corrections limitées, contrôles de dépendances et avant/après persistants."""
from . import textes_riches as tr
from django.core import signing
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from . import models as m
from .suivi import exiger
from .verrous_metier import serialiser, menage_de

PERIODES = {
    'accompagnement': (m.Accompagnement, 'accompagnement'),
    'appartenance': (m.Appartenance, 'appartenance'),
    'accordrepas': (m.AccordRepas, 'accord_repas'),
    'accordhebergement': (m.AccordHebergement, 'accord_hebergement'),
    'sejour': (m.Sejour, 'sejour'), 'affectation': (m.Affectation, 'affectation'),
    'absence': (m.Absence, 'absence'), 'situationsociale': (m.SituationSociale, 'situation'),
}
TEXTES = {'evenementsocial':m.EvenementSocial, 'bilansocial':m.BilanSocial}


def suivi_de(objet):
    if isinstance(objet,m.Accompagnement):return objet
    if isinstance(objet,m.Appartenance):return None
    if hasattr(objet,'accompagnement_id'):return objet.accompagnement
    if hasattr(objet,'accord_id'):return objet.accord.accompagnement
    return objet.sejour.accord.accompagnement


def droits(acteur, nature):
    exiger(acteur,'view_personne','view_menage','view_'+nature,'change_'+nature,
        'view_revisiontextesocial' if nature in TEXTES else 'view_correctionperiode')
    if nature!='appartenance':exiger(acteur,'view_accompagnement')


def etat(objet):
    if isinstance(objet,(m.EvenementSocial,m.BilanSocial)):
        return [str(objet.date_effet),objet.texte,getattr(objet,'source',''),getattr(objet, 'texte_document', None)]
    resultat = [str(objet.debut),str(objet.fin),getattr(objet,'source','')]
    if isinstance(objet, (m.AccordRepas, m.AccordHebergement)):
        resultat += [objet.revision, str(objet.annule_le)]
    return resultat


def jeton(objet):
    return signing.dumps([objet._meta.model_name,str(objet.pk),etat(objet)],salt='chrs7-correction')


def verifier_jeton(objet, attendu):
    try:precedent=signing.loads(attendu,salt='chrs7-correction',max_age=86400)
    except signing.BadSignature as exc:raise ValidationError('Le formulaire a expiré. Rechargez la fiche.') from exc
    if precedent != [objet._meta.model_name,str(objet.pk),etat(objet)]:
        raise ValidationError('Cette donnée a changé depuis l’ouverture du formulaire. Rechargez la fiche.')


def motif_valide(motif):
    motif=motif.strip()
    if not motif or len(motif)>240:raise ValidationError('Indiquez un motif de 1 à 240 caractères.')
    return motif


def incluse(parent,debut,fin=None,point=False):
    if debut<parent.debut or (parent.fin and (debut>=parent.fin or (not point and (fin is None or fin>parent.fin)))):
        raise ValidationError('La correction dépasse la période de rattachement.')


def dates_dependantes(a):
    # Les accords peuvent conserver une période historique plus large après
    # clôture du suivi ; les réalisations doivent toujours rester dans le suivi.
    for accord in list(a.accords_repas.filter(annule_le__isnull=True))+list(a.accords_hebergement.filter(annule_le__isnull=True)):
        if accord.debut<a.debut:raise ValidationError('Un accord commence avant le nouvel accompagnement.')
    for r in m.RepasDistribue.objects.filter(accord__accompagnement=a,annule_le__isnull=True):
        incluse(a,r.date,point=True)
    for s in m.Sejour.objects.filter(accord__accompagnement=a):incluse(a,s.debut,s.fin)
    for x in m.AffectationIntervenant.objects.filter(accompagnement=a,annule_le__isnull=True):
        incluse(a, x.debut, point=True)
        if x.fin:
            incluse(a, x.debut, x.fin)
    for r in m.RemiseAide.objects.filter(accord__accompagnement=a,annule_le__isnull=True):incluse(a,r.date,point=True)
    if a.accords_aides.filter(annule_le__isnull=True,debut__lt=a.debut).exists():raise ValidationError('Un accord d’aide commence avant la prise en charge.')
    from .social import date_evenement
    for e in m.EvenementSocial.objects.filter(accompagnement=a):date_evenement(a, e.date_effet)
    for modele,champ in [(m.SituationSociale,'debut'),(m.BilanSocial,'date_effet')]:
        for valeur in modele.objects.filter(accompagnement=a).values_list(champ,flat=True):incluse(a,valeur,point=True)


def valider(objet):
    nature=objet._meta.model_name
    objet.full_clean()
    if objet.debut>timezone.localdate() and nature not in ('accordrepas','accordhebergement','accompagnement','appartenance'):
        raise ValidationError('Un début effectif ne peut pas être futur.')
    if objet.fin and objet.fin>timezone.localdate() and nature in ('sejour','affectation','absence'):
        raise ValidationError('Une fin effective ne peut pas être future.')
    if nature=='accompagnement':dates_dependantes(objet)
    elif nature=='accordrepas':
        a=objet.accompagnement
        if objet.debut<a.debut:raise ValidationError('L’accord commence avant l’accompagnement.')
        for r in objet.realisations.filter(annule_le__isnull=True):
            incluse(objet,r.date,point=True);incluse(a,r.date,point=True)
    elif nature=='accordhebergement':
        if objet.debut<objet.accompagnement.debut:raise ValidationError('L’accord commence avant l’accompagnement.')
        for s in objet.sejours.all():
            # Admission ouverte sous un accord borné permise, sans prolongation.
            incluse(objet,s.debut,point=True)
    elif nature=='sejour':
        if hasattr(objet,'individualisation') and objet.fin!=objet.individualisation.date or objet.origine_collective_id and objet.debut!=objet.origine_collective.fin:
            raise ValidationError('La date de continuité ne se corrige pas indépendamment de ses fragments ; les autres dates restent corrigibles.')
        incluse(objet.accord,objet.debut,point=True)
        incluse(objet.accord.accompagnement,objet.debut,objet.fin)
        for periode in list(objet.affectations.all())+list(objet.absences.all()):incluse(objet,periode.debut,periode.fin)
    elif nature in ('affectation','absence'):
        from .hebergement import bornes
        bornes(objet.sejour,objet.debut,objet.fin)
        voisins=type(objet).objects.filter(sejour=objet.sejour).exclude(pk=objet.pk).filter(Q(fin__isnull=True)|Q(fin__gt=objet.debut))
        if objet.fin:voisins=voisins.filter(debut__lt=objet.fin)
        if voisins.exists():raise ValidationError('La correction crée un chevauchement dans ce séjour.')
    elif nature=='situationsociale':
        from .social import date_valide
        date_valide(objet.accompagnement,objet.debut)


def enregistrer(acteur,objet,ancien,motif):
    nature=objet._meta.model_name
    m.CorrectionPeriode.objects.create(menage=menage_de(objet),suivi=suivi_de(objet),nature=nature,
        **{PERIODES[nature][1]:objet},ancien_debut=ancien[0],ancienne_fin=ancien[1],
        nouveau_debut=objet.debut,nouvelle_fin=objet.fin,ancienne_source=ancien[2],
        nouvelle_source=getattr(objet,'source',''),motif=motif,auteur=acteur)


@serialiser('objet')
def periode(acteur,objet,debut,fin,motif,attendu,source=None):
    nature=objet._meta.model_name
    droits(acteur,nature)
    objet=type(objet).objects.get(pk=objet.pk)
    verifier_jeton(objet,attendu)
    motif=motif_valide(motif)
    accord = isinstance(objet, (m.AccordRepas, m.AccordHebergement))
    if accord:
        from .accords import exiger_actif
        exiger_actif(objet)
    ancien=(objet.debut,objet.fin,getattr(objet,'source',''))
    if (objet.fin is None)!=(fin is None):
        raise ValidationError('Utilisez la clôture dédiée. La correction ne ferme ni ne rouvre une période.')
    objet.debut,objet.fin=debut,fin
    if source is not None and nature=='situationsociale':objet.source=source
    if ancien==(objet.debut,objet.fin,getattr(objet,'source','')):raise ValidationError('Aucune modification.')
    if nature=='situationsociale':
        serie=m.SituationSociale.objects.filter(accompagnement=objet.accompagnement,beneficiaire=objet.beneficiaire,dimension=objet.dimension)
        precedent=serie.filter(debut__lt=ancien[0]).order_by('-debut').first()
        suivant=serie.filter(debut__gt=ancien[0]).order_by('debut').first()
        if (precedent and debut<=precedent.debut) or (suivant and debut>=suivant.debut):
            raise ValidationError('La date doit rester entre les valeurs voisines ; aucun réordonnancement automatique.')
        objet.fin=suivant.debut if suivant else None
        if precedent:
            avant=(precedent.debut,precedent.fin,precedent.source)
            precedent.fin=debut;precedent.full_clean();precedent.save(update_fields=['fin'])
            enregistrer(acteur,precedent,avant,motif)
    valider(objet)
    if accord:
        objet.revision += 1
    objet.save(update_fields=['debut','fin']+(['source'] if nature=='situationsociale' else [])+(['revision'] if accord else []))
    enregistrer(acteur,objet,ancien,motif)
    return objet


@serialiser('objet')
def texte(acteur,objet,date_effet,texte,motif,attendu,source=''):
    nature=objet._meta.model_name
    droits(acteur,nature)
    objet=type(objet).objects.get(pk=objet.pk)
    verifier_jeton(objet,attendu);motif=motif_valide(motif)
    ancienne=etat(objet)
    from .social import date_valide, date_evenement
    (date_evenement if nature == 'evenementsocial' else date_valide)(objet.accompagnement,date_effet)
    objet.date_effet=date_effet
    if nature == 'bilansocial':
        valeur = tr.preparer(texte, max_length=2000, required=True)
        objet.texte, objet.texte_document = str(valeur), valeur.document
    else:
        objet.texte=texte
    if nature=='evenementsocial':objet.source=source
    objet.full_clean()
    if etat(objet)==ancienne:raise ValidationError('Aucune modification.')
    m.RevisionTexteSocial.objects.create(accompagnement=objet.accompagnement,
        **({'evenement':objet} if nature=='evenementsocial' else {'bilan':objet}),
        ancienne_date=ancienne[0],nouvelle_date=date_effet,ancien_texte=ancienne[1],nouveau_texte=objet.texte,
        ancien_texte_document=ancienne[3],nouveau_texte_document=getattr(objet, 'texte_document', None),
        ancienne_source=ancienne[2],nouvelle_source=getattr(objet,'source',''),motif=motif,auteur=acteur)
    objet.save(update_fields=['date_effet','texte']+(['source'] if nature=='evenementsocial' else ['texte_document']))
    return objet
