"""Un seul niveau de réponses ; chaque racine et réponse reste autorisée séparément."""
from django.core.exceptions import PermissionDenied,ValidationError
from django.http import QueryDict
from django.utils import timezone
from acteurs.contexte import perimetre,courant
from . import models as m,liaisons as s,releve,transmissions


def donnees():
    q=QueryDict('',mutable=True);q.update(lia_periode='toutes',lia_sous='true',lia_filtres='1')
    q.setlist('lia_types',[k for k,v in s.TYPES]);f=s.filtres(q);f.is_valid();return f.cleaned_data


def racine(point,cle):
    if not cle or len(cle)>160:raise ValidationError('Discussion inconnue.')
    with perimetre(point.compte,service=point.service_id,statistiques='accessibles',reperage=False):
        s.Point(point.compte,point.nature,point.objet.pk if point.objet else point.service_id)
        ligne=next((x for x in s._selection(point,donnees()) if x['cle']==cle),None)
        if ligne is None:raise PermissionDenied('Cette discussion n’est plus accessible.')
        return ligne


def point_racine(compte,ligne):
    cible=ligne['_cible'];source=ligne['_source']
    with perimetre(compte,service=source.service_id if source else None):
        return s.Point(compte,s.NATURES[type(cible)],cible.pk) if cible is not None else s.Point(compte,'service',source.service_id if source else None)


def meme_cible(message,ligne):
    cible=transmissions.cible_note(message) if isinstance(message,m.NotePartagee) else None
    attendu=ligne['_cible']
    if (cible is None)!=(attendu is None):return False
    if cible is not None and s.identite(cible)!=s.identite(attendu):return False
    source=s.origine(message);origine=ligne['_source']
    if source is not None or origine is not None:
        return bool(source and origine and source.service_id==origine.service_id)
    return True


def verifier_rattachement(compte,cle,cible):
    point=s.Point(compte,s.NATURES[type(cible)],cible.pk) if cible is not None else s.Point(compte,'service',courant().service_id if courant() else None)
    ligne=racine(point,cle)
    contribution=ligne['contribution']
    if contribution is not None:
        type(contribution).objects.select_for_update().get(pk=contribution.pk)
        if m.AnnulationContribution.objects.filter(**{'note_id' if isinstance(contribution,m.NotePartagee) else 'transmission_id':contribution.pk}).exists():raise ValidationError('Ce message a été annulé ; rechargez la discussion.')
    parent=ligne['_cible']
    if (parent is None)!=(cible is None) or cible is not None and s.identite(parent)!=s.identite(cible):raise ValidationError('Une réponse conserve exactement la portée de son entrée d’origine.')
    if not point.ecriture():raise PermissionDenied
    return ligne


def assembler(point,lignes,data):
    par_cle={x['cle']:x for x in lignes}
    for x in lignes:x['reponses']=[]
    if par_cle:
        for model in (m.NotePartagee,m.Transmission):
            if not point.compte.has_perm('personnes.view_'+model._meta.model_name):continue
            qs=model.objects.filter(fil_cle__in=par_cle).select_related('auteur','annulation').prefetch_related('revisions__auteur')
            if not data['lia_annules']:qs=qs.filter(annulation__isnull=True)
            for reponse in qs:
                try:releve.lecture(point.compte,reponse)
                except PermissionDenied:continue
                ligne=par_cle[reponse.fil_cle]
                if not meme_cible(reponse,ligne):continue
                ligne['reponses'].append({'contribution':reponse,'cle':'reponse-'+model._meta.model_name+'-'+str(reponse.pk),'date':timezone.localdate(reponse.cree_le)})
    def periode(jour):return (not data['lia_debut'] or jour>=data['lia_debut']) and (not data['lia_fin'] or jour<data['lia_fin'])
    def trouve(texte):return all(mot.casefold() in texte.casefold() for mot in data['lia_q'].split())
    resultat=[]
    for x in lignes:
        texte=' '.join((x['titre'],x['cible'],str(x['auteur']),x['contribution'].contenu if x['contribution'] else x['message']))
        racine_trouvee=periode(x['date']) and trouve(texte)
        reponses=x['reponses'];reponses.sort(key=lambda r:(r['contribution'].cree_le,r['contribution'].pk))
        correspondantes=[r for r in reponses if periode(r['date']) and trouve(r['contribution'].contenu+' '+str(r['contribution'].auteur))]
        if not racine_trouvee and not correspondantes:continue
        x['fil_ouvert']=bool(data['lia_q'] and correspondantes)
        x['derniere_reponse']=reponses[-1]['contribution'].cree_le if reponses else None
        x['activite']=max(x['date'],timezone.localdate(x['derniere_reponse'])) if reponses else x['date']
        resultat.append(x)
    return sorted(resultat,key=lambda x:(x['activite'],x['derniere_reponse'] or x['saisi_le'],x['cle']),reverse=True)
