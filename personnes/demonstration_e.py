"""Appels, relève et modèles exploratoires du seul scénario neuf."""
from datetime import timedelta,time
from decimal import Decimal
from . import models as m,appels115 as s,bd6,transmissions,releve,propositions


def completer(acteur,personnes,suivis,jour,organismes,professionnels):
    from . import textes_riches as tr
    org=list(organismes.values())
    for champ,vals in [('motif_principal',['Hébergement fictif','Accès aux droits fictif','Alimentation fictive']),('lieu_appel',['Accueil fictif','Rue fictive']),('demande_secondaire115',['Repas fictif','Transport fictif','Domiciliation fictive']),('reponse115',['Information fictive','Orientation proposée fictive','Rappel convenu fictif'])]:
        for v in vals:propositions.enregistrer(acteur,champ,v,True,'Propositions entièrement fictives ; listes historiques 115 non disponibles.')
    def donner(delta,heure=None,**kw):
        d={c:m.VersionAppel115._meta.get_field(c).get_default() for c in s.CHAMPS}
        d.update(date=jour+timedelta(days=delta),heure=heure,type_appelant='inconnu',motif_principal='Hébergement fictif',details='Appel entièrement fictif de l’Établissement Les Passerelles',source='Écoute fictive pour démonstration',demandes_secondaires=[],reponses=[],etat_reponse='inconnue');d.update(kw);return d
    def creer(delta,heure=None,ps=(),**kw):return s.ecrire(acteur,s.creation(),list(ps),action='saisie',**donner(delta,heure,**kw))
    a=creer(-63,time(23,58),adultes_declares=1,enfants_declares=2,lieu_appel='Rue fictive',demandes_secondaires=['Repas fictif','Transport fictif'])
    ps=list(suivis['Samira'].beneficiaires.all())
    s.ecrire(acteur,s.jeton(a),ps,appel=a,action='suite',motif='Personnes fictives identifiées après le premier appel',**donner(-63,time(23,58),type_appelant='tiers',appelant_intervenant=None,appelant_libre='Proche fictif',menage=suivis['Samira'].menage,adultes_declares=1,enfants_declares=2,etat_reponse='apportee',reponses=['Information fictive','Rappel convenu fictif']))
    s.lier(acteur,a,s.jeton(a),'Lien explicite après ouverture fictive de la prise en charge',accompagnement=suivis['Samira'])
    for delta,h,mn,nom in [(-61,0,3,'Samira'),(-20,10,15,'Noor'),(-8,19,30,'Thomas'),(-2,8,15,'Alex')]:
        creer(delta,time(h,mn),[personnes[nom]],type_appelant='personne',appelant_personne=personnes[nom],adultes_declares=1,enfants_declares=0,etat_reponse='apportee',reponses=['Information fictive'],orientation=org[2])
    for i in range(8):
        creer(-i,time((i*3)%24,i),adultes_declares=0 if i==0 else None,enfants_declares=None,etat_reponse='sans_reponse' if i%2 else 'inconnue',lieu_appel='Accueil fictif' if i%2 else 'Rue fictive',motif_principal='Alimentation fictive' if i%3==0 else 'Hébergement fictif',demandes_secondaires=['Domiciliation fictive'] if i%2 else [])
    a=creer(-1,heure=None);s.ecrire(acteur,s.jeton(a),[],appel=a,action='correction',motif='Heure fictive retrouvée sur le brouillon',**donner(-1,time(21,45)))
    x=releve.creer_action(acteur,'Rappel fictif à préparer',jour+timedelta(days=1),appel=a)
    releve.changer_action(acteur,x,bd6.jeton(x),'Action saisie dans le mauvais contexte fictif',annuler=True)
    a=creer(-1,time(21,45));s.annuler(acteur,a,s.jeton(a),'Double saisie fictive, premier appel conservé')
    message=transmissions.transmettre(acteur,'Information de relève fictive, déclarée la veille.',jour-timedelta(days=1))
    transmissions.rectifier(acteur,message,'Information de relève fictive, date corrigée après vérification.','Correction fictive du jour, sans effacer la saisie',etat_attendu=transmissions.jeton(message),date_fait=jour-timedelta(days=2))
    note=transmissions.noter(acteur,'Suivre le rappel prévu ; aucune prestation déduite de cette note.',personne=personnes['Noor'],date_fait=jour)
    x=releve.creer_action(acteur,'Préparer le relais fictif',jour,note=note);releve.terminer(acteur,x,bd6.jeton(x))
    releve.changer_action(acteur,x,bd6.jeton(x),'Clôture fictive trop rapide : rappel encore attendu',reouvrir=True)
    # Paramètres privés uniquement ; résultats recalculés à chaque ouverture.
    params=dict(schema=1,exploration=True,population='appels',debut=(jour-timedelta(days=90)).isoformat(),fin=(jour+timedelta(days=1)).isoformat(),reference=jour.isoformat(),periode='',mesure='objets',axe='motif',croisement='etat',classes='',filtre1='',operation1='egal',valeur1='',filtre2='',operation2='egal',valeur2='')
    m.ModeleRapport.objects.create(auteur=acteur,nom='Appels fictifs — demandes et réponses',parametres=params)
    m.ModeleRapport.objects.create(auteur=acteur,nom='Appels fictifs — horaires par tranches',parametres={**params,'axe':'heure','croisement':'','classes':'Nuit | 0 | 6\nJournée | 6 | 22\nSoir | 22 | 24'})
