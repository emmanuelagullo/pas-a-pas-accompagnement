// Vrais Django/SQLite dans deux runtimes WASM, sans navigateur ni données réelles.
import fs from 'node:fs';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';
const dossier=process.env.PWA_BUNDLE?pathToFileURL(path.resolve(process.env.PWA_BUNDLE)+path.sep):new URL('../dist/pwa/',import.meta.url),racine=fileURLToPath(dossier);
const config=JSON.parse(fs.readFileSync(new URL('config.json',dossier)));
const {loadPyodide}=await import(new URL('runtime/pyodide.mjs',dossier));
async function moteur(fichiers={}){
  const p=await loadPyodide({indexURL:racine+'runtime/'});await p.loadPackage(['micropip','pycryptodome','pillow']);
  for(const nom of config.wheels)p.FS.writeFile('/tmp/'+nom,fs.readFileSync(racine+'wheels/'+nom));
  await p.runPythonAsync(`import micropip\nawait micropip.install(${JSON.stringify(config.wheels.map(n=>'emfs:/tmp/'+n))})`);
  p.unpackArchive(new Uint8Array(fs.readFileSync(racine+'application.zip')),'zip',{extractDir:'/application'});
  p.runPython("import sys;sys.path.insert(0,'/application');from pwa import bridge as b");
  p.FS.mkdirTree('/data');for(const [nom,contenu] of Object.entries(fichiers))p.FS.writeFile('/data/'+nom,contenu);
  p.runPython("b.initialize('https://chrs-fictif.example','/chrs/')");
  p.runPython(`from django.conf import settings; assert settings.VERSION_APPLICATION == ${JSON.stringify(config.application_version)}`);
  return p;
}
const premier=await moteur();
premier.runPython(`
import json,urllib.parse

def requete(chemin,donnees=None):
    corps=urllib.parse.urlencode(donnees or {}).encode()
    entetes=[['Origin','https://chrs-fictif.example'],['Referer','https://chrs-fictif.example/chrs/app/']]
    if donnees is not None:entetes.append(['Content-Type','application/x-www-form-urlencoded'])
    meta=json.loads(b.handle(json.dumps({'url':'https://chrs-fictif.example/chrs/app/'+chemin,'method':'POST' if donnees is not None else 'GET','headers':entetes}),corps))
    return meta,b.response_bytes().decode()

meta,html=requete('installer/')
assert meta['status']==200 and 'Préparer mon espace' in html
assert 'Carnet de suivi des apprentissages' not in html
mot='Phrase fictive pour WASM-834!'
csrf=lambda:b.COOKIES['pas_accompagnement_csrftoken']
meta,_=requete('installer/',{'username':'fictif-wasm','password1':mot,'password2':mot,'csrfmiddlewaretoken':csrf()})
assert meta['status']==302,meta
meta,_=requete('personnes/creer/',{'designation':'Personne fictive WASM','csrfmiddlewaretoken':csrf()})
assert meta['status']==302,meta
meta,html=requete('personnes/')
assert meta['status']==200 and 'Personne fictive WASM' in html
from personnes.models import Personne
personne=Personne.objects.get()
meta=json.loads(b.handle(json.dumps({'url':f'https://chrs-fictif.example/chrs/app/personnes/{personne.pk}/fiche.pdf','method':'GET','headers':[]}),b''))
assert meta['status']==200,meta
assert dict(meta['headers'])['Content-Type']=='application/pdf'
assert b.response_bytes().startswith(b'%PDF-')
inventaire=json.loads(b.inventory())
assert set(inventaire['files'])=={'accompagnement.sqlite3','secret-key'}
`);
const fichiers={};
for(const nom of ['accompagnement.sqlite3','secret-key']){
  const f=premier.globals.get('b').file_bytes(nom);try{fichiers[nom]=f.toJs();}finally{f.destroy();}
}
const second=await moteur(fichiers);
second.runPython(`
import json,urllib.parse
from django.contrib.auth import get_user_model
from personnes.models import Personne
assert Personne.objects.filter(designation='Personne fictive WASM').count()==1
assert b.COOKIES=={}
meta=json.loads(b.handle(json.dumps({'url':'https://chrs-fictif.example/chrs/app/personnes/','method':'GET','headers':[]}),b''))
assert meta['status']==302
assert any(k=='Location' and v.startswith('/chrs/app/connexion/') for k,v in meta['headers'])
# Les données d’une version inconnue ne sont pas migrées ni remplacées par du vide.
from django.db import connection
with connection.cursor() as c:c.execute("INSERT INTO django_migrations(app,name,applied) VALUES ('identites','future_inconnue','2026-01-01')")
try:b.initialize('https://chrs-fictif.example','/chrs/')
except ValueError as erreur:assert 'plus récente' in str(erreur)
else:raise AssertionError('Migration inconnue acceptée')
`);
console.log('Pyodide CHRS : premier compte → personne → snapshot SQLite → nouveau moteur sans session → migration future refusée : OK');
