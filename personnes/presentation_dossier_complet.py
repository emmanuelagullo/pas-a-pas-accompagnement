"""Présentation des schémas fixes ; valeurs et unités restent explicites."""
from datetime import date
from decimal import Decimal
from django.db.models import Model
from django.utils.formats import date_format,number_format
from . import dossier_complet as service


def valeur(f,v):
    if v is None or v=='':return 'Non renseigné'
    if isinstance(v,Model):return str(v)
    if isinstance(v,dict):return v.get('libelle','')+' · '+v.get('id','')
    if f.choices:return dict(f.choices).get(v,v)
    if isinstance(v,date):return date_format(v,'SHORT_DATE_FORMAT')
    if isinstance(v,Decimal):return number_format(v,2)
    return v


def lignes(modele,x,champs):
    return [(modele._meta.get_field(c).verbose_name,valeur(modele._meta.get_field(c),getattr(x,c))) for c in champs]


def snapshot(code,x):
    r=service.RUBRIQUES[code]
    return {'debut':x['debut'],'fin':x['fin'],'source':x['source'],'annulation':x.get('motif_annulation',''),
        'lignes':[(r.modele._meta.get_field(c).verbose_name,valeur(r.modele._meta.get_field(c),x.get(c))) for c in r.champs]}


def preparer(code,facts,jour,acteur):
    from . import intervenants,partenaires
    r=service.RUBRIQUES[code];faits=list(facts)
    profils={}
    if 'interlocuteur' in r.champs:
        ids=[x.interlocuteur_id for x in faits if x.interlocuteur_id]+[x.representant_intervenant_id for x in faits if getattr(x,'representant_intervenant_id',None)]
        profils={f.intervenant_id:f for f in intervenants.a_date(ids,jour)}
    organismes={}
    if 'organisme' in r.champs and acteur.has_perms(partenaires.DROITS_LECTURE):
        ids=[x.organisme_id for x in faits if x.organisme_id]
        organismes={f.partenaire_id:f for f in partenaires.a_date(ids,jour)}
    resultat=[]
    for x in faits:
        titre=x.get_etat_display() if x.etat!='detail' else 'Total de dette déclaré' if code=='dettes' and x.nature=='total' else getattr(x,r.libelle) or str(getattr(x,'organisme',''))
        resultat.append({'fait':x,'titre':titre,'lignes':lignes(r.modele,x,r.champs) if x.etat=='detail' else [],
            'echeance_depassee':bool(getattr(x,'echeance_prevue',None) and x.echeance_prevue<=jour),
            'representant_profil':profils.get(getattr(x,'representant_intervenant_id',None)),
            'profil':profils.get(getattr(x,'interlocuteur_id',None)),'organisme_fiche':organismes.get(getattr(x,'organisme_id',None))})
    return resultat
