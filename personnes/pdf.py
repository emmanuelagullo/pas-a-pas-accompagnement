"""Contenu de la fiche personne, indépendant des moteurs de rendu."""
from django.template.loader import render_to_string
from django.utils import timezone


def produire(personne, *, navigateur=False, coordonnees=None):
    from pas_communs.pdf import fiche_texte, rendre_html
    from django.conf import settings
    contexte = {'personne': personne, 'edite_le': timezone.localtime(), 'coordonnees': coordonnees}
    if navigateur:
        lignes = [
            'Données fictives uniquement',
            'Nom d’usage ou identifiant provisoire : '+personne.designation,
            'Prénom : '+(personne.prenom or 'Non renseigné'),
            'Naissance : '+personne.naissance_affichee,
            'Identifiant de la fiche : '+str(personne.pk),
            'Fiche créée le : '+timezone.localtime(personne.cree_le).strftime('%d/%m/%Y à %H:%M'),
            'Éditée le : '+contexte['edite_le'].strftime('%d/%m/%Y à %H:%M'),
        ]
        if coordonnees:
            lignes += ['Coordonnées déclarées depuis le '+coordonnees.debut.strftime('%d/%m/%Y'),
                'Adresse : '+(coordonnees.adresse or 'Non renseignée'),
                'Téléphone : '+(coordonnees.telephone or 'Non renseigné'),
                'Courriel : '+(coordonnees.courriel or 'Non renseigné'),
                'Fax : '+(coordonnees.fax or 'Non renseigné'), 'Source : '+coordonnees.source]
        return fiche_texte('Pas à Pas — Fiche personne', lignes)
    def refuser(url):
        # Aucun réseau, fichier ou média autorisé dans cette fiche sans images.
        raise ValueError('Ressource externe interdite dans la fiche personne.')
    return rendre_html(render_to_string('personnes/fiche_pdf.html', contexte),
        base_url=None, feuille_style=settings.BASE_DIR/'static/fiche-pdf.css', recuperer=refuser)
