#!/usr/bin/env python3
"""Vérifier la version réellement embarquée, sans exécuter un binaire étranger."""
from pathlib import Path, PurePosixPath
import tarfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parent.parent
from publication import identity
attendu = (identity()['application_version']+'\n').encode('utf-8')
archives = [ROOT/'dist'/name for name in ['PasAPasAccompagnement-windows.zip', 'PasAPasAccompagnement-linux.tar.gz'] if (ROOT/'dist'/name).is_file()]
if not archives:
    raise SystemExit('Aucune archive de programme.')
for archive in archives:
    if archive.suffix == '.zip':
        with ZipFile(archive) as z:
            noms = [n for n in z.namelist() if PurePosixPath(n).name == 'version-application.txt']
            assert len(noms) == 1 and z.read(noms[0]) == attendu
    else:
        with tarfile.open(archive) as z:
            noms = [m for m in z.getmembers() if PurePosixPath(m.name).name == 'version-application.txt' and m.isfile()]
            assert len(noms) == 1
            with z.extractfile(noms[0]) as f:
                assert f.read() == attendu
print('Version embarquée des archives : OK')
