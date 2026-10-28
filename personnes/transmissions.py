from acteurs.contexte import service_metier
"""Écriture transactionnelle des transmissions et notes métier."""
from . import textes_riches as tr
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from .models import Transmission, NotePartagee


@service_metier
def _droit(auteur, action, modele):
    if not auteur.is_authenticated or not auteur.has_perm(f"personnes.{action}_{modele}"):
        raise PermissionDenied


def _texte(valeur):
    valeur = (valeur or "").strip()
    if not valeur:
        raise ValidationError("Le texte est obligatoire.")
    return valeur


@service_metier
@transaction.atomic
def transmettre(auteur, contenu, date_fait=None, *, cle_envoi=None):
    _droit(auteur, "add", "transmission")
    date_valide(date_fait)
    return enregistrer_envoi(Transmission,cle_envoi,dict(auteur=auteur,date_fait=date_fait,**tr.colonnes('contenu',contenu,required=True)))


@service_metier
@transaction.atomic
def noter(auteur, contenu, *, personne=None, menage=None, accompagnement=None, sejour=None, accord_hebergement=None, accord_repas=None, accord_aide=None, date_fait=None, cle_envoi=None):
    _droit(auteur, "add", "notepartagee")
    cibles = [c for c in (personne, menage, accompagnement, sejour, accord_hebergement, accord_repas, accord_aide) if c is not None]
    if len(cibles) != 1:
        raise ValidationError("Une note doit avoir exactement un rattachement.")
    cible = cibles[0]
    _droit(auteur, "view", {"Menage":"menage", "Personne": "personne", "Accompagnement": "accompagnement", "Sejour": "sejour", "AccordHebergement":"accordhebergement", "AccordRepas":"accordrepas", "AccordAide":"accordaide"}[type(cible).__name__])
    date_valide(date_fait)
    return enregistrer_envoi(NotePartagee,cle_envoi,dict(auteur=auteur,date_fait=date_fait,accord_hebergement=accord_hebergement,accord_repas=accord_repas,accord_aide=accord_aide,**tr.colonnes('contenu',contenu,required=True),personne=personne,menage=menage,accompagnement=accompagnement,sejour=sejour))


@service_metier
@transaction.atomic
def rectifier(auteur, contribution, nouveau_texte, motif, *, texte_attendu=None, etat_attendu=None, date_fait=...):
    """Correction conservant chaque version, sous verrou transactionnel."""
    from .models import RevisionContribution
    modele = "transmission" if isinstance(contribution, Transmission) else "notepartagee"
    _droit(auteur, "change", modele)
    if modele == "notepartagee":
        cible = cible_note(contribution)
        _droit(auteur, "view", type(cible).__name__.lower())
    nouveau_texte, motif = tr.preparer(nouveau_texte, required=True), _texte(motif)
    objet = type(contribution).objects.select_for_update().get(pk=contribution.pk)
    if etat_attendu:
        verifier_etat(objet, etat_attendu)
    elif objet.contenu_document is not None and texte_attendu is not None:
        raise ValidationError('Rechargez la contribution enrichie avant de la corriger.')
    if texte_attendu is not None and objet.contenu != texte_attendu:
        raise ValidationError("Cette contribution a été modifiée entre-temps. Rechargez-la avant de corriger.")
    nouvelle_date=objet.date_fait if date_fait is ... else date_fait
    date_valide(nouvelle_date)
    if hasattr(objet,'annulation'):raise ValidationError("Cette contribution est annulée ; son contenu reste conservé.")
    if objet.contenu == nouveau_texte and objet.contenu_document == nouveau_texte.document and objet.date_fait==nouvelle_date:
        raise ValidationError("La correction doit modifier le texte.")
    # Comparer-et-échanger aussi sur SQLite ; le verrou de ligne seul ne suffit pas.
    condition = {'contenu_document__isnull': True} if objet.contenu_document is None else {'contenu_document': objet.contenu_document}
    change = type(objet).objects.filter(pk=objet.pk, contenu=objet.contenu,
        **condition,date_fait=objet.date_fait).update(contenu=str(nouveau_texte), contenu_document=nouveau_texte.document,date_fait=nouvelle_date)
    if change != 1:
        raise ValidationError('Cette contribution a changé. Votre saisie est conservée.')
    revision = RevisionContribution.objects.create(
        transmission=objet if modele == "transmission" else None,
        note=objet if modele == "notepartagee" else None,
        auteur=auteur, ancienne_date=objet.date_fait,nouvelle_date=nouvelle_date, ancien_texte=objet.contenu, nouveau_texte=str(nouveau_texte),
        ancien_texte_document=objet.contenu_document, nouveau_texte_document=nouveau_texte.document, motif=motif)
    objet.date_fait=nouvelle_date
    objet.contenu = str(nouveau_texte)
    objet.contenu_document = nouveau_texte.document

    return revision


