#!/usr/bin/env python3
"""Publier l'artefact exact du prototype réussi, sans reconstruction ni secret."""
# Adapté du préparateur Petits Pas (AGPL-3.0-or-later).
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

from pas_communs.publication import TAG, verifier
FORMAT='pas-a-pas-accompagnement-publication'

SOURCE = "pas-a-pas-accompagnement/pas-a-pas-accompagnement"
MAX_BYTES = 256 * 1024**2
MAX_FILES = 5000


def require_pages_url(value):
    url = urllib.parse.urlsplit(value)
    if (url.scheme != "https" or not url.hostname or url.username or url.password
            or not re.fullmatch(r"/(?:[a-zA-Z0-9_-]+/)*", url.path or "/") or url.query or url.fragment):
        raise ValueError("La PWA exige une URL HTTPS avec un chemin terminé par /, sans paramètres.")


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def validate_bundle(root):
    from pas_communs.publication import verifier_bundle
    return verifier_bundle(root, version=r"chrs\.pwa\.[a-f0-9]{16}",
        requis={"index.html", "worker.js", "sw.js", "application.zip"}, application="pas-a-pas-accompagnement")


def json_request(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response), response.headers


def select_job(api, project, pipeline_id, commit, ref='main', tag=None):
    info, _ = json_request(api + '/projects/' + urllib.parse.quote(SOURCE, safe=''))
    if str(info['id']) != project or info['path_with_namespace'] != SOURCE:
        raise ValueError('Projet source inattendu.')
    base = api + '/projects/' + project
    pipeline, _ = json_request(base + '/pipelines/' + pipeline_id)
    if pipeline['sha'] != commit or pipeline['ref'] != ref or pipeline.get('source') not in {'push', 'web'}:
        raise ValueError('Pipeline source inattendu.')
    if tag:
        if not TAG.fullmatch(tag) or ref != tag:
            raise ValueError('Tag invalide.')
        for url, key in [
            (base + '/repository/tags/' + urllib.parse.quote(tag, safe=''), 'commit'),
            ('https://api.github.com/repos/emmanuelagullo/pas-a-pas-accompagnement/commits/' + urllib.parse.quote(tag,safe=''), 'sha')]:
            record, _ = json_request(url)
            actual = record[key]['id'] if key == 'commit' else record[key]
            if actual != commit:
                raise ValueError('Tag absent ou divergent entre les forges.')
    elif ref != info['default_branch']:
        raise ValueError('Branche inattendue.')
    page, jobs = '1', []
    while page:
        batch, headers = json_request(base + '/pipelines/' + pipeline_id + '/jobs?include_retried=false&per_page=100&page=' + page)
        jobs.extend(batch)
        page = headers.get('X-Next-Page', '')
    required = ['pwa-prototype', 'deploiement-ephemere', 'deploiement-persistant-local']
    for name in required:
        selected = [j for j in jobs if j['name'] == name]
        if len(selected) != 1 or selected[0]['status'] != 'success':
            raise ValueError('Contrôle absent, ambigu ou en échec : ' + name)
    tests = [j for j in jobs if j['name'].startswith('test:') or j['name'] == 'test']
    if not tests or any(j['status'] != 'success' for j in tests):
        raise ValueError('Matrice Django non réussie.')
    checked = [j for j in jobs if j['name'] in required or j in tests]
    if any(j['commit']['id'] != commit or str(j['pipeline']['id']) != pipeline_id for j in checked):
        raise ValueError('Contrôle issu d’un autre commit ou pipeline.')
    job = next(j for j in jobs if j['name'] == 'pwa-prototype')
    return job, base + '/jobs/' + str(job['id']) + '/artifacts'


