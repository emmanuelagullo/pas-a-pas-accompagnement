#!/usr/bin/env python3
"""Contrôler le site construit avec le vérificateur Hugo commun."""
import argparse
from pathlib import Path
import runpy


def verifier(sortie, base):
    for nom in ('index.html', 'essayer/index.html', 'premiers-pas/index.html',
                'le-projet/index.html', 'demarrer/index.html', 'guide/index.html',
                'roles/equipe/index.html', 'conception/index.html', 'css/site.css',
                'css/identite.css'):
        if not (sortie / nom).is_file():
            raise ValueError('Page ou ressource absente : ' + nom)
    chemin = Path(__file__).resolve().parent.parent / 'site/theme-communs/hugo/verifier-site.py'
    if not chemin.is_file():
        raise ValueError('Initialiser le thème : git submodule update --init site/theme-communs')
    commun = runpy.run_path(str(chemin))
    commun['verifier'](sortie, base)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sortie', type=Path, default=Path('site/public'))
    p.add_argument('--base-url', required=True)
    a = p.parse_args()
    try:
        verifier(a.sortie, a.base_url)
    except ValueError as exc:
        p.exit(1, str(exc) + '\n')
