"""Adaptateur produit des versions et notes ; primitives d'intégrité du socle."""
import os
from pathlib import Path
import re
import subprocess
import sys
from pas_communs.publication import identite, TAG

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))


def identity():
    result=identite(commit_local=lambda:subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    if not (os.environ.get('CI_COMMIT_SHA') or os.environ.get('GITHUB_SHA')):
        from pas_a_pas_accompagnement.version import version_application
        version=version_application()
        if TAG.fullmatch(version):
            result.update(tag=version,application_version=version)
    return result


def release_notes(tag=None,text=None):
    text=(ROOT/'CHANGELOG.md').read_text(encoding='utf-8') if text is None else text
    sections=list(re.finditer(r'^## (.+)$',text,re.M))
    matches=[m for m in sections if (re.match(re.escape(tag)+r'(?:\s|$)',m[1]) if tag else m[1] in {'À venir','Unreleased'})]
    if len(matches)!=1:
        raise ValueError('Une rubrique unique du CHANGELOG.md est requise : '+(tag or 'À venir'))
    section=matches[0]
    fin=next((m.start() for m in sections if m.start()>section.start()),len(text))
    notes=text[section.end():fin].strip()
    if not notes:
        if tag:raise ValueError('Notes de version vides.')
        notes='Aucune nouvelle modification depuis la dernière version numérotée.'
    return notes+'\n'