def jeton(objet):
    from django.core import signing
    return signing.dumps([objet._meta.model_name, objet.pk, objet.contenu, objet.contenu_document, str(objet.date_fait)], salt='texte-contribution-v1')


def verifier_etat(objet, attendu):
    from django.core import signing
    try:
        etat = signing.loads(attendu, salt='texte-contribution-v1', max_age=86400)
    except signing.BadSignature as exc:
        raise ValidationError('Le formulaire a expiré. Votre saisie est conservée.') from exc
    if etat != [objet._meta.model_name, objet.pk, objet.contenu, objet.contenu_document, str(objet.date_fait)]:
        raise ValidationError('Cette contribution a été modifiée entre-temps. Votre saisie est conservée ; consultez la version actuelle avant de réessayer.')


CIBLES_NOTE=('menage','personne','accompagnement','sejour','accord_hebergement','accord_repas','accord_aide')

def cible_note(note):return next(getattr(note,c) for c in CIBLES_NOTE if getattr(note,c+'_id'))

def date_valide(date):
    from django.utils import timezone
    if date and date>timezone.localdate():raise ValidationError({'date_fait':'La date de la contribution ne peut pas être future.'})

@service_metier
@transaction.atomic
def annuler(auteur,contribution,attendu,motif):
    from .models import AnnulationContribution
    _droit(auteur,'add','annulationcontribution')
    modele='transmission' if isinstance(contribution,Transmission) else 'notepartagee'
    _droit(auteur,'view',modele)
    if modele=='notepartagee':_droit(auteur,'view',cible_note(contribution)._meta.model_name)
    objet=type(contribution).objects.select_for_update().get(pk=contribution.pk)
    verifier_etat(objet,attendu)
    if hasattr(objet,'annulation'):raise ValidationError('Contribution déjà annulée.')
    if not motif.strip() or len(motif)>240:raise ValidationError({'motif':'Expliquez l’annulation (240 caractères au plus).'})
    # CAS sur le texte/date avant l’ajout du statut, y compris sur SQLite.
    condition={'contenu_document__isnull':True} if objet.contenu_document is None else {'contenu_document':objet.contenu_document}
    if type(objet).objects.filter(pk=objet.pk,contenu=objet.contenu,date_fait=objet.date_fait,**condition).update(contenu=objet.contenu)!=1:raise ValidationError('Contribution modifiée ; rechargez.')
    x=AnnulationContribution(auteur=auteur,motif=motif.strip(),**{'transmission' if modele=='transmission' else 'note':objet});x.full_clean();x.save();return x


def enregistrer_envoi(modele,cle,valeurs):
    if cle is None:return modele.objects.create(**valeurs)
    x,cree=modele.objects.get_or_create(cle_envoi=cle,defaults=valeurs)
    if not cree:
        if hasattr(x,'annulation'):
            raise ValidationError("Cet envoi a déjà été annulé ; consultez le cahier avant de publier un nouveau message.")
        for champ,valeur in valeurs.items():
            attendu=valeur.pk if hasattr(valeur,'_meta') else valeur
            actuel=getattr(x,champ+'_id') if x._meta.get_field(champ).is_relation else getattr(x,champ)
            if actuel!=attendu:raise ValidationError('Cet envoi existe déjà avec un autre contenu. Consultez le cahier avant de publier un nouveau message.')
    return x
