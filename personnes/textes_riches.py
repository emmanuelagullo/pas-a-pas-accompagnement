"""Petit format narratif v1 : aucune interprétation HTML ou Markdown des textes.

Cette primitive reste applicative tant qu'un second consommateur ne justifie
pas son extraction. Le document est la source ; le texte est sa projection.
"""
import json
from html import escape
from urllib.parse import urlsplit

from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html
from django.utils.safestring import mark_safe

MAX_OCTETS = 65536
MAX_NOEUDS = 2048
MAX_PROFONDEUR = 12


def adresse(valeur):
    if not isinstance(valeur, str) or len(valeur) > 2048 or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in valeur):
        raise ValidationError('Indiquez une adresse web complète, sans espace.')
    try:
        url = urlsplit(valeur)
        _ = url.port  # Vérifier aussi les ports invalides.
        valide = url.scheme in ('https', 'http') and url.hostname and not url.username and not url.password and '\\' not in valeur
    except ValueError:
        valide = False
    if not valide:
        raise ValidationError('Les liens doivent commencer par https:// ou http:// et désigner un site web.')
    return valeur


def valider(document):
    """Valider et reconstruire : pas d'attribut ou de nœud inconnu conservé."""
    try:
        if len(json.dumps(document, ensure_ascii=False, allow_nan=False).encode()) > MAX_OCTETS:
            raise ValueError
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise ValidationError('Le texte enrichi est trop volumineux ou invalide.') from exc
    if not isinstance(document, dict) or set(document) != {'version', 'doc'} or type(document['version']) is not int or document['version'] != 1:
        raise ValidationError('Ce format de texte enrichi n’est pas pris en charge.')
    compteur = 0

    def noeud(n, parent=None, profondeur=0):
        nonlocal compteur
        compteur += 1
        if compteur > MAX_NOEUDS or profondeur > MAX_PROFONDEUR or not isinstance(n, dict):
            raise ValidationError('Le texte enrichi est trop complexe.')
        typ = n.get('type')
        permis = {None: {'doc'}, 'doc': {'paragraph', 'bulletList', 'orderedList'},
                  'paragraph': {'text', 'hardBreak'}, 'bulletList': {'listItem'},
                  'orderedList': {'listItem'}, 'listItem': {'paragraph', 'bulletList', 'orderedList'}}
        if not isinstance(typ, str) or typ not in permis.get(parent, set()):
            raise ValidationError('Structure de texte non autorisée.')
        resultat = {'type': typ}
        cles = {'type'}
        if typ == 'text':
            cles |= {'text', 'marks'}
            texte = n.get('text')
            if not isinstance(texte, str) or not texte or any(ord(c) < 32 and c not in '\n\t' for c in texte):
                raise ValidationError('Texte invalide.')
            resultat['text'] = texte
            marques = n.get('marks', [])
            if not isinstance(marques, list) or len(marques) > 3:
                raise ValidationError('Mise en forme invalide.')
            vues = set()
            for m in marques:
                if not isinstance(m, dict) or not isinstance(m.get('type'), str):
                    raise ValidationError('Mise en forme invalide.')
                mt = m['type']
                if mt not in ('bold', 'italic', 'link') or mt in vues or set(m) != ({'type', 'attrs'} if mt == 'link' else {'type'}):
                    raise ValidationError('Mise en forme non autorisée.')
                vues.add(mt)
                if mt == 'link':
                    if not isinstance(m['attrs'], dict) or set(m['attrs']) != {'href'}:
                        raise ValidationError('Lien invalide.')
                    adresse(m['attrs']['href'])
            if marques:
                resultat['marks'] = sorted(marques, key=lambda m: m['type'])
        elif typ != 'hardBreak':
            cles.add('content')
            enfants = n.get('content', [])
            if not isinstance(enfants, list) or (typ != 'paragraph' and not enfants):
                raise ValidationError('Structure de texte vide ou invalide.')
            if typ == 'listItem' and enfants and (not isinstance(enfants[0], dict) or enfants[0].get('type') != 'paragraph'):
                raise ValidationError('Un élément de liste commence par un paragraphe.')
            resultat['content'] = [noeud(e, typ, profondeur + 1) for e in enfants]
        if typ == 'orderedList':
            cles.add('attrs')
            attrs = n.get('attrs', {'start': 1})
            if not isinstance(attrs, dict) or set(attrs) != {'start'} or type(attrs['start']) is not int or not 1 <= attrs['start'] <= 999999:
                raise ValidationError('Numérotation invalide.')
            resultat['attrs'] = attrs
        if set(n) - cles:
            raise ValidationError('Attribut de texte non autorisé.')
        return resultat

    return {'version': 1, 'doc': noeud(document['doc'])}


