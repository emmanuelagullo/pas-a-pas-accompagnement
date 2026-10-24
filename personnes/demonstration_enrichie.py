"""Suite du scénario neuf Établissement Les Passerelles ; jamais exécutée à sa réouverture."""
from datetime import date, timedelta
from . import models as m, suivi, repas, hebergement as h, bd6, famille, coordonnees, contacts_menage, partenaires, intervenants, interventions, propositions, social


def completer(nadia, remi, camille, personnes, suivis, jour):
    def j(delta):return jour+timedelta(days=delta)
    source='Scénario intégralement fictif Établissement Les Passerelles'
    for champ, valeur in [('situation_familiale','Séparée'),('situation_familiale','En couple'),
            ('situation_familiale','Célibataire'),('ville','Ville des Passerelles (fictive)'),
            ('ville','Ville des Rives (fictive)'),('pays','Pays fictif'),('code_postal','00000'),
            ('fonction','Accompagnement social'),('fonction','Accès aux droits')]:
        propositions.enregistrer(nadia,champ,valeur,True,'Préparation du jeu fictif')
    orgs={}
    for nom,ville in [('Établissement Les Passerelles','Ville des Passerelles'),('Association des Rives','Ville des Rives'),('Maison des droits','Ville des Passerelles')]:
        orgs[nom]=partenaires.creer(nadia,j(-120),source,partenaires.jeton_creation(),
            nom=nom+' (fictive)',rue='Allée imaginaire',code_postal='00000',ville=ville+' (fictive)',pays='Pays fictif',
            telephone='+00 000 000 000',courriel='organisme-'+str(len(orgs)+1)+'@example.invalid',fax='',informations='Coordonnées fictives ; aucun appel ni envoi nécessaire pour la recette.')
    profs=[]
    for nom,fonction,org in [('Maëlle','Accompagnement social','Établissement Les Passerelles'),('Joël','Accompagnement social','Association des Rives'),('Lou','Accès aux droits','Maison des droits')]:
        profs.append(intervenants.creer(nadia,j(-120),source,intervenants.jeton_creation(),nom=nom+' (professionnel fictif)',fonction=fonction,organisme=orgs[org],telephone='+00 000 000 000',courriel=nom.lower().replace('ë','e')+'@example.invalid',fax=''))
    # Données explicitement connues/estimées dans le scénario, jamais déduites du ménage.
    for nom, age in [('Samira',36),('Lina',12),('Adam',7),('Thomas',41)]:
        p=personnes[nom];p.precision_naissance='exacte';p.date_naissance=date(jour.year-age,4,10);p.full_clean();p.save()
    for nom in ('Noor','Inès','Gabriel','Éva','Yannis'):
        personnes[nom]=m.Personne.objects.create(designation=nom+' (fictif)',cree_par=nadia)
    personnes['Yannis'].precision_naissance='annee_estimee';personnes['Yannis'].annee_naissance=jour.year-54;personnes['Yannis'].save()
    for nom,membres,debut in [('Noor',['Noor'],-110),('Gabriel et Éva',['Gabriel','Éva'],-90),('Yannis',['Yannis'],-45)]:
        ps=[personnes[n] for n in membres];menage=suivi.creer_menage(nadia,nom+' — Établissement Les Passerelles (fictif)',ps,j(debut))
        if nom=='Noor':
            ancien=suivi.ouvrir(nadia,menage,ps,j(-110));suivi.clore(nadia,ancien,j(-80))
            a=suivi.ouvrir(nadia,menage,ps,j(-20))
        else:a=suivi.ouvrir(nadia,menage,ps,j(debut))
        suivis[membres[0]]=a
    # Inès reste un dossier individuel sans ménage ni prise : tester la première ouverture courte.
    a=suivis['Gabriel'];ps=list(a.beneficiaires.all());accord=h.accorder(remi,a,ps,j(-30),j(-2))
    sejour=h.admettre(remi,accord,ps,j(-30));lieu=h.creer_lieu(remi,'Logement diffus des Rives (fictif)',organisme=orgs['Association des Rives'])
    h.ajouter_periode(remi,sejour,j(-30),None,lieu=lieu);h.sortir(remi,sejour,j(-2))
    suivi.clore(nadia,suivis['Yannis'],j(-5))
    accord=repas.accorder(camille,suivis['Noor'],[personnes['Noor']],j(-20),None,'petit_dejeuner')
    for delta in (-3,-2,-1):repas.distribuer(camille,accord,personnes['Noor'],j(delta),1)
    # Plusieurs versions d'adresse, une correction distincte d'un déménagement.
    for nom in ('Samira','Thomas','Noor'):
        p=personnes[nom]
        def v(ville):return dict(rue='Allée imaginaire\nBâtiment de démonstration',code_postal='00000',ville=ville,pays='Pays fictif',telephone='+00 000 000 000',courriel=nom.lower()+'@example.invalid',fax='')
        coordonnees.renseigner(nadia,p,j(-60),source,bd6.jeton(p),**v('Ville des Passerelles (fictive)'))
        if nom=='Thomas':
            f=coordonnees.renseigner(nadia,p,j(-10),source,bd6.jeton(p),**v('Ville des Rives (fictive)'))
            coordonnees.renseigner(nadia,p,j(-10),source,bd6.jeton(p),correction=f.pk,motif='Correction fictive du complément d’adresse',**{**v('Ville des Rives (fictive)'),'rue':'Allée imaginaire\nAppartement de démonstration'})
    contacts_menage.designer(nadia,suivis['Samira'].menage,personnes['Samira'],j(-60),source,bd6.jeton(suivis['Samira'].menage))
    famille.renseigner(nadia,personnes['Noor'],j(-20),source,bd6.jeton(personnes['Noor']),situation_familiale='Célibataire',rapports_parentaux='',fratrie='',enfants_a_charge=0,enfants_non_a_charge=None,grossesse=None)
    def mission(a,prof,debut,role='referent'):
        return interventions.affecter(nadia,a,j(debut),None,role,prof,None,source,bd6.jeton(a))
    a=suivis['Samira'];x=mission(a,profs[0],-60)
    interventions.affecter(nadia,a,x.debut,j(-20),x.role,profs[0],None,source,bd6.jeton(a),correction=x.pk,cloture=True,motif='Relais professionnel fictif')
    mission(a,profs[1],-20);mission(a,profs[2],-40,'suivi_exterieur')
    mission(suivis['Thomas'],profs[0],-49);mission(suivis['Noor'],profs[0],-20);mission(suivis['Noor'],profs[1],-20)
    a=suivis['Alex'];x=mission(a,profs[2],-50,'orienteur');interventions.annuler(nadia,a,x,'Erreur fictive de dossier ; aucune orientation effective',bd6.jeton(a))
    social.evenement(nadia,suivis['Noor'],personnes['Noor'],j(-3),'Reprise fictive de contact après une première prise en charge close.',source)
    population_elargie(nadia, personnes, suivis, jour, profs, source)
    parcours_repetes(nadia, remi, camille, suivis, jour)
    identites_et_liens(nadia, personnes, jour)
    from .demonstration_dossier_complet import completer as completer_dossier
    completer_dossier(nadia, personnes, jour, orgs, profs)


