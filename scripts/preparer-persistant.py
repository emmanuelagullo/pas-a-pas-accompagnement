#!/usr/bin/env python3
"""Contrôler l'espace arrêté et préserver une copie avant toute migration."""
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def preparer():
    import django
    from django.conf import settings
    from pas_communs.local import verrouiller
    from pas_communs.paquets import creer_sauvegarde
    from pas_a_pas_accompagnement.paquets import PROFIL
    path = Path(os.environ.get('ACCOMPAGNEMENT_DONNEES', ''))
    if not path.is_absolute() or path == ROOT or path.is_relative_to(ROOT) or ROOT.is_relative_to(path):
        raise ValueError('Dossier de données absolu requis, distinct du code et de ses parents.')
    if path != path.resolve():
        raise ValueError('Utiliser un chemin absolu canonique, sans lien ou traversée.')
    if path.is_symlink():
        raise ValueError('Utiliser le chemin réel du dossier de données.')
    base = path / 'accompagnement.sqlite3'
    cle = path / 'secret-key'
    # Ne pas générer une clé neuve pour une base existante.
    if base.exists() and (not cle.is_file() or not cle.read_text().strip()):
        raise ValueError('Base existante sans clé : rétablir la clé avant de continuer.')
    django.setup()
    if base.exists():
        dest = Path(os.environ.get('ACCOMPAGNEMENT_SAUVEGARDES', ''))
        if not dest.is_absolute() or dest == path or dest.is_relative_to(path) or dest.is_relative_to(ROOT):
            raise ValueError('ACCOMPAGNEMENT_SAUVEGARDES : dossier absolu hors données et code requis.')
        if dest != dest.resolve():
            raise ValueError('Utiliser le chemin réel du dossier de sauvegardes.')
        dest.mkdir(parents=True, exist_ok=True, mode=0o700)
        nom = 'avant-demarrage-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.zip'
        with verrouiller(settings.LOCAL_DIR), (dest / nom).open('xb') as sortie:
            os.chmod(sortie.name, 0o600)
            creer_sauvegarde(settings.LOCAL_DIR, sortie, profil=PROFIL)
        print('Copie privée avant migration créée. Conserver aussi une sauvegarde hors hébergement.')
    else:
        print('Nouvel espace vide : aucun compte ni fiche ne sera créé automatiquement.')


if __name__ == '__main__':
    try:
        preparer()
    except (ValueError, OSError) as exc:
        raise SystemExit(str(exc))
