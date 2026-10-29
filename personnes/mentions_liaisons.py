"""Mentions explicites : une notification n'accorde aucun accès au message."""
from contextvars import Context
import re
from django.core import signing
from django.core.exceptions import PermissionDenied,ValidationError,ObjectDoesNotExist
from django.db import transaction
from acteurs.contexte import perimetre
from acteurs import politique as p
from acteurs.models import LienCompteProfessionnel,Notification,Responsabilite
from . import liaisons as s,models as m,releve


def chez(compte,fonction):
    # Un destinataire est évalué dans son propre contexte, sans les caches ni
    # les sélections de l'émetteur. Aucun contexte de requête n'est modifié.
    def lire():
        with perimetre(compte,statistiques='accessibles',reperage=False):return fonction()
    return Context().run(lire)


def peut_recevoir(compte,point):
    if not compte.is_active or not p.active():return False
    def verifier():
        if not p.habilitations(compte).filter(service_id=point.service_id).exists():return False
        model=m.Transmission if point.nature=='service' else m.NotePartagee
        if not compte.has_perm('personnes.view_'+model._meta.model_name):return False
        s.Point(compte,point.nature,point.objet.pk if point.objet else point.service_id)
        if point.nature=='service':return True
        if point.origine:return p.portees(compte,model).filter(pk=point.origine.pk).exists()
        return bool(point.ds and s.lire_responsabilite(compte,Responsabilite(dossier=point.ds)))
    try:return chez(compte,verifier)
    except (PermissionDenied,ObjectDoesNotExist,ValidationError):return False


def exiger_emetteur(point):
    def verifier():
        actuel=s.Point(point.compte,point.nature,point.objet.pk if point.objet else point.service_id)
        if not actuel.ecriture():raise PermissionDenied
    chez(point.compte,verifier)


def candidats(point,q):
    exiger_emetteur(point)
    if not p.active():raise PermissionDenied
    q=q.strip()[:60]
    if len(q)<2 or not point.service_id:return []
    from acteurs.models import Habilitation
    liens=LienCompteProfessionnel.objects.filter(compte_id__in=Habilitation.objects.filter(service_id=point.service_id).values('compte_id'),compte__is_active=True,professionnel__libelle__icontains=q).exclude(compte=point.compte).select_related('compte','professionnel').order_by('professionnel__libelle','pk')
    # Préfiltre organisationnel puis contrôle de la portée exacte. Aucun compte
    # extérieur ni professionnel sans compte n'est proposé.
    resultat=[]
    for lien in liens:
        if not peut_recevoir(lien.compte,point):continue
        label=str(lien.professionnel)
        token=signing.dumps({'auteur':str(point.compte.pk),'cible':point.params(),'compte':str(lien.compte_id),'label':label},salt='mention-liaison-v1')
        resultat.append({'label':label,'jeton':token})
        if len(resultat)==12:break
    return resultat


def verifier(point,jetons,texte):
    if jetons:exiger_emetteur(point)
    if len(jetons)>20:raise ValidationError('Un message peut mentionner au plus vingt collègues.')
    from django.contrib.auth import get_user_model
    resultat={}
    for token in jetons:
        try:
            d=signing.loads(token,salt='mention-liaison-v1',max_age=86400)
            if d['auteur']!=str(point.compte.pk) or d['cible']!=point.params():raise ValueError
            compte=get_user_model().objects.get(pk=d['compte'])
            if not re.search(re.escape('@'+d['label'])+r'(?![\w])',str(texte)):continue  # Mention retirée du brouillon.
            if not peut_recevoir(compte,point):raise ValidationError('Un collègue mentionné ne peut plus lire ce message. Retirez sa mention avant de publier.')
            resultat[compte.pk]=compte
        except (signing.BadSignature,KeyError,TypeError,ValueError,ObjectDoesNotExist):raise ValidationError('Mention expirée ou invalide ; retirez-la puis sélectionnez à nouveau le collègue.')
    return list(resultat.values())


@transaction.atomic
def notifier(point,message,comptes):
    origine=s.origine(message)
    if not origine:raise PermissionDenied('La portée du message doit être établie avant sa notification.')
    for compte in comptes:
        def lire():
            courant=type(message).objects.get(pk=message.pk)
            releve.lecture(compte,courant)
            return not hasattr(courant,'annulation')
        try:autorise=chez(compte,lire)
        except (PermissionDenied,ObjectDoesNotExist):autorise=False
        if not autorise:raise ValidationError('Un collègue mentionné ne peut plus lire ce message ; rechargez les propositions.')
        Notification.objects.get_or_create(compte=compte,cle='mention:'+message._meta.model_name+':'+str(message.pk),defaults={'dossier':origine.dossier,'origine':origine,'nature':'mention'})


def contribution(compte,notification):
    o=notification.origine
    if not o or o.modele not in ('personnes.notepartagee','personnes.transmission'):raise PermissionDenied
    model=m.NotePartagee if o.modele.endswith('notepartagee') else m.Transmission
    message=model.objects.select_related('auteur').get(pk=o.identifiant)
    releve.lecture(compte,message)
    if hasattr(message,'annulation'):raise PermissionDenied
    return message


def destination(compte,message):
    cible=s.transmissions.cible_note(message) if isinstance(message,m.NotePartagee) else None
    point=s.Point(compte,s.NATURES[type(cible)],cible.pk) if cible else s.Point(compte,'service',s.origine(message).service_id)
    jour=releve.date_de(message)
    return point,point.page({'lia_periode':'dates','lia_debut':jour.isoformat(),'lia_fin':(jour+s.timedelta(days=1)).isoformat(),'lia_types':['messages'],'lia_focus':'message-'+message._meta.model_name+'-'+str(message.pk)})


def selection(point,jetons):
    resultat=[]
    for token in jetons[:20]:
        label='Mention invalide — retirer'
        try:
            d=signing.loads(token,salt='mention-liaison-v1',max_age=86400)
            if d['auteur']==str(point.compte.pk) and d['cible']==point.params():label='@'+d['label']
        except (signing.BadSignature,KeyError,TypeError):pass
        resultat.append({'jeton':token,'label':label})
    return resultat
