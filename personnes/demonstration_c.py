from acteurs.contexte import service_metier
"""Aides complémentaires du seul scénario neuf, sans modifier les repas des 60 jours."""
from datetime import timedelta
from decimal import Decimal as D
from . import aides as s,models as m,bd6


@service_metier
def completer(acteur,personnes,suivis,jour,organismes):
    org=next(v for k,v in organismes.items() if 'Rives' in k)
    types={}
    for code,nature,libelle,unite,fraction in [('TAM1','transport','TAM1 — carte historique de 1 voyage','carte',False),('TAM3','transport','TAM3 — carte historique de 3 voyages','carte',False),('TAM10','transport','TAM10 — carte historique de 10 voyages','carte',False),('SNCF','transport','Autres transports / SNCF — titre historique','titre',False),('RESTO','bon_alimentaire','Bon restaurant fictif','bon',False),('SUPER','bon_alimentaire','Bon supermarché fictif','bon',False),('PRODUITS','produits','Produits alimentaires fictifs','kg',True),('JOUR','accueil_jour','Accueil de jour fictif','passage',False)]:
        types[code]=s.cataloguer(acteur,s.jeton_catalogue(),'Préparation du jeu fictif',nature=nature,libelle=libelle,unite=unite,fractionnable=fraction,precision='Libellé historique ou unité fictive. Une remise ne prouve ni trajet ni utilisation.',actif=True)
    def creer(nom,code,q='5',valeur=None):
        a=suivis[nom]
        return s.accorder(acteur,a,types[code],list(a.beneficiaires.all()),bd6.jeton(a),debut=max(a.debut,jour-timedelta(days=10)),fin=min(a.fin,jour+timedelta(days=30)) if a.fin else jour+timedelta(days=30),quantite=D(q) if q else None,prestataire=org,financeur=org,valeur_bon=D(valeur) if valeur else None,devise='EUR',source='Décision entièrement fictive')
    def remise(a,q,delta=-2):
        s.remettre(acteur,a,list(a.beneficiaires.all()),min(jour+timedelta(days=delta),a.fin-timedelta(days=1)) if a.fin else jour+timedelta(days=delta),D(q),'Remise fictive',bd6.jeton(a))
        return a.remises.first()
    a=creer('Samira','TAM3');r=remise(a,'1')
    s.remettre(acteur,a,list(r.beneficiaires.all()),r.date,D('2'),'Bordereau fictif vérifié',bd6.jeton(a),motif='Quantité mal saisie fictive',correction=r.pk)
    creer('Samira','TAM10','2')
    a=creer('Noor','SNCF','2');remise(a,'1')
    a=creer('Thomas','TAM1');r=remise(a,'1')
    s.annuler(acteur,a,bd6.jeton(a),'Remise saisie par erreur pour le mauvais dossier fictif',remise=r.pk)
    a=creer('Samira','RESTO','4','12.50');r=remise(a,'2')
    s.constater(acteur,a,r.pk,jour-timedelta(days=1),D('0'),'Bons non utilisés déclarés fictifs',bd6.jeton(a))
    a=creer('Noor','SUPER','2','25');r=remise(a,'1')
    s.constater(acteur,a,r.pk,jour-timedelta(days=1),D('1'),'Utilisation déclarée fictive',bd6.jeton(a))
    a=creer('Yannis','PRODUITS','10');remise(a,'2.750')
    a=creer('Noor','JOUR',None);remise(a,'1')

    from . import hebergement as h,repas
    parent=h.creer_lieu(acteur,'Établissement fictif des Rives',organisme=org,niveau='etablissement')
    chambre=h.creer_lieu(acteur,'Chambre imaginaire A',parent=parent,niveau='chambre')
    h.creer_lieu(acteur,'Place imaginaire 1',parent=chambre,niveau='place')
    d={c:getattr(chambre,c) for c in ('libelle','parent','niveau','partenaire','organisme')};d['libelle']='Chambre imaginaire A — libellé corrigé'
    h.corriger_lieu(acteur,chambre,bd6.jeton(chambre),'Correction fictive du libellé, sans déplacement de personne',**d)
    repas.accorder(acteur,suivis['Noor'],[personnes['Noor']],jour+timedelta(days=1),jour+timedelta(days=15),'dejeuner',jours_semaine=[2,4])
