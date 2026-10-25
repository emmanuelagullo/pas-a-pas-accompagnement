#!/usr/bin/env python3
"""Vraies vues Django des trois profils, sans simuler une fenêtre ou Pyodide.

Exige les dépendances serveur/PDF et pwa/requirements-pdf.txt existantes ;
aucun paquet n'est installé ici.
Les bases et comptes fictifs sont créés uniquement dans des dossiers temporaires.
"""
import os
import argparse
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile

RACINE = Path(__file__).resolve().parent.parent
VERIFIER = r'''
import os
import django
django.setup()
from datetime import date
from decimal import Decimal
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from personnes import bd6, famille, coordonnees, ouverture_prise, contacts_menage, partenaires, intervenants, interventions, complements_identite, relations_personnelles, dossier_complet, parcours, aides
from personnes.models import Personne

call_command('migrate', interactive=False, verbosity=0)
if hasattr(settings, 'STATIC_ROOT') and settings.STATIC_ROOT:
    call_command('collectstatic', interactive=False, verbosity=0)
u = get_user_model().objects.create_user('qualification-solenne-fictive')
call_command('autoriser_chrs7', u.username, verbosity=0)
call_command('autoriser_solenne', u.username, verbosity=0)
u = get_user_model().objects.get(pk=u.pk)
p = Personne.objects.create(designation='Personne fictive de qualification', cree_par=u)
a = ouverture_prise.ouvrir(u, p, [p], date(2026, 1, 1), date(2026, 6, 1), ouverture_prise.jeton(p),
    creer_menage=True, libelle_menage='Ménage fictif de qualification')
famille.renseigner(u, p, date(2026, 1, 1), 'Entretien fictif', bd6.jeton(p),
    situation_familiale='Célibataire', rapports_parentaux='', fratrie='',
    enfants_a_charge=0, enfants_non_a_charge=None, grossesse=None)
coordonnees.renseigner(u, p, date(2026, 1, 1), 'Entretien fictif', bd6.jeton(p),
    rue='Rue fictive', code_postal='00100', ville='Ville fictive', pays='Pays fictif',
    telephone='', courriel='personne@example.invalid', fax='')
contacts_menage.designer(u, a.menage, p, date(2026, 1, 1), 'Choix fictif', bd6.jeton(a.menage))
organisme = partenaires.creer(u, date(2026, 1, 1), 'Source fictive', partenaires.jeton_creation(),
    nom='Organisme fictif de qualification', rue='', code_postal='', ville='Ville partenaire fictive', pays='',
    telephone='', courriel='', fax='', informations='')
professionnel = intervenants.creer(u, date(2026, 1, 1), 'Source fictive', intervenants.jeton_creation(),
    nom='Professionnel fictif de qualification', fonction='Travail social', organisme=organisme,
    telephone='', courriel='professionnel@example.invalid', fax='')
interventions.affecter(u, a, date(2026, 1, 1), None, 'referent', professionnel, None,
    'Décision fictive', bd6.jeton(a))
complements_identite.renseigner(u,p,date(2026,1,1),'Source fictive',bd6.jeton(p),
    sexe_declare='',naissance_lieu='',naissance_ville='Ville natale fictive',naissance_pays='Pays fictif',
    nationalites=['Nationalité fictive A','Nationalité fictive B'],apatridie_declaree=None)
proche=Personne.objects.create(designation='Proche fictif de qualification',cree_par=u)
relations_personnelles.enregistrer(u,p,proche,date(2026,1,1),None,'proche','','Source fictive',bd6.jeton(p))
d=dossier_complet
admin={c:d.m.SituationAdministrative._meta.get_field(c).get_default() for c in d.ADMIN_CHAMPS}
admin.update(numero_ss='SS-FICTIF-QUALIFICATION',qualification='Qualification fictive de recette')
d.administration(u,p,date(2026,1,1),'Source fictive',bd6.jeton(p),**admin)
for code,r in d.RUBRIQUES.items():
    v={c:r.modele._meta.get_field(c).get_default() for c in r.champs}
    v.update({'evolutions':dict(libelle='Évolution fictive déclarée'), 'territoires':dict(type_territoire='agglomeration',territoire='Territoire fictif'), 'antecedents':dict(libelle='Passage institutionnel fictif de recette'), 'besoins':dict(categorie='mobilite',libelle='Besoin fictif de recette'),
        'ressources':dict(libelle='Ressource fictive de recette',montant=Decimal('10.50'),periodicite='mensuelle'),
        'dettes':dict(creancier='Créancier fictif de recette',montant=None),
        'pieces':dict(type_document='Pièce fictive de recette'),
        'couvertures':dict(libelle='Couverture fictive de recette',organisme=organisme,interlocuteur=professionnel),
        'protections':dict(mesure='Mesure fictive de recette',representant_intervenant=professionnel)}[code])
    d.enregistrer(u,code,p,date(2026,1,1),None,'Source fictive',bd6.jeton(p),**v)
for code, r in parcours.RUBRIQUES.items():
    v={c:r.version._meta.get_field(c).get_default() for c in r.champs}
    v.update({'demandes':{'etat':'acceptee','motif_demande':'Accueil fictif de recette','demandeur':'personne'},
        'orientations':{'etat':'proposee','destination':'Destination fictive de recette','motif_orientation':'Besoin fictif'},
        'objectifs':{'etat':'encours','theme':'Thème fictif','titre':'Objectif fictif de recette','horizon':'court'},
        'suivi':{'etat':'actif','raison':'Suivi fictif de recette'}}[code])
    e=parcours.creer(u,code,p,[p],date(2026,1,1),'Recette fictive',bd6.jeton(p),**v)
    if code=='demandes':parcours.lier(u,e,a,bd6.jeton(e),'Admission fictive confirmée')
type_aide=aides.cataloguer(u,aides.jeton_catalogue(),'Source fictive',nature='transport',libelle='Titre fictif de qualification',unite='titre',fractionnable=False,precision='Aucun trajet déduit',actif=True)
aide=aides.accorder(u,a,type_aide,[p],bd6.jeton(a),debut=date(2026,1,1),fin=None,quantite=Decimal('3'),prestataire=None,financeur=None,valeur_bon=None,devise='EUR',source='Décision fictive')
aides.remettre(u,aide,[p],date(2026,1,2),Decimal('1'),'Remise fictive',bd6.jeton(aide))
from personnes import financements
financements.enregistrer(u,aide,financements.jeton(aide),'Convention fictive','definition',
    [dict(phase='autorise',date=date(2026,1,1),libelle='Titre fictif',unite='titre',categorie='',quantite=Decimal('3'),prix=Decimal('2.10'),tarif=None,justification='Décision fictive de qualification')],
    [dict(phase='autorise',financeur=organisme,budget='Mobilité fictive',montant=Decimal('6.30'),reference='FICTIF')],
    debut=date(2026,1,1),fin=None,devise='EUR',emetteur=organisme,mentions='Mention fictive de qualification',prestataire=organisme,prescripteur=organisme,facturation=organisme,signataire=professionnel,reference='QUALIFICATION-FICTIVE',source='Convention fictive')
document_financement=financements.emettre(u,aide,financements.jeton(aide),'engagement','autorise',date(2026,1,2))
from personnes import appels115,transmissions,releve
from personnes.models import VersionAppel115
from django.contrib.auth.models import Permission
u.user_permissions.add(*Permission.objects.filter(content_type__app_label='personnes',codename__in=['view_transmission','add_transmission','view_notepartagee','add_notepartagee','view_actionrelais','add_actionrelais','change_actionrelais']))
u=get_user_model().objects.get(pk=u.pk)
v={c:VersionAppel115._meta.get_field(c).get_default() for c in appels115.CHAMPS}
v.update(date=date(2026,1,2),type_appelant='personne',appelant_personne=p,motif_principal='Demande fictive de qualification',source='Écoute fictive',etat_reponse='apportee',reponses=['Information fictive'],demandes_secondaires=['Repas fictif'])
appel115=appels115.ecrire(u,appels115.creation(),[p],action='saisie',**v)
appels115.lier(u,appel115,appels115.jeton(appel115),'Lien fictif explicite',accompagnement=a)
transmission=transmissions.transmettre(u,'Relève fictive de qualification',date(2026,1,2))
releve.creer_action(u,'Action fictive explicite',None,transmission=transmission)
transmissions.noter(u,'Note fictive de prestation',accord_aide=aide,date_fait=date(2026,1,2))
client = Client(HTTP_HOST=settings.ALLOWED_HOSTS[0])
client.force_login(u, backend='django.contrib.auth.backends.ModelBackend')
prefixe = settings.FORCE_SCRIPT_NAME or ''
def chemin(route, *args):
    url = reverse(route, args=args)
    return url[len(prefixe):] if prefixe and url.startswith(prefixe) else url
from personnes import pieces_dossier
from django.core.files.uploadedfile import SimpleUploadedFile
piece_f=pieces_dossier.ajouter(u,p,bd6.jeton(p),titre='Document fictif de recette',date_document=None,source='Qualification fictive',fichier=SimpleUploadedFile('fictif.txt',b'Document fictif portable'))
version_f=piece_f.versions.first()
r=client.get(chemin('dossiers:piece_telecharger',version_f.pk),secure=True)
assert r.status_code==200 and r.content==b'Document fictif portable' and 'no-store' in r['Cache-Control']
for route, args, texte in [
    ('dossiers:pieces',['personne',p.pk],'Document fictif de recette'),
    ('dossiers:appel115',[appel115.pk],'Demande fictive de qualification'),
    ('suivi:notes',['accord_aide',aide.pk],'Note fictive de prestation'),
    ('dossiers:releve_recherche',[],'Rechercher et imprimer la relève'),
    ('dossiers:explorer',[],'Explorer les populations'),
    ('dossiers:financement',['aide',aide.pk],'Mobilité fictive'),
    ('dossiers:document_financement',[document_financement.pk],document_financement.numero),
    ('dossiers:prise', ['personne', p.pk, a.pk], 'Ville fictive'),
    ('dossiers:famille', [p.pk], 'Célibataire'),
    ('dossiers:contact_menage', [a.menage_id], 'Personne fictive de qualification'),
    ('dossiers:intervenants', [], 'Professionnel fictif de qualification'),
    ('dossiers:intervenant', [professionnel.pk], 'Travail social'),
    ('dossiers:fiche_a', [p.pk,'economique'], 'Ressource fictive de recette'),
    ('dossiers:fiche_a', [p.pk,'droits'], 'Qualification fictive de recette'),
    ('dossiers:rapport_a', [], 'Ressource fictive de recette'),
    ('dossiers:complements_identite', [p.pk], 'Ville natale fictive'),
    ('dossiers:relations_personnelles', [p.pk], 'Proche fictif de qualification'),
    ('dossiers:rapport_complements_identite', [], 'Nationalité fictive B'),
    ('dossiers:rapport_relations', [], 'Proche fictif de qualification'),
    ('dossiers:interventions', [a.pk], 'Professionnel fictif de qualification'),
    ('dossiers:partenaires', [], 'Organisme fictif de qualification'),
    ('dossiers:partenaire', [organisme.pk], 'Ville partenaire fictive'),
    ('dossiers:coordonnees', [p.pk], '00100'),
    ('dossiers:rapport_familles', [], 'Célibataire'),
    ('dossiers:rapport_coordonnees', [], 'Ville fictive')]:
    response = client.get(chemin(route, *args), secure=True)
    assert response.status_code == 200, (route, response.status_code)
    assert texte in response.content.decode(), route
for code in ('pieces','couvertures','protections'):
    r=client.get(chemin('dossiers:fiche_a',p.pk,'droits'),{'rubrique':code},secure=True)
    assert r.status_code==200 and 'de recette' in r.content.decode()
for code in (*d.RUBRIQUES,'administration'):
    r=client.get(chemin('dossiers:rapport_a'),{'rubrique':code,'date':'2026-01-02','format':'csv'},secure=True)
    assert r.status_code==200 and 'text/csv' in r['Content-Type']
for code in parcours.RUBRIQUES:
    r=client.get(chemin('dossiers:parcours','personne',p.pk),{'rubrique':code},secure=True)
    assert r.status_code==200, (code,r.status_code)
    e=parcours.RUBRIQUES[code].racine.objects.get()
    assert client.get(chemin('dossiers:parcours_element',code,e.pk),secure=True).status_code==200
    r=client.get(chemin('dossiers:rapport_parcours'),{'rubrique':code,'date':'2026-01-02','format':'csv'},secure=True)
    assert r.status_code==200 and str(e.pk) in r.content.decode(),code
assert client.get(chemin('dossiers:aide',aide.pk),secure=True).status_code==200
assert client.get(chemin('dossiers:rapport_aides'),{'debut':'2026-01-01','fin':'2026-02-01','mode':'remises','format':'csv'},secure=True).status_code==200
from personnes import hebergement as heberg,annulations_arrivees as erreurs,parametrage,preparation_repas
from personnes import models as modeles
accord_erreur=heberg.accorder(u,a,[p],date(2026,1,1),None)
sejour_erreur=heberg.admettre(u,accord_erreur,[p],date(2026,1,1))
erreurs.annuler(u,sejour_erreur,erreurs.jeton(sejour_erreur),'Arrivée fictive erronée de qualification')
r=client.get(chemin('dossiers:annuler_arrivee',sejour_erreur.pk),secure=True)
assert r.status_code==200 and 'Arrivée fictive erronée' in r.content.decode()
manifest=parametrage.exporter(u)
attendu,_=parametrage.preparer(u,manifest)
nb_personnes=modeles.Personne.objects.count()
recu=parametrage.confirmer(u,attendu,'Transfert fictif de qualification',True)
assert recu.correspondances['organismes'] and modeles.Personne.objects.count()==nb_personnes
r=client.get(chemin('dossiers:parametrage'),{'format':'json'},secure=True)
assert r.status_code==200 and 'no-store' in r['Cache-Control']
assert preparation_repas.proposer(u,a,date(2026,1,1),'tous')[0]==[p]
# ST2–ST5 : mêmes parcours HTTP dans les trois profils, dont sous-chemin PWA.
from personnes import exploration, justificatifs_exploration, modeles_personnels
from urllib.parse import urlencode
params=dict(population='aides',debut='2026-01-01',fin='2026-02-01',reference='2026-01-31',mesure='quantite',axe='total',croisement='',classes='',filtre1='',operation1='egal',valeur1='',filtre2='',operation2='egal',valeur2='')
r=client.get(chemin('dossiers:explorer'),params,secure=True)
assert r.status_code==200 and all(t in r.content.decode() for t in ('Modifier retenir','Modifier afficher','Modifier compter','Modifier classer'))
from personnes.forms_exploration import ExplorationForm
f=ExplorationForm(params,acteur=u);assert f.is_valid(),f.errors
lignes,totaux,selection=exploration.calculer(u,f.cleaned_data,contributions=True)
assert list(totaux.values())==[Decimal('1')]
url=justificatifs_exploration.lien(u,f.cleaned_data,'quantite',lignes[0],2)
def sans_prefixe(url):return url[len(prefixe):] if prefixe and url.startswith(prefixe) else url
r=client.get(sans_prefixe(url),secure=True);assert r.status_code==200 and 'fin exclue' in r.content.decode()
r=client.get(sans_prefixe(url)+'&format=csv',secure=True);assert r.status_code==200 and 'text/csv' in r['Content-Type']
modele=modeles.ModeleRapport.objects.create(auteur=u,nom='Analyse fictive',parametres={**params,'schema':1,'exploration':True})
ticket=modeles_personnels.jeton(u,modele)
r=client.post(chemin('dossiers:explorer'),{**params,'nom':'Variante fictive','modele_cible':modele.pk,'attendu_modele':ticket,'action_modele':'variante'},secure=True)
assert r.status_code==302
r=client.post(chemin('dossiers:explorer'),{**params,'nom':'Remplacé explicitement','modele_cible':modele.pk,'attendu_modele':ticket,'action_modele':'remplacer'},secure=True)
assert r.status_code==302
r=client.post(chemin('dossiers:explorer'),{**params,'nom':'Formulaire périmé','modele_cible':modele.pk,'attendu_modele':ticket,'action_modele':'remplacer'},secure=True)
assert r.status_code==409 and 'Formulaire périmé' in r.content.decode()
r=client.get(chemin('dossiers:personnaliser_rapport','statistiques'),{'rapport':'repas','debut':'2026-01-01','fin':'2026-02-01'},secure=True)
assert r.status_code==302
r=client.get(sans_prefixe(r['Location']),secure=True);assert r.status_code==200
if os.environ.get('SOLENNE_VERIFIER_PDF') == 'oui':
    pdf_analyse=client.get(chemin('dossiers:explorer'),{**params,'format':'pdf'},secure=True)
    assert pdf_analyse.status_code==200 and pdf_analyse.content.startswith(b'%PDF-')
    response = client.get(chemin('personnes:fiche_pdf', p.pk), secure=True)
    assert response.status_code == 200 and response.content.startswith(b'%PDF-')
    pdf_aide=client.get(chemin('dossiers:aide_pdf',aide.pk),secure=True)
    assert pdf_aide.status_code==200 and pdf_aide.content.startswith(b'%PDF-')
    pdf_financement=client.get(chemin('dossiers:document_financement',document_financement.pk),{'format':'pdf'},secure=True)
    assert pdf_financement.status_code==200 and pdf_financement.content.startswith(b'%PDF-')
    pdf_appel=client.get(chemin('dossiers:appel115_pdf',appel115.pk),secure=True)
    assert pdf_appel.status_code==200 and pdf_appel.content.startswith(b'%PDF-')
    pdf_releve=client.get(chemin('dossiers:releve_recherche'),{'debut':'2026-01-01','fin':'2026-02-01','format':'pdf'},secure=True)
    assert pdf_releve.status_code==200 and pdf_releve.content.startswith(b'%PDF-')
    assert 'no-store' in pdf_financement['Cache-Control']
    assert 'no-store' in response['Cache-Control']
bd6.corriger_prevision(u, a, None, 'Retrait fictif', bd6.jeton(a))
a.refresh_from_db()
assert a.fin is None and a.fin_prevue is None
print(settings.SETTINGS_MODULE + ' : ouverture, lectures BD, rapports et correction : OK ; PDF : ' + ('OK' if os.environ.get('SOLENNE_VERIFIER_PDF') == 'oui' else 'NON TESTÉ (--sans-pdf)'))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sans-pdf', action='store_true', help='Valider les parcours HTML sans qualifier les moteurs PDF.')
    args = parser.parse_args()
    if not args.sans_pdf:
        absents = [nom for nom in ('weasyprint', 'fpdf') if importlib.util.find_spec(nom) is None]
        if absents:
            parser.error('Dépendances PDF absentes : ' + ', '.join(absents) + '. '
                'Installer les dépendances existantes de requirements-pdf.txt et pwa/requirements-pdf.txt '
                '(fpdf est fourni par fpdf2), ou relancer explicitement avec --sans-pdf. '
                'Aucune base de qualification créée.')
    for profil in ('pas_a_pas_accompagnement.settings_local',
                   'pas_a_pas_accompagnement.settings_serveur', 'pwa.settings'):
        with tempfile.TemporaryDirectory(prefix='solenne-profils-fictifs-') as temporaire:
            env = {k: v for k, v in os.environ.items() if not k.startswith(('ACCOMPAGNEMENT_', 'PWA_'))
                   and k not in {'DJANGO_SETTINGS_MODULE', 'DATABASE_URL'}}
            env.update(SOLENNE_VERIFIER_PDF='non' if args.sans_pdf else 'oui', DJANGO_SETTINGS_MODULE=profil, ACCOMPAGNEMENT_DONNEES=temporaire,
                ACCOMPAGNEMENT_2FA='desactive', ACCOMPAGNEMENT_HOSTS='qualification.fictive.example',
                ACCOMPAGNEMENT_CSRF_ORIGINS='https://qualification.fictive.example',
                PWA_HOST='qualification.fictive.example', PWA_ORIGIN='https://qualification.fictive.example',
                PWA_BASE_PATH='/qualification/')
            subprocess.run([sys.executable, '-c', VERIFIER], cwd=RACINE, env=env, check=True)


if __name__ == '__main__':
    main()