def population_elargie(nadia, personnes, suivis, jour, profs, source):
    """26 personnes de plus : listes longues et cas limites reproductibles."""
    from . import informations_suivi
    def j(delta):return jour+timedelta(days=delta)
    groupes=[['Robin A'],['Robin B'],['Léo'],['Maïa'],['Sol'],['Tao'],
        ['Ana','Luis'],['Zoé','Nils'],['Mina','Ari'],['Cam','Noé'],
        ['Aïcha','Malik','Sara','Élie','Aya','Tom'],['Louise','Paul','Rose','Milo','Alix','Owen']]
    menages=[]
    for i,noms in enumerate(groupes):
        ps=[]
        for n,nom in enumerate(noms):
            libelle='Robin' if nom.startswith('Robin ') else nom
            p=m.Personne(designation=libelle+' (fictif)',cree_par=nadia)
            # Certains renseignements sont délibérément inconnus ; pas d'âge
            # déduit des positions dans le ménage ni de date au 1er janvier.
            if i%3==0:
                p.precision_naissance='annee_estimee';p.annee_naissance=jour.year-30-n
            p.full_clean();p.save();personnes[nom]=p;ps.append(p)
        debut=-55+2*i
        menage=suivi.creer_menage(nadia,' / '.join(noms)+' — Établissement Les Passerelles (fictif)',ps,j(-150 if i<3 else debut))
        menages.append(menage)
        if i<3:
            ancien=suivi.ouvrir(nadia,menage,ps,j(-150));suivi.clore(nadia,ancien,j(-100))
        # Dernier ménage : un membre n'est pas bénéficiaire de cette prise.
        a=suivi.ouvrir(nadia,menage,ps[:-1] if i==11 else ps,j(debut));suivis[noms[0]]=a
        cible=ps[0]
        for dim,val in [('logement','sans_solution' if i%2 else 'logement_autonome'),
                ('emploi','sans_emploi' if i%3 else 'emploi'),
                ('ressources','sans_ressources' if i%2 else 'inconnu')]:
            bd6.renseigner(nadia,cible,dim,val,j(debut),source,bd6.jeton(cible))
        if i%2==0:
            bd6.renseigner(nadia,cible,'emploi','formation',j(-10),source,bd6.jeton(cible))
        mission=interventions.affecter(nadia,a,j(debut),None,'referent',profs[i%3],None,source,bd6.jeton(a))
        info={c:'' for c in informations_suivi.CHAMPS}
        info.update(provenance='Accueil volontaire fictif',motif_entree='Accompagnement des démarches',
            objectifs_courts='Préparer un entretien fictif et faire le point sur les droits.',
            objectifs_longs='Consolider une solution de logement et le parcours choisi.')
        informations_suivi.enregistrer(nadia,a,informations_suivi.jeton(a,None),'Projet fictif initial',**info)
        if i<5:suivi.clore(nadia,a,j(-6+i))
        if i==0:
            bd6.commenter(nadia,cible,'Homonyme fictif : vérifier les identités avant toute association.','',bd6.jeton(cible))
    # Noé change de ménage ; ses anciens bénéfices ne sont pas réécrits et il
    # ne devient pas automatiquement bénéficiaire de la prise du nouveau ménage.
    lien=menages[9].appartenances.get(personne=personnes['Noé'])
    suivi.clore(nadia,lien,j(-3));suivi.ajouter_appartenance(nadia,menages[10],personnes['Noé'],j(-3))


