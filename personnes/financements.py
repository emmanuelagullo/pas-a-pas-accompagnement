"""Calculs déclarés versionnés ; aucune dépense, facture ou réalisation implicite."""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import hashlib,json
from uuid import uuid4
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from . import models as m,bd6,suivi
from .verrous_metier import serialiser

CIBLES={'hebergement':m.AccordHebergement,'repas':m.AccordRepas,'aide':m.AccordAide}
LECTURE=('view_financementprestation','view_versionfinancement','view_lignecout','view_imputationfinancement','view_documentfinancement','view_annulationdocument','view_partenaire','view_fichepartenaire','view_intervenant','view_ficheintervenant','view_personne','view_menage','view_accompagnement','view_tarifprestation','view_versiontarif')
ENTETE=('emetteur','mentions','debut','fin','devise','prestataire','prescripteur','facturation','signataire','reference','source')
TARIF=('debut','fin','libelle','unite','categorie','montant','devise','prestataire','actif','source')
LIGNE=('phase','date','libelle','unite','categorie','quantite','prix','tarif','justification')
IMPUTATION=('phase','financeur','budget','montant','reference')


def droit(acteur,accord=None,*actions):
    suivi.exiger(acteur,*LECTURE,*actions)
    if accord:suivi.exiger(acteur,'view_'+accord._meta.model_name)


def requis(texte,nom,maximum):
    if not isinstance(texte,str) or not texte.strip() or len(texte)>maximum:raise ValidationError({nom:'Renseignez cette information et respectez sa longueur maximale.'})


def creation_tarif():return signing.dumps(str(uuid4()),salt='financement-tarif')


@transaction.atomic
def _definir_tarif(acteur,attendu,motif,action='definition',tarif=None,**valeurs):
    suivi.exiger(acteur,'view_tarifprestation','view_versiontarif','add_versiontarif','change_tarifprestation' if tarif else 'add_tarifprestation')
    requis(motif,'motif',240)
    if set(valeurs)!=set(TARIF):raise ValidationError('Tarif incomplet.')
    requis(valeurs['source'],'source',160);requis(valeurs['libelle'],'libelle',160);requis(valeurs['unite'],'unite',60)
    if tarif:
        if action not in ('changement','correction'):raise ValidationError('Distinguez nouveau prix et correction d’erreur.')
        bd6.reserver(tarif,attendu)
        existe=tarif.versions.filter(debut=valeurs['debut']).exists()
        if (action=='correction')!=existe:raise ValidationError({'debut':'Corrigez un prix à sa date existante ; un nouveau prix prend une nouvelle date.'})
        n=tarif.versions.first().version+1
    else:
        if action!='definition':raise ValidationError('Commencez par définir ce tarif.')
        try:pk=signing.loads(attendu,salt='financement-tarif',max_age=86400)
        except (signing.BadSignature,TypeError):raise ValidationError('Création non vérifiable ; rechargez le formulaire.')
        if m.TarifPrestation.objects.filter(pk=pk).exists():raise ValidationError('Création déjà confirmée.')
        tarif=m.TarifPrestation(pk=pk,libelle=valeurs['libelle'],cree_par=acteur);tarif.save(force_insert=True);n=1
    x=m.VersionTarif(tarif=tarif,version=n,auteur=acteur,motif=motif.strip(),action=action,**valeurs)
    x.full_clean();x.save();tarif.libelle=x.libelle;tarif.save(update_fields=['libelle']);return tarif


def applicable(tarif,date):
    v=tarif.versions.filter(debut__lte=date).order_by('-debut','-version').first()
    return v if v and (v.fin is None or date<v.fin) else None


def financement(accord):
    return m.FinancementPrestation.objects.filter(**{nature(accord):accord}).first()


def nature(accord):return next(k for k,v in CIBLES.items() if isinstance(accord,v))


def etat(accord):
    a=accord.accompagnement;f=financement(accord)
    return [accord._meta.model_name,str(accord.pk),str(accord.debut),str(accord.fin),str(accord.annule_le),str(a.debut),str(a.fin),
        sorted(str(x) for x in accord.beneficiaires.values_list('pk',flat=True)),str(f.pk) if f else '',f.revision_sociale if f else 0]


def jeton(accord):
    accord.refresh_from_db();accord.accompagnement.refresh_from_db()
    return signing.dumps(etat(accord),salt='financement-prestation')


