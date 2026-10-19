"""Contenu de la fiche personne, indépendant des moteurs de rendu."""
from django.template.loader import render_to_string
from django.utils import timezone


def produire(personne, *, navigateur=False):
    from pas_communs.pdf import fiche_texte, rendre_html
    from django.conf import settings
    contexte = {'personne': personne, 'edite_le': timezone.localtime()}
    if navigateur:
        return fiche_texte('Pas à Pas — Fiche personne', [
            'Données fictives uniquement',
            'Nom d’usage ou identifiant provisoire : '+personne.designation,
            'Prénom : '+(personne.prenom or 'Non renseigné'),
            'Identifiant de la fiche : '+str(personne.pk),
            'Fiche créée le : '+timezone.localtime(personne.cree_le).strftime('%d/%m/%Y à %H:%M'),
            'Éditée le : '+contexte['edite_le'].strftime('%d/%m/%Y à %H:%M'),
        ])
    def refuser(url):
        # Aucun réseau, fichier ou média autorisé dans cette fiche sans images.
        raise ValueError('Ressource externe interdite dans la fiche personne.')
    return rendre_html(render_to_string('personnes/fiche_pdf.html', contexte),
        base_url=None, feuille_style=settings.BASE_DIR/'static/fiche-pdf.css', recuperer=refuser)
