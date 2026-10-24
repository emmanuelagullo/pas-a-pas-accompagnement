"""Réutilisation des moteurs PDF existants pour les relevés textuels métier."""
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string


def produire(request,titre,lignes,nom):
    from pas_communs.pdf import fiche_texte,rendre_html
    try:
        if getattr(settings,'MODE_PWA',False):contenu=fiche_texte(titre,lignes)
        else:
            def refuser(url):raise ValueError('Aucune ressource externe autorisée.')
            contenu=rendre_html(render_to_string('aides/pdf.html',{'titre':titre,'lignes':lignes}),base_url=None,feuille_style=settings.BASE_DIR/'static/fiche-pdf.css',recuperer=refuser)
    except ValueError:return HttpResponse('Le document ne peut pas être généré avec les caractères présents.',status=422)
    r=HttpResponse(contenu,content_type='application/pdf');r['Content-Disposition']='attachment; filename="'+nom+'"';r['Cache-Control']='private, no-store';r['X-Content-Type-Options']='nosniff';return r
