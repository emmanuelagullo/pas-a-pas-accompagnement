#!/usr/bin/env python3
"""Captures publiques de la base jetable Les Passerelles (jamais de données réelles)."""
import argparse
from contextlib import contextmanager
import os
import signal
import subprocess
from urllib.parse import urlsplit
import sys
import time
import urllib.request
from pathlib import Path

# Lance depuis scripts/ : ajouter explicitement la racine du depot aux imports.
RACINE_DEPOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE_DEPOT))

from pas_a_pas_accompagnement.demo import IDENTIFIANT, MOT_DE_PASSE


def attendre(url, delai=300, processus=None):
    limite=time.monotonic()+delai
    derniere='aucune réponse HTTP'
    while time.monotonic()<limite:
        if processus is not None and processus.poll() is not None:
            raise RuntimeError(f'Le serveur fictif s’est arrêté (code {processus.returncode}). Consulter .ci-captures-chrs.log.')
        try:
            with urllib.request.urlopen(url + '/connexion/', timeout=2) as r:
                if r.status == 200:return
                derniere=f'HTTP {r.status}'
        except OSError as e:
            derniere=str(e)
        time.sleep(.2)
    raise RuntimeError(f'Le serveur fictif ne répond pas après {delai:g} s : {derniere}')


@contextmanager
def serveur_fictif(args):
    if not args.demarrer_serveur:
        yield None
        return
    url=urlsplit(args.base_url)
    if url.scheme!='http' or url.hostname!='127.0.0.1' or url.path or url.query or url.fragment:
        raise ValueError('--demarrer-serveur exige une URL http://127.0.0.1:PORT sans chemin.')
    env=dict(os.environ,PYTHONUNBUFFERED='1',ACCOMPAGNEMENT_HOSTS='127.0.0.1,localhost',
        ACCOMPAGNEMENT_BIND='127.0.0.1',PORT=str(url.port or 80),ACCOMPAGNEMENT_SCENARIO_DEMO='complet')
    with (RACINE_DEPOT/'.ci-captures-chrs.log').open('wb') as journal:
        processus=subprocess.Popen(['bash','start-render.sh'],cwd=RACINE_DEPOT,env=env,
            stdout=journal,stderr=subprocess.STDOUT,start_new_session=True)
        try:yield processus
        finally:
            # Un groupe de processus temporaire, jamais un fichier PID persistant.
            if processus.poll() is None:
                os.killpg(processus.pid,signal.SIGTERM)
                try:processus.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(processus.pid,signal.SIGKILL);processus.wait()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base-url', default='http://127.0.0.1:8000')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--demarrer-serveur',action='store_true',help='Démarrer puis arrêter le vrai serveur jetable pour ces captures.')
    p.add_argument('--delai-demarrage',type=float,default=300)
    args = p.parse_args()
    if args.delai_demarrage<=0:p.error('Le délai doit être positif.')
    with serveur_fictif(args) as processus:
        attendre(args.base_url,args.delai_demarrage,processus)
        capturer(args)


