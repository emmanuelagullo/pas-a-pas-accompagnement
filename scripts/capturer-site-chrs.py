#!/usr/bin/env python3
"""Captures publiques de la base jetable Les Passerelles (jamais de données réelles)."""
import argparse
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright


def attendre(url):
    for _ in range(90):
        try:
            with urllib.request.urlopen(url + '/connexion/', timeout=2) as r:
                if r.status == 200:
                    return
        except OSError:
            pass
        time.sleep(1)
    raise RuntimeError('Le serveur fictif ne répond pas')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base-url', default='http://127.0.0.1:8000')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    attendre(args.base_url)
    args.output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
        page.goto(args.base_url + '/connexion/')
        page.get_by_role('heading', name='Connexion').wait_for()
        page.screenshot(path=str(args.output / 'connexion.png'))
        # Le profil jetable affiche des identifiants publics ; ils ne sont jamais
        # extraits d'une base persistante ni d'un environnement de production.
        from pas_a_pas_accompagnement.demo import IDENTIFIANT, MOT_DE_PASSE
        page.locator('input[name="username"]').fill(IDENTIFIANT)
        page.locator('input[name="password"]').fill(MOT_DE_PASSE)
        page.get_by_role('button', name='Se connecter').click()
        page.get_by_role('link', name='Statistiques').wait_for()
        for slug, url, titre in (
            ('statistiques', '/statistiques/', "Statistiques d’activité"),
            ('liaison', '/menages/liaison/', 'Cahier de liaison'),
        ):
            page.goto(args.base_url + url)
            page.get_by_role('heading', name=titre, level=1).wait_for()
            if page.locator('main').count() != 1:
                raise RuntimeError('Page sans contenu principal : ' + url)
            page.screenshot(path=str(args.output / (slug + '.png')))
        browser.close()
    for nom in ('connexion', 'statistiques', 'liaison'):
        chemin = args.output / (nom + '.png')
        if not chemin.is_file() or chemin.stat().st_size < 1000:
            raise RuntimeError('Capture manquante ou vide : ' + str(chemin))


if __name__ == '__main__':
    main()