def texte_simple(document):
    def lire(n):
        if n['type'] == 'text':
            return n['text']
        if n['type'] == 'hardBreak':
            return '\n'
        separateur = '' if n['type'] == 'paragraph' else '\n'
        return separateur.join(lire(e) for e in n.get('content', []))
    return lire(document['doc']).strip()


class ValeurTexte(str):
    def __new__(cls, texte, document=None):
        obj = super().__new__(cls, texte)
        obj.document = document
        return obj


def preparer(valeur, max_length=None, required=False):
    doc = getattr(valeur, 'document', None)
    if doc is not None:
        doc = valider(doc)
        texte = texte_simple(doc)
    else:
        texte = str(valeur or '').strip()
    if required and not texte:
        raise ValidationError('Le texte est obligatoire.')
    if max_length and len(texte) > max_length:
        raise ValidationError(f'Le texte ne doit pas dépasser {max_length} caractères.')
    return ValeurTexte(texte, doc)


def lire_objet(objet, champ):
    return ValeurTexte(getattr(objet, champ), getattr(objet, champ + '_document', None))


def colonnes(champ, valeur, **options):
    valeur = preparer(valeur, **options)
    return {champ: str(valeur), champ + '_document': valeur.document}


def rendre(texte, document=None):
    if document is None:
        return mark_safe(escape(str(texte or '')).replace('\n', '<br>'))
    try:
        document = valider(document)
    except ValidationError:
        # Une archive altérée ne transforme jamais sa projection en HTML.
        return rendre(texte)

    def html(n):
        typ = n['type']
        if typ == 'text':
            contenu = escape(n['text'])
            for m in n.get('marks', []):
                if m['type'] == 'link':
                    contenu = '<a href="' + escape(m['attrs']['href'], quote=True) + '" target="_blank" rel="noopener noreferrer">' + contenu + '</a>'
                else:
                    balise = 'strong' if m['type'] == 'bold' else 'em'
                    contenu = f'<{balise}>{contenu}</{balise}>'
            return contenu
        if typ == 'hardBreak':
            return '<br>'
        contenu = ''.join(html(e) for e in n.get('content', []))
        if typ == 'doc':
            return contenu
        balise = {'paragraph': 'p', 'bulletList': 'ul', 'orderedList': 'ol', 'listItem': 'li'}[typ]
        attribut = f' start="{n["attrs"]["start"]}"' if typ == 'orderedList' else ''
        return f'<{balise}{attribut}>{contenu}</{balise}>'
    return mark_safe(html(document['doc']))


class WidgetTexte(forms.Textarea):
    """Textarea utilisable sans JS ; le document existant reste en lecture seule."""
    def value_from_datadict(self, data, files, name):
        return (data.get(name, ''), data.get(name + '_document', ''))

    def render(self, name, value, attrs=None, renderer=None):
        attrs = dict(attrs or {})
        if isinstance(value, tuple):
            texte, brut = value
        else:
            texte, brut = str(value or ''), json.dumps(getattr(value, 'document', None), ensure_ascii=False) if getattr(value, 'document', None) is not None else ''
        attrs.update({'data-texte-obligatoire': '1' if attrs.get('required') else '0', 'data-texte-riche': '1', 'lang': 'fr', 'spellcheck': 'true'})
        if brut:
            try:
                texte = texte_simple(valider(json.loads(brut)))
            except (ValidationError, ValueError, TypeError, RecursionError):
                pass
            attrs['readonly'] = True
        # maxlength s'applique au texte lisible côté Python, pas au JSON.
        textarea = super().render(name, texte, attrs, renderer)
        return format_html('{}<input type="hidden" name="{}" value="{}" data-document-riche><noscript><span class="helptext">Sans JavaScript, les textes enrichis sont consultables mais ne peuvent pas être modifiés.</span></noscript>', textarea, name + '_document', brut)


class ChampTexte(forms.Field):
    widget = WidgetTexte

    def __init__(self, *args, max_length=None, **kwargs):
        self.max_length = max_length
        super().__init__(*args, **kwargs)
        if max_length:
            self.widget.attrs['data-max-texte'] = max_length

    def clean(self, value):
        if isinstance(value, tuple):
            texte, brut = value
            doc = None
            if brut:
                try:
                    if len(brut.encode()) > MAX_OCTETS:
                        raise ValueError
                    doc = json.loads(brut)
                except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
                    raise ValidationError('Le texte enrichi transmis est invalide.') from exc
            value = ValeurTexte(texte, doc)
        valeur = preparer(value, self.max_length, self.required)
        self.run_validators(valeur)
        return valeur
