"""Réédition du contenu conservé ; statut d'annulation ajouté sans le réécrire."""
from django.conf import settings
from django.template.loader import render_to_string
from . import financements as s


def produire(doc,*,navigateur=False):
    from pas_communs.pdf import fiche_texte,rendre_html
    from django.core.exceptions import ValidationError
    if s.empreinte(doc.contenu)!=doc.empreinte:raise ValidationError('Contenu conservé non conforme à son empreinte.')
    titre=doc.numero+' — '+doc.contenu['titre']
    lignes=['Date d’émission : '+str(doc.date),*doc.contenu['lignes'],'Empreinte : '+doc.empreinte]
    if hasattr(doc,'annulation'):
        a=doc.annulation;lignes.insert(0,'DOCUMENT ANNULÉ — '+a.motif+' · '+str(a.auteur)+' · '+str(a.enregistre_le))
    if navigateur:return fiche_texte(titre,lignes)
    def refuser(url):raise ValueError('Aucune ressource externe autorisée.')
    return rendre_html(render_to_string('aides/pdf.html',{'titre':titre,'lignes':lignes}),base_url=None,feuille_style=settings.BASE_DIR/'static/fiche-pdf.css',recuperer=refuser)
