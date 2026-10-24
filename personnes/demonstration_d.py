"""Financements et documents du scénario neuf ; ne complète jamais un essai existant."""
from datetime import timedelta
from decimal import Decimal as D
from . import models as m,financements as s,bd6


def completer(acteur,personnes,suivis,jour,organismes,professionnels):
    org=list(organismes.values());operateur=org[1];payeur=org[0];prescripteur=org[2]
    def tarif(libelle,unite,prix,categorie=''):
        return s.definir_tarif(acteur,s.creation_tarif(),'Tarif entièrement fictif',debut=jour-timedelta(days=150),fin=None,libelle=libelle,unite=unite,categorie=categorie,montant=D(prix),devise='EUR',prestataire=operateur,actif=True,source='Convention fictive de l’Établissement Les Passerelles')
    chambre=tarif('Chambre fictive','chambre-nuit','35.50')
    petit=tarif('Petit déjeuner fictif','repas','3.25')
    adulte=tarif('Déjeuner fictif adulte','repas','8.50','Adulte déclaré')
    enfant=tarif('Déjeuner fictif jeune','repas','5.25','Jeune déclaré')
    bebe=tarif('Repas fictif petite enfance','repas','0','Petite enfance déclarée')
    carte=tarif('Carte TAM3 fictive','carte','2.10')
    def ligne(t,q,phase,date=None):
        v=t.versions.first()
        return dict(phase=phase,date=date or jour-timedelta(days=2),libelle=v.libelle,unite=v.unite,categorie=v.categorie,quantite=D(q),prix=v.montant,tarif=v,justification='Quantité fictive explicitement vérifiée ; aucune déduction d’âge ni paiement.')
    def ecrire(a,ls,imps=None,action='definition',motif='Convention de démonstration entièrement fictive'):
        return s.enregistrer(acteur,a,s.jeton(a),motif,action,ls,imps or [],debut=a.debut,fin=a.fin,devise='EUR',emetteur=payeur,mentions='Bon fictif à présenter au prestataire ; aucune démarche réelle à effectuer.',prestataire=operateur,prescripteur=prescripteur,facturation=payeur,signataire=professionnels[0],reference='CONVENTION-FICTIVE',source='Établissement Les Passerelles — décision fictive')
    def imputation(montant,budget,financeur=payeur):return dict(phase='autorise',financeur=financeur,budget=budget,montant=D(montant),reference='ACCORD-FICTIF')
    # Chambres et petits déjeuners séparés ; deux financeurs, reliquat visible.
    a=suivis['Samira'].accords_hebergement.filter(annule_le__isnull=True).first()
    if a:
        ls=[ligne(chambre,'10','prevu'),ligne(chambre,'10','autorise'),ligne(petit,'15','autorise')]
        ecrire(a,ls,[imputation('300','Hébergement fictif'),imputation('80','Aide fictive',operateur)])
        doc=s.emettre(acteur,a,s.jeton(a),'engagement','autorise',jour-timedelta(days=1))
        s.annuler_document(acteur,a,doc,s.jeton(a),'Correction fictive du nombre de petits déjeuners, sans toucher aux séjours.')
        ls[-1]=ligne(petit,'12','autorise')
        ecrire(a,ls,[imputation('300','Hébergement fictif'),imputation('80','Aide fictive',operateur)],action='correction',motif='Douze petits déjeuners autorisés et non quinze.')
        s.emettre(acteur,a,s.jeton(a),'engagement','autorise',jour,remplace=doc)
    # Repas : catégories explicitement choisies ; gratuité distincte d’inconnu.
    a=suivis['Samira'].accords_repas.filter(annule_le__isnull=True).first()
    if a:ecrire(a,[ligne(adulte,'5','autorise'),ligne(enfant,'10','autorise'),ligne(bebe,'1','autorise')])
    a=suivis['Samira'].accords_aides.filter(nature='transport',libelle__contains='TAM3',annule_le__isnull=True).first()
    if a:
        ecrire(a,[ligne(carte,'5','autorise'),ligne(carte,'2','realise')],[imputation('10','Mobilité fictive')])
        s.emettre(acteur,a,s.jeton(a),'releve','realise',jour)
    # Tarif modifié après émission : aucun calcul antérieur ne change.
    v=chambre.versions.first();d={c:getattr(v,c) for c in s.TARIF};d.update(debut=jour,montant=D('37'))
    s.definir_tarif(acteur,bd6.jeton(chambre),'Nouveau prix fictif, anciens documents inchangés',tarif=chambre,action='changement',**d)
    # Une prestation au coût nul et une autre sans financement chiffré restent distinctes.
    a=suivis['Noor'].accords_aides.filter(nature='accueil_jour',annule_le__isnull=True).first()
    if a:ecrire(a,[dict(phase='autorise',date=jour-timedelta(days=2),libelle='Accueil de jour gratuit fictif',unite='passage',categorie='',quantite=D('1'),prix=D('0'),tarif=None,justification='Gratuité explicitement déclarée dans la convention fictive.')])
