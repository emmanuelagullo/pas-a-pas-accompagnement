#!/usr/bin/env python3
"""Vérifier les liens internes du site Hugo construit, sans requête réseau."""
import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, unquote


class Liens(HTMLParser):
    def __init__(self):
        super().__init__();self.urls=[];self.fr=False;self.titre=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='html':self.fr=attrs.get('lang')=='fr'
        if tag=='title':self.titre=True
        for key in ['href','src']:
            if key in attrs:self.urls.append(attrs[key])


def verifier(sortie,base):
    sortie=sortie.resolve();origin=urlsplit(base)
    if origin.scheme!='https' or not origin.netloc or not base.endswith('/'):
        raise ValueError('URL de base HTTPS terminée par / requise.')
    for nom in ['index.html','essayer/index.html','premiers-pas/index.html','le-projet/index.html','css/site.css']:
        if not (sortie/nom).is_file():raise ValueError('Page ou ressource absente : '+nom)
    pages=list(sortie.rglob('*.html'))
    for page in pages:
        relatif=page.relative_to(sortie).as_posix()
        adresse=urljoin(base,relatif.removesuffix('index.html'))
        parser=Liens();parser.feed(page.read_text(encoding='utf-8'))
        if not parser.fr or not parser.titre:raise ValueError('Titre/langue manquant : '+relatif)
        for lien in parser.urls:
            url=urlsplit(urljoin(adresse,lien))
            if url.scheme not in {'http','https'} or url.netloc!=origin.netloc or not url.path.startswith(origin.path):continue
            chemin=unquote(url.path[len(origin.path):])
            cible=sortie/chemin
            if url.path.endswith('/'):cible=cible/'index.html'
            if not cible.resolve().is_relative_to(sortie) or not cible.is_file():
                raise ValueError('Lien interne absent : '+relatif+' → '+lien)
    print(f'Site public : {len(pages)} pages HTML et liens internes vérifiés.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sortie',type=Path,default=Path('site/public'))
    p.add_argument('--base-url',required=True)
    a=p.parse_args()
    try:verifier(a.sortie,a.base_url)
    except ValueError as exc:p.exit(1,str(exc)+'\n')