def parcours_repetes(nadia, remi, camille, suivis, jour):
    """Quatre ou cinq prises par dossier, avec plusieurs prestations chacune."""
    from . import informations_suivi
    def j(delta):return jour+timedelta(days=delta)
    lieu=m.LieuHebergement.objects.filter(libelle__contains='unité A').get()
    for cle,cible in [('Robin A',5),('Robin B',5),('Léo',5),('Noor',5),('Samira',5),('Thomas',5),('Gabriel',4),('Maïa',4),('Sol',4)]:
        recente=suivis[cle];menage=recente.menage;ps=list(recente.beneficiaires.all())
        nombre=cible-menage.accompagnements.count()
        for p in ps:
            premier=menage.appartenances.filter(personne=p).order_by('debut').first()
            if premier.debut>j(-450):suivi.ajouter_appartenance(nadia,menage,p,j(-450),premier.debut)
        for i in range(nombre):
            debut=-450+i*60;fin=debut+24
            a=suivi.ouvrir(nadia,menage,ps,j(debut),j(fin))
            accord=h.accorder(remi,a,ps,j(debut),j(debut+14))
            for s in h.admettre_individuellement(remi,accord,ps,j(debut+1)):
                h.ajouter_periode(remi,s,j(debut+1),None,lieu=lieu)
                h.ajouter_periode(remi,s,j(debut+4),j(debut+6),absence=True)
                h.sortir(remi,s,j(debut+14))
            for service in ('petit_dejeuner','dejeuner'):
                r=repas.accorder(camille,a,ps,j(debut),j(debut+14),service)
                for p in ps:
                    for delta in (1,2):repas.distribuer(camille,r,p,j(debut+delta),1)
            donnees={c:'' for c in informations_suivi.CHAMPS}
            donnees.update(provenance='Orientation fictive antérieure',motif_entree='Accueil temporaire fictif',
                objectifs_courts='Organiser un hébergement temporaire et les repas.',
                objectifs_longs='Préparer une solution choisie avec la personne.',
                motif_sortie='Fin de cette étape fictive',destination_sortie='Solution déclarée dans le scénario')
            informations_suivi.enregistrer(nadia,a,informations_suivi.jeton(a,None),'Projet historique fictif',**donnees)
            bd6.commenter(nadia,a,'Étape fictive '+str(i+1)+' : hébergement et deux services de repas ; accompagnement social distinct des prestations.','',bd6.jeton(a))
            suivi.clore(nadia,a,j(fin))


