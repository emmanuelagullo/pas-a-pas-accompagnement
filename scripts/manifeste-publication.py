#!/usr/bin/env python3
"""Décrire/vérifier un candidat CHRS fictif ; aucun upload ni release."""
import argparse
import json
from pathlib import Path
import subprocess
import shutil
from pas_communs.publication import identite, manifeste, verifier, verifier_bundle

ROOT=Path(__file__).resolve().parent.parent
FORMAT='pas-a-pas-accompagnement-publication'
p=argparse.ArgumentParser(description=__doc__)
g=p.add_mutually_exclusive_group(required=True)
g.add_argument('--destination',type=Path);g.add_argument('--verifier',type=Path)
p.add_argument('--mode',choices=['programme','navigateur'])
p.add_argument('--target');p.add_argument('--bundle',type=Path)
p.add_argument('files',nargs='*',type=Path)
a=p.parse_args()
try:
    if a.verifier:
        record=json.loads(a.verifier.read_text())
        verifier(record,a.verifier.parent,format=FORMAT,mode=a.mode,target=a.target)
        print('Candidat CHRS vérifié. Aucune publication.')
    else:
        if not a.mode or not a.target:p.error('Définir --mode et --target.')
        fichiers=a.files
        if a.mode=='navigateur':
            if not a.bundle:p.error('Définir --bundle pour le navigateur.')
            verifier_bundle(a.bundle,version=r'chrs\.pwa\.[a-f0-9]{16}',
                requis={'index.html','worker.js','sw.js','application.zip'},application='pas-a-pas-accompagnement')
            if a.destination.parent.resolve().is_relative_to(a.bundle.resolve()):
                p.error('Placer le manifeste hors du bundle.')
            archive=a.destination.parent/'PasAPasAccompagnement-pwa.zip'
            if archive.exists():p.error('Archive de candidat déjà présente ; choisir une sortie neuve.')
            archive=Path(shutil.make_archive(str(archive.with_suffix('')),'zip',root_dir=a.bundle))
            fichiers=[archive]
        record=manifeste(FORMAT,identite(commit_local=lambda:subprocess.check_output(
            ['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()),a.mode,a.target,fichiers)
        a.destination.write_text(json.dumps(record,indent=2)+'\n')
        print('Manifeste CHRS préparé. Aucune publication.')
except (ValueError,OSError,subprocess.SubprocessError) as erreur:p.exit(1,str(erreur)+'\n')
