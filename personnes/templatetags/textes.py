from django import template
from django.utils.html import format_html
from personnes.textes_riches import rendre

register = template.Library()


@register.filter
def texte_riche(objet, champ='texte'):
    lire = objet.get if isinstance(objet, dict) else lambda nom, defaut=None: getattr(objet, nom, defaut)
    texte = lire(champ, '')
    document = lire(champ + '_document')
    if not texte:
        document = None
        texte = 'Commentaire effacé.' if type(objet).__name__ == 'CommentaireDossier' else 'Non renseigné'
    return format_html('<div class="texte-narratif">{}</div>', rendre(texte, document))
