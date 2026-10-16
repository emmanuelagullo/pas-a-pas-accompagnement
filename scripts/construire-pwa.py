#!/usr/bin/env python3
"""Assembler la PWA CHRS fictive ; aucune base ni donnée du développeur."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urldefrag,urlsplit
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
from pas_communs.construction_pwa import PYODIDE,BASE,telecharger,verifier_runtime
from pas_communs.navigateur import copier_ressources

ROOT=Path(__file__).resolve().parent.parent


def construire(sortie,runtime_cache=None,wheels_cache=None):
    sortie=Path(sortie).resolve()
    if sortie==ROOT or ROOT.is_relative_to(sortie) or sortie==Path(sortie.anchor):
        raise ValueError("Choisir un dossier de sortie distinct")
    # Ne pas conserver de ressources obsolètes dans un nouveau manifeste.
    if sortie.exists():
        if any(sortie.iterdir()):
            raise ValueError("La sortie doit être vide ; placer les caches en dehors du bundle.")
    sortie.mkdir(parents=True,exist_ok=True)
    runtime=sortie/"runtime";runtime.mkdir()
    cache=Path(runtime_cache).resolve() if runtime_cache else runtime
    cache.mkdir(parents=True,exist_ok=True)
    def obtenir(nom,empreinte=None):
        source=cache/nom;telecharger(BASE+nom,source,empreinte)
        if source!=runtime/nom:shutil.copyfile(source,runtime/nom)
    obtenir("pyodide-lock.json")
    lock=json.loads((runtime/"pyodide-lock.json").read_text());verifier_runtime(lock)
    choisis=set()
    def choisir(nom):
        if nom in choisis:return
        choisis.add(nom)
        for dep in lock["packages"][nom]["depends"]:choisir(dep)
    for nom in ["micropip","pycryptodome"]:choisir(nom)
    noms={n:None for n in ["pyodide.mjs","pyodide.asm.mjs","pyodide.asm.wasm","python_stdlib.zip"]}
    noms.update({lock["packages"][n]["file_name"]:lock["packages"][n]["sha256"] for n in choisis})
    with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lambda v:obtenir(*v),noms.items()))
    wheels=sortie/"wheels";wheels.mkdir()
    ligne=next(l for l in (ROOT/"requirements-communs.txt").read_text().splitlines() if l.startswith("pas-communs @ "))
    url,fragment=urldefrag(ligne.split(" @ ",1)[1]);nom=Path(urlsplit(url).path).name
    if not fragment.startswith("sha256=") or len(fragment[7:])!=64:raise ValueError("Empreinte du socle absente")
    if wheels_cache:
        source=Path(wheels_cache)/nom
        if hashlib.sha256(source.read_bytes()).hexdigest()!=fragment[7:]:raise ValueError("Wheel altéré")
        shutil.copyfile(source,wheels/nom)
    else:telecharger(url,wheels/nom,fragment[7:])
    with tempfile.TemporaryDirectory() as temp:
        exigences=Path(temp)/"pwa.txt"
        exigences.write_text("\n".join(l for l in (ROOT/"requirements.lock").read_text().splitlines() if not l.startswith("-r ")))
        subprocess.run([sys.executable,"-m","pip","download","--only-binary=:all:","--no-deps","--dest",str(wheels),"-r",str(exigences),
            *(["--no-index","--find-links",str(Path(wheels_cache).resolve())] if wheels_cache else [])],check=True)
    with ZipFile(sortie/"application.zip","w",ZIP_DEFLATED) as archive:
        for dossier in ["pas_a_pas_accompagnement","identites","personnes","templates","pwa"]:
            for path in sorted((ROOT/dossier).rglob("*")):
                if not path.is_file() or any(part in {"__pycache__", "node_modules"} for part in path.parts) or path.name.startswith("tests") or path.suffix not in {".py",".html"}:continue
                if dossier == "pwa" and (path.parent != ROOT/"pwa" or path.suffix != ".py"):continue
                info=ZipInfo(path.relative_to(ROOT).as_posix(),(2026,1,1,0,0,0));info.compress_type=ZIP_DEFLATED
                archive.writestr(info,path.read_bytes())
    shutil.copytree(ROOT/"static",sortie/"static")
    for nom in ["index.html","shell.js","worker.js","sw.js","manifest.webmanifest","icon.svg","icon-192.png","icon-512.png"]:
        shutil.copyfile(ROOT/"pwa"/nom,sortie/nom)
    copier_ressources(sortie/"socle")
    h=hashlib.sha256()
    for p in sorted(sortie.rglob("*")):
        if p.is_file():h.update(p.relative_to(sortie).as_posix().encode());h.update(p.read_bytes())
    version="chrs.pwa."+h.hexdigest()[:16]
    p=sortie/"sw.js";p.write_text(p.read_text().replace("__BUILD__",version))
    assets=[{"url":"/"+p.relative_to(sortie).as_posix(),"sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(sortie.rglob("*")) if p.is_file()]
    (sortie/"config.json").write_text(json.dumps({"application":"pas-a-pas-accompagnement","version":version,"pyodide":PYODIDE,
        "wheels":[p.name for p in sorted(wheels.glob("*.whl"))],"assets":assets},indent=2)+"\n")
    print("PWA fictive construite :",sortie,version)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sortie",type=Path,default=ROOT/"dist/pwa")
    p.add_argument("--runtime",type=Path)
    p.add_argument("--wheels",type=Path)
    a=p.parse_args();construire(a.sortie,a.runtime,a.wheels)
