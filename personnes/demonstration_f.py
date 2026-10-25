"""Documents et rapports de consolidation, exclusivement dans le jeu neuf."""
from django.core.files.uploadedfile import SimpleUploadedFile
from . import pieces_dossier as s,bd6,models as m


def enrichir(acteur,personnes,suivis,jour):
    p=personnes['Noor']
    from . import dossier_complet as dc,coordonnees
    from datetime import timedelta
    dc.enregistrer(acteur,'antecedents',p,jour-timedelta(days=10),None,'Entretien fictif',bd6.jeton(p),etat='detail',libelle='Accueil institutionnel antérieur fictif',frequentation='oui',organisme=None,periode_declaree='Quelques mois déclarés, date inconnue',date_entree=None,date_sortie=None,precision_dates='')
    dc.enregistrer(acteur,'territoires',p,jour-timedelta(days=10),None,'Entretien fictif',bd6.jeton(p),etat='detail',type_territoire='agglomeration',territoire='Agglomération fictive des Passerelles',anciennete_declaree='Deux ans déclarés',depuis=None,precision_depuis='')
    dc.enregistrer(acteur,'evolutions',p,jour-timedelta(days=9),None,'Bilan fictif',bd6.jeton(p),etat='detail',domaine='demarches',libelle='Reprise déclarée des démarches fictives')
    contact=coordonnees.a_date([p],jour).first()
    if contact:
        valeurs={c:getattr(contact,c) for c in coordonnees.CHAMPS};valeurs['usage_adresse']='dernier_fixe'
        coordonnees.renseigner(acteur,p,contact.debut,'Précision fictive de l’adresse déclarée',bd6.jeton(p),motif='Qualification fictive : dernier domicile fixe, pas adresse actuelle déduite',correction=contact.pk,**valeurs)
    x=dc.enregistrer(acteur,'besoins',p,jour-timedelta(days=10),None,'Entretien fictif',bd6.jeton(p),etat='detail',categorie='mobilite',libelle='Accueil de plain-pied fictif',adaptation='Besoin pratique fictif, sans diagnostic médical.')
    dc.enregistrer(acteur,'besoins',p,x.debut,None,'Relecture fictive',bd6.jeton(p),correction=x.pk,motif='Précision fictive de l’adaptation',etat='detail',categorie='mobilite',libelle='Accueil de plain-pied fictif',adaptation='Éviter les escaliers pendant la période déclarée fictive.')
    piece=s.ajouter(acteur,p,bd6.jeton(p),titre='Préparation fictive du rendez-vous',date_document=jour,source='Scénario fictif Établissement Les Passerelles',fichier=SimpleUploadedFile('rendez-vous-fictif.txt','Exemple fictif de document externe. Aucun rendez-vous réel.\n'.encode()))
    s.ajouter(acteur,p,bd6.jeton(p),piece=piece,titre='Préparation fictive du rendez-vous — titre corrigé',date_document=jour,source='Relecture fictive',fichier=None,motif='Précision du titre, fichier initial conservé')
    menage=suivis['Samira'].menage
    piece=s.ajouter(acteur,menage,bd6.jeton(menage),titre='Brouillon fictif associé par erreur',date_document=None,source='Exercice fictif',fichier=SimpleUploadedFile('brouillon-fictif.txt',b'Brouillon fictif sans donnee reelle.'))
    s.annuler(acteur,piece,bd6.jeton(menage),'Document fictif associé au mauvais contexte ; historique conservé')
    from datetime import timedelta
    params=dict(schema=1,exploration=True,population='sejours',debut=(jour-timedelta(days=60)).isoformat(),fin=(jour+timedelta(days=1)).isoformat(),reference=jour.isoformat(),mesure='quantite',axe='etat',croisement='',classes='',filtre1='',operation1='egal',valeur1='',filtre2='',operation2='egal',valeur2='',nombre_mesures='4',mesure2='nuitees_adultes',mesure3='nuitees_enfants',mesure4='nuitees_age_inconnu')
    m.ModeleRapport.objects.create(auteur=acteur,nom='Nuitées fictives — total et âges à chaque nuit',parametres=params)
