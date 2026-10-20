#!/usr/bin/env python3
"""Pas à Pas — Accompagnement : programme local sur données fictives."""
import argparse
import os
from pathlib import Path
import sys
import tempfile
import time

from pas_communs import local as bureau

NOM = "Pas à Pas — Accompagnement"
BASE = "accompagnement.sqlite3"


def paquet_par_defaut():
    return bureau.paquet_par_defaut("pas-a-pas-accompagnement")


def configurer(paquet):
    os.environ["ACCOMPAGNEMENT_DONNEES"] = str(paquet)
    os.environ["DJANGO_SETTINGS_MODULE"] = "pas_a_pas_accompagnement.settings_local"


def verifier_distribution():
    import django
    import webview
    from django.core.management import call_command
    from django.template.loader import get_template
    from django.contrib.staticfiles import finders
    from django.core.wsgi import get_wsgi_application
    django.setup()
    call_command("check")
    get_wsgi_application()
    get_template("installation_locale.html")
    get_template("copies_locales.html")
    get_template("personnes/liste.html")
    get_template("identites/securite.html")
    get_template("identites/mot_de_passe.html")
    if not finders.find("application.css"):
        raise RuntimeError("La feuille de style est absente de la distribution.")
    if os.name == "nt":
        import clr  # noqa: F401
    else:
        import gi
        gi.require_version("WebKit2", "4.1")
        from gi.repository import Gtk, WebKit2  # noqa: F401
    from personnes.models import Personne
    from personnes.pdf import produire
    from django.utils import timezone
    sonde = Personne(designation="Vérification fictive du programme", cree_le=timezone.now())
    if not produire(sonde).startswith(b"%PDF-"):
        raise RuntimeError("Le moteur PDF est absent de la distribution.")
    print("Distribution Pas à Pas vérifiée, moteur PDF compris.")


def main():
    projet = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    sys.path.insert(0, str(projet))
    if os.name == "nt" and getattr(sys, "frozen", False):
        os.environ.setdefault("WEASYPRINT_DLL_DIRECTORIES", str(projet))
    analyseur = argparse.ArgumentParser(description=__doc__)
    from pas_a_pas_accompagnement.version import version_application
    analyseur.add_argument("--version", action="version", version=version_application())
    analyseur.add_argument("--paquet", type=Path)
    analyseur.add_argument("--copier-paquet", type=Path, metavar="DESTINATION")
    analyseur.add_argument("--verifier-distribution", action="store_true")
    analyseur.add_argument("--sans-fenetre", action="store_true", help="ouvrir le serveur local dans votre navigateur")
    args = analyseur.parse_args()
    if args.verifier_distribution:
        # Ni migrations ni données d’essai dans le paquet utilisateur.
        with tempfile.TemporaryDirectory(prefix="pas-accompagnement-verification-") as temp:
            configurer(Path(temp))
            verifier_distribution()
        return
    if args.sans_fenetre and os.name == "nt" and getattr(sys, "frozen", False):
        analyseur.error("Le mode sans fenêtre s’utilise depuis les sources dans un terminal sous Windows.")
    explicite = args.paquet or os.environ.get("ACCOMPAGNEMENT_DONNEES")
    paquet = Path(explicite or paquet_par_defaut()).expanduser().resolve()
    ancien = projet / ".local"
    if not explicite and not (paquet / BASE).exists() and (ancien / BASE).is_file():
        raise SystemExit("Un espace #SOC1 existe dans .local. Fermez le serveur, puis utilisez "
            f"--paquet {ancien} ou --paquet {ancien} --copier-paquet {paquet}.")
    if paquet == projet or projet.is_relative_to(paquet):
        raise SystemExit("Choisissez un dossier de données distinct du programme.")
    if args.copier_paquet:
        destination = args.copier_paquet.expanduser().resolve()
        if destination == paquet or destination.is_relative_to(paquet):
            analyseur.error("la destination doit être distincte de la source")
        bureau.copier_paquet(paquet, destination, nom_base=BASE)
        return
    if not paquet.exists() and list(paquet.parent.glob(f".{paquet.name}-avant-restauration-*")):
        raise SystemExit("Paquet absent après une possible restauration interrompue. Conservez les copies précédentes.")
    os.umask(0o077)
    paquet.parent.mkdir(parents=True, exist_ok=True)
    with bureau.verrouiller(paquet):
        bureau.initialiser_paquet(paquet, nom_base=BASE)
        configurer(paquet)
        import django
        from django.core.management import call_command
        from django.core.wsgi import get_wsgi_application
        django.setup()
        if bureau.migration_necessaire(paquet, nom_base=BASE):
            bureau.proteger_avant_migration(paquet, nom_base=BASE)
        call_command("migrate", interactive=False, verbosity=0)
        call_command("collectstatic", interactive=False, verbosity=0)
        from pas_a_pas_accompagnement.paquets import restauration
        from pas_communs.paquets import appliquer_restauration
        from threading import RLock, Event
        verrou = RLock()
        redemarrer = Event()
        fenetre = None

        class CommandesFenetre:
            def appliquer_et_redemarrer(self):
                if restauration.attente() is None or fenetre is None:
                    return False
                redemarrer.set()
                fenetre.destroy()
                return True

        try:
            with bureau.ServeurBureau(get_wsgi_application(), verrou=verrou,
                    ecritures_bloquees=lambda: restauration.attente() is not None) as serveur:
                serveur.verifier_css("static/application.css")
                if args.sans_fenetre:
                    print("Adresse locale : " + serveur.url, flush=True)
                    try:
                        while True:
                            time.sleep(.25)
                    except KeyboardInterrupt:
                        pass
                else:
                    fenetre = bureau.creer_fenetre(NOM, serveur.url, commandes=CommandesFenetre())
                    import webview
                    webview.start()
        finally:
            # Même ordre que Petits Pas : arrêt/attente HTTP, connexions, renommages.
            if restauration.attente() is not None:
                from django.db import connections
                connections.close_all()
                ancien = appliquer_restauration(paquet, restauration.attente())
                print("Restauration appliquée ; état précédent conservé : " + str(ancien))
            else:
                restauration.annuler()
    if redemarrer.is_set():
        os.execv(sys.executable, [sys.executable, *sys.argv[1:]] if getattr(sys, "frozen", False)
                 else [sys.executable, *sys.argv])



def notifier(message):
    import ctypes
    ctypes.windll.user32.MessageBoxW(None, message, NOM, 0x10)


if __name__ == "__main__":
    if os.name == "nt" and getattr(sys, "frozen", False):
        bureau.demarrer_avec_journal(main,
            paquet_par_defaut().parent / "logs/dernier-demarrage.log", application=NOM,
            notifier=notifier, interactif="--verifier-distribution" not in sys.argv)
    else:
        main()