def capturer(args):
    from playwright.sync_api import sync_playwright
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**({'executable_path':os.environ['PWA_CHROMIUM']} if os.environ.get('PWA_CHROMIUM') else {}))
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
        page.goto(args.base_url + '/connexion/')
        page.get_by_role('heading', name='Connexion', exact=True).wait_for()
        page.screenshot(path=str(args.output / 'connexion.png'))
        # Le profil jetable affiche des identifiants publics ; ils ne sont jamais
        # extraits d'une base persistante ni d'un environnement de production.
        page.locator('input[name="username"]').fill(IDENTIFIANT)
        page.locator('input[name="password"]').fill(MOT_DE_PASSE)
        page.get_by_role('button', name='Se connecter').click()
        page.get_by_role('link', name='Statistiques').wait_for()
        # Qualification visuelle du parcours de relève, sur données fictives.
        # Vérifier les deux temporalités et les accès avant de capturer la page.
        page.goto(args.base_url + '/menages/jour/')
        page.get_by_role('heading', name='Travail du jour', level=1, exact=True).wait_for()
        page.get_by_role('heading', name='Relève actuelle — transmissions récentes', exact=True).wait_for()
        page.get_by_role('heading', name='Relève actuelle — actions explicitement en attente', exact=True).wait_for()
        page.locator('#situation-date').wait_for()
        page.get_by_role('link', name='Écrire une transmission').wait_for()
        page.get_by_role('link', name='Consulter les statistiques d’activité').wait_for()
        page.screenshot(path=str(args.output / 'travail-du-jour.png'), full_page=True)
        for slug, url, titre in (
            ('statistiques', '/statistiques/?rapport=synthese', "Statistiques d’activité"),
            ('liaison', '/menages/liaison/', 'Cahier de liaison'),
        ):
            page.goto(args.base_url + url)
            page.get_by_role('heading', name=titre, level=1, exact=True).wait_for()
            if page.locator('main').count() != 1:
                raise RuntimeError('Page sans contenu principal : ' + url)
            page.screenshot(path=str(args.output / (slug + '.png')))
        # CHRS15 : qualification des deux explorations sur la base fictive.
        # La période inclut le scénario même lorsque les dates franchissent une année.
        from datetime import date, timedelta
        from urllib.parse import urlencode
        # Le serveur jetable et le navigateur partagent la même date civile locale.
        jour = date.today()
        bornes = {'debut': (jour - timedelta(days=60)).isoformat(),
                  'fin': (jour + timedelta(days=1)).isoformat()}
        for slug, rapport, titre, mesure in (
            ('exploration-repas', 'exploration_repas', 'Repas par mois et service', 'Quantité distribuée'),
            ('exploration-hebergement', 'exploration_hebergement', 'Nuitées d’affectation par mois et lieu', 'Nuitées d’affectation théoriques'),
        ):
            params = {**bornes, 'rapport': rapport, 'regroupement': 'categorie'}
            page.goto(args.base_url + '/statistiques/?' + urlencode(params))
            page.get_by_role('heading', name=titre, exact=True).wait_for()
            tableau = page.locator('section.carte table').last
            tableau.get_by_role('columnheader', name=mesure).wait_for()
            if tableau.locator('tbody tr').count() < 1:
                raise RuntimeError('Exploration sans ligne : ' + rapport)
            if page.locator('[role="alert"]').count():
                raise RuntimeError('Erreur dans le rapport : ' + rapport)
            page.screenshot(path=str(args.output / (slug + '.png')), full_page=True)
            with page.expect_download() as telechargement:
                page.get_by_role('button', name='Exporter le CSV', exact=True).click()
            fichier = telechargement.value
            if not fichier.suggested_filename.endswith('.csv'):
                raise RuntimeError('Export CSV manquant : ' + rapport)
            with open(fichier.path(), encoding='utf-8-sig') as entree:
                entete = entree.readline()
            if ('quantite_distribuee' if rapport == 'exploration_repas'
                    else 'nuitees_affectation_theoriques') not in entete:
                raise RuntimeError('Colonnes CSV incorrectes : ' + rapport)
        # CHRS17 : recette navigateur complète, sans dépendre des valeurs chiffrées.
        # Les filtres et les exports sont vérifiés sur la même base fictive.
        page.goto(args.base_url + '/statistiques/?' + urlencode({
            **bornes, 'rapport': 'exploration_repas', 'service': 'dejeuner',
            'regroupement': 'categorie', 'comparer': '1'}))
        page.get_by_role('heading', name='Repas par mois et service', exact=True).wait_for()
        if page.locator('select#service').input_value() != 'dejeuner':
            raise RuntimeError('Le filtre de service n’est pas appliqué')
        if page.locator('select#regroupement').input_value() != 'categorie':
            raise RuntimeError('Le regroupement n’est pas appliqué')
        if not page.locator('input[name="comparer"][type="checkbox"]').is_checked():
            raise RuntimeError('La comparaison n’est pas activée')
        page.get_by_role('heading', name='Comparaison avec la période précédente', exact=True).wait_for()
        # Changer de période ne doit pas perdre les autres critères.
        page.locator('select#periode').select_option('mois')
        page.get_by_role('button', name='Appliquer').click()
        page.get_by_role('heading', name='Repas par mois et service', exact=True).wait_for()
        if (page.locator('select#service').input_value() != 'dejeuner' or
                page.locator('select#regroupement').input_value() != 'categorie' or
                not page.locator('input[name="comparer"][type="checkbox"]').is_checked()):
            raise RuntimeError('La période rapide a effacé les filtres ou la comparaison')
        # Le scénario peut être relancé sur la même base : éviter les homonymes.
        nom_modele = 'Repas du mois — recette navigateur'
        page.get_by_role('link',name='Conserver ces réglages…',exact=True).click()
        page.locator('#id_nom').fill(nom_modele)
        page.get_by_role('button',name='Enregistrer',exact=True).click()
        page.get_by_role('heading', name='Repas par mois et service', exact=True).wait_for()
        if (page.locator('select#periode').input_value() != 'mois' or
                page.locator('select#service').input_value() != 'dejeuner' or
                page.locator('select#regroupement').input_value() != 'categorie' or
                not page.locator('input[name="comparer"][type="checkbox"]').is_checked()):
            raise RuntimeError('Le modèle rouvert ne conserve pas ses critères')
        page.get_by_text('Accès utilisé :').wait_for()
        page.screenshot(path=str(args.output / 'modele-rapport.png'), full_page=True)
        with page.expect_download() as telechargement:
            page.get_by_role('button', name='Exporter le CSV', exact=True).click()
        fichier = telechargement.value
        if not fichier.suggested_filename.endswith('.csv'):
            raise RuntimeError('Export du modèle de rapport absent')
        with open(fichier.path(), encoding='utf-8-sig') as entree:
            entete = entree.readline()
        if 'quantite_distribuee' not in entete or 'service' not in entete:
            raise RuntimeError('L’export du modèle ne correspond pas au regroupement')
        # Modifier le formulaire doit ouvrir une consultation indépendante.
        page.locator('select#service').select_option('diner')
        page.get_by_role('button', name='Calculer').click()
        if page.locator('select#service').input_value() != 'diner':
            raise RuntimeError('La modification du service n’est pas appliquée')
        page.goto(args.base_url+'/dossiers/rapports/')
        page.get_by_role('link',name=nom_modele,exact=True).last.click()
        if page.locator('select#service').input_value() != 'dejeuner':
            raise RuntimeError('La consultation a modifié le modèle enregistré')
        browser.close()
    for nom in ('connexion', 'travail-du-jour', 'statistiques', 'liaison',
                'exploration-repas', 'exploration-hebergement', 'modele-rapport'):
        chemin = args.output / (nom + '.png')
        if not chemin.is_file() or chemin.stat().st_size < 1000:
            raise RuntimeError('Capture manquante ou vide : ' + str(chemin))


if __name__ == '__main__':
    main()