def extract(archive, parent, *, prefix=''):
    with ZipFile(archive) as zipped:
        entries = zipped.infolist()
        if len(entries) > MAX_FILES or sum(e.file_size for e in entries) > MAX_BYTES or len({e.filename for e in entries}) != len(entries):
            raise ValueError('Archive trop volumineuse ou entrées répétées.')
        for entry in entries:
            name = entry.filename
            parts = PurePosixPath(name).parts
            if (name.startswith('/') or '\\' in name or '..' in parts
                    or stat.S_ISLNK(entry.external_attr >> 16)):
                raise ValueError('Chemin invalide.')
            if entry.is_dir():
                continue
            if prefix:
                if not name.startswith(prefix):
                    raise ValueError('Fichier inattendu dans le candidat : ' + name)
                parts = PurePosixPath(name[len(prefix):]).parts
            if not parts:
                raise ValueError('Chemin vide.')
            dest = parent.joinpath(*parts)
            dest.parent.mkdir(parents=True,exist_ok=True)
            with zipped.open(entry) as src, dest.open('xb') as out:
                shutil.copyfileobj(src,out)


def download(url, path):
    total = 0
    with urllib.request.urlopen(url, timeout=60) as source, path.open("wb") as destination:
        while block := source.read(1024**2):
            total += len(block)
            if total > MAX_BYTES:
                raise ValueError("Artefact téléchargé trop volumineux.")
            destination.write(block)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--pages-url',required=True)
    args = parser.parse_args()
    require_pages_url(args.pages_url.rstrip('/') + '/')
    if args.destination.exists():
        raise ValueError('Destination déjà présente.')
    env = os.environ
    if env.get('CI_PIPELINE_SOURCE') != 'pipeline' or env.get('PWA_SOURCE_PROJECT') != SOURCE:
        raise ValueError('Déclenchement interprojets attendu.')
    project, pipeline, commit = env['PWA_SOURCE_PROJECT_ID'],env['PWA_SOURCE_PIPELINE_ID'],env['PWA_SOURCE_SHA']
    ref, tag = env['PWA_SOURCE_REF'],env.get('PWA_SOURCE_TAG') or None
    if not project.isdecimal() or not pipeline.isdecimal() or not re.fullmatch(r'[a-f0-9]{40}',commit):
        raise ValueError('Identité source invalide.')
    job, url = select_job(env['CI_API_V4_URL'],project,pipeline,commit,ref,tag)
    with tempfile.TemporaryDirectory(prefix='pwa-promotion-') as t:
        temp=Path(t)
        archive=temp/'artifact.zip'
        download(url,archive)
        candidate=temp/'candidate';candidate.mkdir()
        extract(archive,candidate,prefix='dist/')
        if {p.name for p in candidate.iterdir()} != {'PasAPasAccompagnement-pwa.zip','publication-pwa.json','notes-version.md'}:
            raise ValueError('Inventaire du candidat inattendu.')
        record=json.loads((candidate/'publication-pwa.json').read_text())
        expected=verifier(record,candidate,format=FORMAT,commit=commit,tag=tag,mode='navigateur',target='chromium-statique')
        if expected != {'PasAPasAccompagnement-pwa.zip','notes-version.md'} or record.get('tag') != tag:
            raise ValueError('Identité ou fichiers inattendus.')
        if record['ci']['provider'] != 'gitlab' or str(record['ci']['run']) != pipeline or str(record['ci']['job']) != str(job['id']):
            raise ValueError('Candidat issu d’un autre job.')
        bundle=temp/'bundle';bundle.mkdir()
        extract(candidate/'PasAPasAccompagnement-pwa.zip',bundle)
        config=validate_bundle(bundle)
        if config.get('commit') != commit or config.get('tag') != tag or config.get('application_version') != record.get('application_version'):
            raise ValueError('Identité embarquée différente du candidat.')
        # Recontrôler la sélection après téléchargement, avant écriture de public.
        current,_=select_job(env['CI_API_V4_URL'],project,pipeline,commit,ref,tag)
        if current['id'] != job['id']:
            raise ValueError('Job remplacé pendant la promotion.')
        shutil.copytree(bundle,args.destination)
        shutil.copyfile(candidate/'notes-version.md',Path('notes-version.md'))
        Path('publication-pwa.json').write_text(json.dumps({**record,'pages_url':args.pages_url,'source_job':job['id']},indent=2)+'\n')
    print('Bundle normal validé, prêt pour GitLab Pages. Aucun code reconstruit.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError,OSError,KeyError,BadZipFile) as exc:
        raise SystemExit('Publication refusée : '+str(exc))
