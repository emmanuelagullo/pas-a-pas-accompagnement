"""Méta-lot B : histoires inventées uniquement dans les espaces d'essai neufs."""
from datetime import timedelta
from . import parcours as s, models as m, bd6, informations_suivi, propositions


def completer(acteur, personnes, suivis, jour, organismes, professionnels):
    source='Scénario fictif — Établissement Les Passerelles'
    org=next(v for k,v in organismes.items() if 'Rives' in k)
    def j(n):return jour+timedelta(days=n)
    def valeurs(code,**kw):
        r=s.RUBRIQUES[code];d={c:r.version._meta.get_field(c).get_default() for c in r.champs}
        d.update({'demandes':{'etat':'attente','motif_demande':'Mise à l’abri fictive','demandeur':'personne'},
            'orientations':{'etat':'proposee','destination':'Service fictif','motif_orientation':'Besoin déclaré fictif'},
            'objectifs':{'etat':'encours','theme':'Accès au logement fictif','titre':'Préparer une solution fictive','horizon':'court'},
            'suivi':{'etat':'actif','raison':'Suivi fictif en cours'}}[code]);d.update(kw);return d
    def creer(code,obj,ps,day,**kw):
        ctx={k:kw.pop(k) for k in ('accompagnement','demande') if k in kw}
        return s.creer(acteur,code,obj,ps,day,source,bd6.jeton(obj),**ctx,**valeurs(code,**kw))
    def changer(code,e,day,**kw):
        x=e.versions.first();d={c:getattr(x,c) for c in s.RUBRIQUES[code].champs};d.update(kw)
        return s.enregistrer(acteur,code,e,day,source,bd6.jeton(e),**d)
    for champ,label in [('motif_demande','Mise à l’abri fictive'),('motif_decision','Absence de place fictive'),('theme','Accès au logement fictif'),('type_destination','Logement accompagné fictif')]:
        propositions.enregistrer(acteur,champ,label,True,'Préparation du scénario fictif')
    demandes={}
    for i,nom in enumerate(('Samira','Thomas','Noor','Gabriel','Yannis')):
        a=suivis[nom];ps=list(a.beneficiaires.all());obj=a.menage
        e=creer('demandes',obj,ps,a.debut-timedelta(days=10),groupe_demande='Famille fictive' if len(ps)>1 else 'Personne seule déclarée',demandeur='professionnel',demandeur_professionnel=professionnels[i%3],
            prescripteur=professionnels[(i+1)%3],organisme_orienteur=org,provenance='Lieu antérieur fictif',
            dernier_hebergement_type='Hébergement précaire fictif',dernier_hebergement_duree='Quelques semaines déclarées',dernier_hebergement_lieu='Lieu imaginaire '+str(i),accueil_prevu=a.debut,activite='urgence' if nom=='Thomas' else 'chrs')
        changer('demandes',e,a.debut-timedelta(days=5),etat='acceptee',motif_decision='Accord fictif avant accueil')
        s.lier(acteur,e,a,bd6.jeton(e),'Demande fictive ayant précédé cette prise en charge')
        demandes[nom]=e
        ancienne=a.informations.first();d={c:getattr(ancienne,c) if ancienne else '' for c in informations_suivi.CHAMPS}
        # Reuse rich documents, without converting them to plain text during this version.
        from .textes_riches import lire_objet
        for c in ('objectifs_courts','objectifs_longs'):
            if ancienne:d[c]=lire_objet(ancienne,c)
        d['activite']='urgence' if nom=='Thomas' else 'chrs'
        informations_suivi.enregistrer(acteur,a,informations_suivi.jeton(a,ancienne),'Activité explicitée dans le scénario fictif',**d)
    for nom,etat,delta in [('Inès','acceptee',-8),('Alex','refusee',-12),('Maïa','retiree',-7),('Robin A','attente',-5),('Robin B','refusee',-6)]:
        e=creer('demandes',personnes[nom],[personnes[nom]],j(delta-3),accueil_prevu=j(15),activite='urgence')
        if etat!='attente':changer('demandes',e,j(delta),etat=etat,motif_decision='Décision ou retrait entièrement fictif')
        if nom=='Alex':
            x=e.versions.first();d={c:getattr(x,c) for c in s.RUBRIQUES['demandes'].champs};d['motif_decision']='Absence de place fictive'
            s.enregistrer(acteur,'demandes',e,x.debut,source,bd6.jeton(e),correction=x.pk,motif='Motif de refus incomplet lors de la saisie fictive',**d)
    # Deux orientations concurrentes, puis des résultats différents ; aucune sortie déduite.
    obj=suivis['Samira'].menage
    for dest,etat,delta in [('Résidence imaginaire A','realisee',-4),('Solution fictive B','refusee',-2)]:
        o=creer('orientations',obj,[personnes['Samira']],j(-15),accompagnement=suivis['Samira'],demande=demandes['Samira'],destination=dest,
            type_destination='Logement accompagné fictif',organisme=org,interlocuteur=professionnels[2],date_prevue=j(7))
        changer('orientations',o,j(delta),etat=etat,resultat='Rendez-vous fictif réalisé' if etat=='realisee' else 'Proposition fictive refusée par la personne')
    o=creer('orientations',personnes['Inès'],[personnes['Inès']],j(-3),destination='Point d’accueil fictif',date_prevue=j(10))
    # Objectifs personnels : contextes d'origine distincts, histoire indépendante des prises.
    for nom,etat in [('Samira','atteint'),('Thomas','suspendu'),('Noor','encours'),('Yannis','abandonne')]:
        p=personnes[nom];a=suivis[nom]
        o=creer('objectifs',p,[p],a.debut,accompagnement=a,titre='Démarche de logement fictive — '+nom,echeance=j(30),texte='Étape inventée lors de l’accueil fictif.')
        if etat!='encours':changer('objectifs',o,j(-2),etat=etat,texte='Bilan fictif de la démarche : '+etat)
    p=personnes['Thomas'];a=suivis['Thomas'].menage.accompagnements.order_by('debut').first()
    creer('objectifs',p,[p],a.debut,accompagnement=a,horizon='long',titre='Projet fictif poursuivi entre plusieurs prises en charge',texte='Cet objectif reste en cours après la clôture de sa prise en charge d’origine.',echeance=j(45))
    ancienne=a.informations.first();d={c:getattr(ancienne,c) if ancienne else '' for c in informations_suivi.CHAMPS}
    from .textes_riches import lire_objet
    for c in ('objectifs_courts','objectifs_longs'):
        if ancienne:d[c]=lire_objet(ancienne,c)
    d.update(activite='chrs',motif_sortie='Changement d’activité fictif',destination_sortie='Relais fictif vers activité urgence',orientation_sortie='Continuité du suivi fictive')
    informations_suivi.enregistrer(acteur,a,informations_suivi.jeton(a,ancienne),'Relais fictif entre activités ; pas de sortie définitive du dossier',**d)

    err=creer('objectifs',personnes['Robin A'],[personnes['Robin A']],j(-3),titre='Objectif saisi pour le mauvais Robin fictif')
    s.annuler(acteur,'objectifs',err,'Confusion d’homonymes fictifs ; objectif à ressaisir sur le bon dossier',bd6.jeton(err))
    for nom in ('Samira','Thomas','Gabriel'):
        p=personnes[nom];e=creer('suivi',p,[p],j(-40))
        changer('suivi',e,j(-10),etat='veille' if nom=='Thomas' else 'termine',raison='Évolution du suivi fictive ; les prises et prestations ne changent pas')
        if nom=='Thomas':changer('suivi',e,j(-1),etat='actif',raison='Reprise de contact fictive')