def reserver(accord,attendu):
    accord.refresh_from_db();accord.accompagnement.refresh_from_db()
    try:ancien=signing.loads(attendu,salt='financement-prestation',max_age=86400)
    except (signing.BadSignature,TypeError):raise ValidationError('État non vérifiable ; rechargez la prestation.')
    if ancien!=etat(accord):raise ValidationError('La prestation ou son financement a changé. Rechargez avant de confirmer.')
    f=financement(accord)
    if f:
        from django.db.models import F
        if not m.FinancementPrestation.objects.filter(pk=f.pk,revision_sociale=ancien[-1]).update(revision_sociale=F('revision_sociale')+1):raise ValidationError('Le financement a changé.')
    return f


def totaux(version):
    return {phase:sum((x.montant for x in version.lignes.all() if x.phase==phase),Decimal('0')) for phase,_ in m.LigneCout.PHASES}


def detail_totaux(version):
    t=totaux(version)
    return [{'phase':p,'libelle':label,'cout':t[p], 'impute':sum((i.montant for i in version.imputations.all() if i.phase==p),Decimal('0')),
        'reste':t[p]-sum((i.montant for i in version.imputations.all() if i.phase==p),Decimal('0'))} for p,label in m.LigneCout.PHASES]


@serialiser('accord')
def enregistrer(acteur,accord,attendu,motif,action,lignes,imputations,**valeurs):
    droit(acteur,accord,'add_versionfinancement')
    requis(motif,'motif',240)
    if set(valeurs)!=set(ENTETE) or action not in ('definition','changement','correction'):raise ValidationError('Définition de financement incomplète.')
    requis(valeurs['source'],'source',160)
    f=reserver(accord,attendu)
    if accord.annule_le:raise ValidationError('Cette prestation est annulée ; les versions précédentes restent consultables.')
    if not f:
        suivi.exiger(acteur,'add_financementprestation')
        if action!='definition':raise ValidationError('Commencez par définir le financement.')
        f=m.FinancementPrestation(accompagnement=accord.accompagnement,cree_par=acteur,**{nature(accord):accord});f.full_clean();f.save()
    elif action=='definition':raise ValidationError('Choisissez nouvelle décision ou correction.')
    if valeurs['debut']<accord.debut or valeurs['fin'] and accord.fin and valeurs['fin']>accord.fin or accord.fin and not valeurs['fin']:
        raise ValidationError('La période de calcul doit rester dans l’autorisation. Elle ne modifie aucune prestation.')
    derniere=f.versions.first()
    v=m.VersionFinancement(financement=f,version=derniere.version+1 if derniere else 1,auteur=acteur,motif=motif.strip(),action=action,**valeurs)
    v.full_clean();v.save()
    if not lignes or len(lignes)>100 or len(imputations)>100:raise ValidationError('Précisez de 1 à 100 composantes et au plus 100 imputations.')
    for d in lignes:
        if set(d)!=set(LIGNE):raise ValidationError('Ligne de coût incomplète.')
        d=dict(d);t=d['tarif']
        for c,n in [('libelle',160),('unite',60),('justification',240)]:requis(d[c],c,n)
        if d['date']<v.debut or v.fin and d['date']>=v.fin:raise ValidationError('La date de chaque composante doit être dans la période du calcul.')
        if d['phase']=='realise' and d['date']>timezone.localdate():raise ValidationError('Un coût réalisé ne peut pas être daté dans le futur.')
        if t:
            suivi.exiger(acteur,'view_tarifprestation','view_versiontarif')
            choisi=applicable(t.tarif,d['date'])
            conserve=derniere and derniere.lignes.filter(phase=d['phase'],date=d['date'],tarif=t,prix=t.montant,libelle=t.libelle,unite=t.unite,categorie=t.categorie).exists()
            if t.devise!=v.devise or not conserve and (not choisi or choisi.pk!=t.pk or not choisi.actif):raise ValidationError('Tarif remplacé, inactif, hors période ou de devise différente ; vérifiez la ligne. Un prix antérieurement accordé peut être conservé sur sa même phase et date.')
            if t.prestataire_id and t.prestataire_id!=v.prestataire_id:raise ValidationError('Le tarif appartient à un autre prestataire.')
            if any(d[c]!=getattr(t,tc) for c,tc in [('libelle','libelle'),('unite','unite'),('categorie','categorie'),('prix','montant')]):raise ValidationError('Les valeurs d’un tarif doivent être reprises exactement ; retirez le tarif pour un prix particulier explicite.')
        try:montant=(Decimal(d['quantite'])*Decimal(d['prix'])).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        except (InvalidOperation, ValueError, TypeError) as exc:raise ValidationError('Quantité ou prix non calculable.') from exc
        x=m.LigneCout(version=v,montant=montant,**d);x.full_clean();x.save()
    for d in imputations:
        if set(d)!=set(IMPUTATION):raise ValidationError('Imputation incomplète.')
        requis(d['budget'],'budget',160)
        x=m.ImputationFinancement(version=v,**d);x.full_clean();x.save()
    for t in detail_totaux(v):
        if t['reste']<0:raise ValidationError('Les imputations dépassent le coût de la phase '+t['libelle']+'.')
    return f