def identites_et_liens(nadia,personnes,jour):
    """Déclarations explicitement fictives ; aucun lien inféré du ménage."""
    from . import complements_identite as identites,relations_personnelles as liens
    def j(delta):return jour+timedelta(days=delta)
    source='Déclarations inventées pour Établissement Les Passerelles'
    def identite(nom,delta,nationalites,**extras):
        p=personnes[nom]
        v=dict(sexe_declare='',naissance_lieu='',naissance_ville='Ville natale fictive',naissance_pays='Pays natal fictif',nationalites=nationalites,apatridie_declaree=None)
        v.update(extras)
        return identites.renseigner(nadia,p,j(delta),source,bd6.jeton(p),**v)
    identite('Samira',-60,['Nationalité fictive A'],sexe_declare='Féminin')
    c=identite('Samira',-20,['Nationalité fictive A','Nationalité fictive B'],sexe_declare='Féminin')
    identites.renseigner(nadia,personnes['Samira'],c.debut,source,bd6.jeton(personnes['Samira']),
        correction=c.pk,motif='Correction fictive du lieu de naissance',sexe_declare=c.sexe_declare,
        naissance_lieu='Lieu imaginaire corrigé',naissance_ville=c.naissance_ville,naissance_pays=c.naissance_pays,
        nationalites=c.nationalites,apatridie_declaree=None)
    identite('Thomas',-60,['Nationalité fictive B'],sexe_declare='Masculin')
    identite('Yannis',-45,[],naissance_ville='',naissance_pays='')
    def rel(nom,autre,delta,role):
        p=personnes[nom]
        return liens.enregistrer(nadia,p,personnes[autre],j(delta),None,role,'',source,bd6.jeton(p))
    rel('Samira','Lina',-60,'parent');rel('Samira','Adam',-60,'parent');rel('Lina','Adam',-60,'fratrie')
    x=rel('Noor','Thomas',-20,'contact')
    liens.enregistrer(nadia,personnes['Noor'],personnes['Thomas'],x.debut,None,'contact','Contacter seulement après échange avec Noor',source,
        bd6.jeton(personnes['Noor']),correction=x.pk,motif='Précision omise lors de la saisie fictive')
    x=rel('Gabriel','Éva',-90,'couple')
    liens.enregistrer(nadia,personnes['Gabriel'],personnes['Éva'],j(-5),None,'proche','Lien amical déclaré après séparation fictive',source,
        bd6.jeton(personnes['Gabriel']),remplace=x.pk)
    x=rel('Robin A','Robin B',-20,'fratrie')
    liens.annuler(nadia,personnes['Robin A'],x,'Homonymes fictifs confondus ; aucun lien connu',bd6.jeton(personnes['Robin A']))
