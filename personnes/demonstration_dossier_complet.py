from acteurs.contexte import service_metier
"""Fin du méta-lot A dans les seuls jeux neufs, sans calcul de droits réels."""
from datetime import timedelta
from decimal import Decimal
from . import dossier_complet as s,bd6


@service_metier
def completer(acteur,personnes,jour,organismes,professionnels):
    def j(n):return jour+timedelta(days=n)
    source='Déclarations entièrement fictives — Établissement Les Passerelles'
    org=next(v for k,v in organismes.items() if 'Rives' in k)
    def donnees(code,**kw):
        r=s.RUBRIQUES[code]
        d={c:r.modele._meta.get_field(c).get_default() for c in r.champs};d.update(kw);return d
    def creer(nom,code,delta,**kw):
        p=personnes[nom]
        return s.enregistrer(acteur,code,p,j(delta),None,source,bd6.jeton(p),motif='Reconstitution fictive de la déclaration',**donnees(code,**kw))
    def changer(nom,code,x,delta,**kw):
        d={c:getattr(x,c) for c in s.RUBRIQUES[code].champs};d.update(kw);p=personnes[nom]
        return s.enregistrer(acteur,code,p,j(delta),None,source,bd6.jeton(p),remplace=x.pk,motif='Évolution fictive du scénario',**d)
    for i,nom in enumerate(('Samira','Thomas','Noor','Gabriel','Yannis','Robin A','Maïa')):
        p=personnes[nom];d={c:s.m.SituationAdministrative._meta.get_field(c).get_default() for c in s.ADMIN_CHAMPS}
        d.update(numero_ss='SS-FICTIF-'+str(i).zfill(3),numero_caf='CAF-FICTIF-'+str(i).zfill(3),qualification='Qualification fictive '+str(i),
            droit_sejour='Situation déclarée fictive',echeance_sejour=j(90),sans_emploi_depuis=j(-90),precision_sans_emploi='estimee')
        s.administration(acteur,p,j(-60),source,bd6.jeton(p),**d)
    x=creer('Samira','ressources',-60,libelle='Allocation fictive A',montant=Decimal('850.25'),periodicite='mensuelle',organisme=org)
    changer('Samira','ressources',x,-15,montant=Decimal('925.75'))
    creer('Samira','ressources',-60,libelle='Autre revenu déclaré fictif',montant=None,periodicite='mensuelle')
    creer('Samira','dettes',-60,creancier='Bailleur fictif',reference='DETTE-FICTIVE-A',montant=Decimal('900'),mensualite=Decimal('30'))
    creer('Samira','dettes',-60,creancier='Autre créancier fictif',montant=None)
    total=creer('Samira','dettes',-60,nature='total',montant=Decimal('1400'))
    d={c:getattr(total,c) for c in s.RUBRIQUES['dettes'].champs};d['montant']=Decimal('1450')
    s.enregistrer(acteur,'dettes',personnes['Samira'],total.debut,None,source,bd6.jeton(personnes['Samira']),correction=total.pk,motif='Erreur fictive du total saisi',**d)
    x=creer('Thomas','ressources',-60,libelle='Salaire fictif',montant=Decimal('1100'),periodicite='mensuelle')
    changer('Thomas','ressources',x,-10,libelle='Rémunération de formation fictive',montant=Decimal('450'))
    creer('Thomas','ressources',-10,libelle='Aide ponctuelle fictive',montant=Decimal('80'),periodicite='ponctuelle')
    creer('Thomas','dettes',-60,creancier='Créancier fictif en devise',montant=Decimal('200'),devise='USD')
    creer('Noor','ressources',-20,libelle='Revenu mensuel fictif',montant=Decimal('0'),periodicite='mensuelle')
    creer('Noor','ressources',-20,libelle='Revenu annuel fictif',montant=Decimal('1000'),periodicite='annuelle')
    creer('Alex','ressources',-60,etat='aucun')
    creer('Yannis','ressources',-45,etat='inconnu')
    creer('Yannis','dettes',-45,etat='inconnu')
    creer('Robin A','ressources',-20,libelle='Revenu fictif en devise',montant=Decimal('75.50'),devise='USD',periodicite='mensuelle')
    creer('Robin B','dettes',-20,etat='aucun')
    piece=creer('Samira','pieces',-60,type_document='Pièce d’identité fictive',reference='PIECE-FICTIVE-01',date_presentation=j(-60),echeance_prevue=j(30))
    creer('Samira','pieces',-60,type_document='Autre justificatif fictif',reference='PIECE-FICTIVE-02',date_presentation=j(-60))
    creer('Thomas','pieces',-60,type_document='Pièce fictive',reference='PIECE-FICTIVE-03',date_presentation=j(-70),echeance_prevue=j(-5))
    creer('Alex','pieces',-60,etat='aucun')
    creer('Samira','couvertures',-60,libelle='Couverture de base fictive',regime='Régime fictif A',organisme=org,identifiant='ADH-FICTIF-01',echeance_prevue=j(60),interlocuteur=professionnels[2])
    x=creer('Samira','couvertures',-60,libelle='Couverture complémentaire fictive',regime='Régime fictif B',organisme=org,echeance_prevue=j(-3))
    changer('Samira','couvertures',x,-10,echeance_prevue=j(90))
    creer('Thomas','couvertures',-60,libelle='Couverture fictive',regime='Régime fictif A',echeance_prevue=j(-2))
    creer('Alex','couvertures',-60,etat='inconnu')
    mesure=creer('Yannis','protections',-45,mesure='Mesure d’assistance fictive',domaine='biens',precision_portee='Portée inventée pour tester le parcours, sans qualification juridique.',
        reference_decision='DECISION-FICTIVE-A',date_decision=j(-50),echeance_prevue=j(15),organisme=org,interlocuteur=professionnels[2])
    creer('Noor','protections',-20,etat='aucun')
    x=creer('Gabriel','protections',-60,mesure='Mesure fictive avec professionnel désigné',domaine='personne',representant_intervenant=professionnels[1],interlocuteur=professionnels[2],echeance_prevue=j(-1))
    err=creer('Robin A','protections',-20,mesure='Mesure saisie pour le mauvais homonyme fictif',representant_personne=personnes['Thomas'])
    s.annuler(acteur,'protections',personnes['Robin A'],err,'Confusion fictive des homonymes Robin',bd6.jeton(personnes['Robin A']))
    # Une déclaration globale explicite termine plusieurs postes, sans effacer l'histoire.
    creer('Maïa','ressources',-40,libelle='Revenu fictif A',montant=Decimal('100'),periodicite='mensuelle')
    creer('Maïa','ressources',-40,libelle='Revenu fictif B',montant=None,periodicite='mensuelle')
    s.enregistrer(acteur,'ressources',personnes['Maïa'],j(-5),None,source,bd6.jeton(personnes['Maïa']),remplacer_ensemble=True,**donnees('ressources',etat='aucun'))