def adresse(objet,jour):
    if not objet:return 'Non renseigné'
    fiche=objet.fiches.filter(debut__lte=jour).filter(Q(fin__isnull=True)|Q(fin__gt=jour)).first()
    if not fiche:return str(objet)+' (coordonnées non renseignées à cette date)'
    champs=('nom','fonction','telephone','courriel') if isinstance(objet,m.Intervenant) else ('nom','rue','code_postal','ville','pays','telephone','courriel')
    texte=' · '.join(str(getattr(fiche,c)) for c in champs if getattr(fiche,c))
    if isinstance(objet,m.Intervenant) and fiche.organisme:texte+=' · '+adresse(fiche.organisme,jour)
    return texte


def contenu_document(v,accord,modele,phase,jour):
    ls=list(v.lignes.filter(phase=phase));imps=list(v.imputations.filter(phase=phase))
    if not ls:raise ValidationError('Aucune composante chiffrée pour cette phase.')
    lignes=['Données fictives uniquement.',
        'Modèle : '+dict(m.DocumentFinancement.MODELES)[modele], 'Phase : '+dict(m.LigneCout.PHASES)[phase],
        'Prise en charge : '+str(accord.accompagnement_id), 'Prestation : '+nature(accord)+' · '+str(accord.pk),
        'Personnes : '+' ; '.join(str(p) for p in accord.beneficiaires.all()),
        'Calcul v'+str(v.version)+' ; période '+str(v.debut)+' → '+str(v.fin or 'sans fin prévue')+' (fin exclue)',
        'Émetteur : '+adresse(v.emetteur,jour),'Prestataire : '+adresse(v.prestataire,jour),'Prescripteur : '+adresse(v.prescripteur,jour),
        'Destinataire de facturation : '+adresse(v.facturation,jour),'Signataire désigné : '+adresse(v.signataire,jour),
        'Référence : '+(v.reference or 'Non renseignée'),'Source : '+v.source]
    for x in ls:lignes.append(f'{x.libelle} · {x.categorie or "sans catégorie déclarée"} · {x.date} : {x.quantite} {x.unite} × {x.prix} {v.devise} = {x.montant} {v.devise} · {x.justification}')
    cout=sum((x.montant for x in ls),Decimal('0'));affecte=sum((i.montant for i in imps),Decimal('0'))
    lignes.append(f'Total {dict(m.LigneCout.PHASES)[phase]} : {cout} {v.devise}')
    for i in imps:lignes.append(f'Financeur : {adresse(i.financeur,jour)} · budget : {i.budget} · référence : {i.reference} · {i.montant} {v.devise}')
    if v.mentions:lignes.append('Mentions particulières : '+v.mentions)
    lignes += [f'Reste sans imputation : {cout-affecte} {v.devise}',
        'Auteur du calcul : '+str(v.auteur)+' (auteur de saisie, distinct du signataire désigné).',
        'Aucune signature électronique, facture, paiement ni réalisation de prestation n’est créé par ce document.']
    return {'gabarit_version':1,'titre':dict(m.DocumentFinancement.MODELES)[modele],'lignes':lignes}


def empreinte(contenu):return hashlib.sha256(json.dumps(contenu,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


@serialiser('accord')
def emettre(acteur,accord,attendu,modele,phase,date,remplace=None):
    droit(acteur,accord,'add_documentfinancement');f=reserver(accord,attendu)
    if not f or accord.annule_le:raise ValidationError('Définissez le financement d’une prestation active avant émission.')
    if modele not in dict(m.DocumentFinancement.MODELES) or phase not in dict(m.LigneCout.PHASES):raise ValidationError('Modèle ou phase inconnu.')
    if date>timezone.localdate():raise ValidationError('La date d’émission ne peut pas être future.')
    if modele=='engagement' and phase!='autorise' or modele=='prescription' and phase!='autorise':raise ValidationError('Un bon porte sur la phase autorisée ; utilisez un relevé pour les autres phases.')
    if remplace:
        if remplace.version.financement_id!=f.pk or not m.AnnulationDocument.objects.filter(document=remplace).exists() or m.DocumentFinancement.objects.filter(remplace=remplace).exists():raise ValidationError('Le document remplacé doit être annulé, appartenir à cette prestation et ne pas avoir déjà de remplacement.')
    v=f.versions.first();contenu=contenu_document(v,accord,modele,phase,date)
    contenu['lignes'].append('Émission enregistrée par : '+str(acteur)+' ; date : '+str(date))
    if remplace:contenu['lignes'].append('Remplace le document annulé '+remplace.numero)
    x=m.DocumentFinancement(version=v,modele=modele,phase=phase,date=date,remplace=remplace,contenu=contenu,empreinte=empreinte(contenu),auteur=acteur)
    x.full_clean();x.save();return x


@serialiser('accord')
def annuler_document(acteur,accord,document,attendu,motif):
    droit(acteur,accord,'add_annulationdocument');reserver(accord,attendu);requis(motif,'motif',240)
    f=financement(accord)
    if not f or document.version.financement_id!=f.pk:raise ValidationError('Document étranger à cette prestation.')
    if m.AnnulationDocument.objects.filter(document=document).exists():raise ValidationError('Document déjà annulé.')
    x=m.AnnulationDocument(document=document,motif=motif.strip(),auteur=acteur);x.full_clean();x.save();return x


def quantites_documentees(acteur,accord,debut,fin):
    """Suggestions de quantités, jamais des prix ni des factures automatiques."""
    from datetime import timedelta
    from django.db.models import Sum
    droit(acteur,accord)
    fin=min(fin or timezone.localdate()+timedelta(days=1),timezone.localdate()+timedelta(days=1))
    if fin<=debut:raise ValidationError('Aucun fait passé dans cette période.')
    communes=dict(phase='realise',date=debut,prix=None,tarif=None)
    ref=f'Faits enregistrés du {debut} au {fin} exclu ; accord {accord.pk}. Quantité à vérifier selon la convention.'
    if isinstance(accord,m.AccordAide):
        suivi.exiger(acteur,'view_remiseaide')
        q=accord.remises.filter(annule_le__isnull=True,date__gte=debut,date__lt=fin).aggregate(q=Sum('quantite'))['q']
        return [{**communes,'libelle':accord.libelle,'unite':accord.unite,'categorie':'','quantite':q,'justification':ref}] if q is not None else []
    if isinstance(accord,m.AccordRepas):
        suivi.exiger(acteur,'view_repasdistribue')
        qs=accord.realisations.filter(annule_le__isnull=True,date__gte=debut,date__lt=fin).values('categorie_declaree').annotate(q=Sum('quantite'))
        return [{**communes,'libelle':accord.get_service_display(),'unite':'repas','categorie':x['categorie_declaree'],'quantite':x['q'],'justification':ref} for x in qs]
    suivi.exiger(acteur,'view_sejour')
    q=0
    for sejour in accord.sejours.filter(debut__lt=fin).filter(Q(fin__isnull=True)|Q(fin__gt=debut)).prefetch_related('beneficiaires'):
        q+=(min(sejour.fin or fin,fin)-max(sejour.debut,debut)).days*sejour.beneficiaires.count()
    return [{**communes,'libelle':'Nuitées de séjour documentées','unite':'personne-nuit de séjour','categorie':'','quantite':Decimal(q),
        'justification':ref+' Absences non déduites ; ne représente pas un nombre de chambres.'}] if q else []


def definir_tarif(*args,**kwargs):
    from django.db import IntegrityError
    try:return _definir_tarif(*args,**kwargs)
    except IntegrityError as e:raise ValidationError('Création déjà confirmée ou tarif modifié ; rechargez avant de réessayer.') from e
