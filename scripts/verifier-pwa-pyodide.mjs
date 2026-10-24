// Vrais Django/SQLite dans deux runtimes WASM, sans navigateur ni données réelles.
import fs from 'node:fs';
import {fileURLToPath,pathToFileURL} from 'node:url';
import path from 'node:path';
const dossier=process.env.PWA_BUNDLE?pathToFileURL(path.resolve(process.env.PWA_BUNDLE)+path.sep):new URL('../dist/pwa/',import.meta.url),racine=fileURLToPath(dossier);
const config=JSON.parse(fs.readFileSync(new URL('config.json',dossier)));
const {loadPyodide}=await import(new URL('runtime/pyodide.mjs',dossier));
async function moteur(fichiers={},essai=false){
  const p=await loadPyodide({indexURL:racine+'runtime/'});
  const attendu=JSON.parse(fs.readFileSync(new URL('runtime/pyodide-lock.json',dossier),'utf8')).info.python;
  const effectif=p.runPython("import sys; sys.version.split()[0]");
  if(effectif!==attendu)throw new Error(`Python embarqué ${effectif}, attendu ${attendu}`);
  console.log(`Python embarqué exécuté : ${effectif}`);
  await p.loadPackage(['micropip','pycryptodome','pillow']);
  for(const nom of config.wheels)p.FS.writeFile('/tmp/'+nom,fs.readFileSync(racine+'wheels/'+nom));
  await p.runPythonAsync(`import micropip\nawait micropip.install(${JSON.stringify(config.wheels.map(n=>'emfs:/tmp/'+n))})`);
  p.unpackArchive(new Uint8Array(fs.readFileSync(racine+'application.zip')),'zip',{extractDir:'/application'});
  p.runPython("import sys;sys.path.insert(0,'/application');from pwa import bridge as b");
  p.FS.mkdirTree('/data');for(const [nom,contenu] of Object.entries(fichiers)){p.FS.mkdirTree('/data/'+path.posix.dirname(nom));p.FS.writeFile('/data/'+nom,contenu);}
  p.runPython(`b.initialize('https://chrs-fictif.example','/chrs/',essai=${essai?'True':'False'},nouveau=${essai&&Object.keys(fichiers).length===0?'True':'False'})`);
  p.runPython(`from django.conf import settings; assert settings.VERSION_APPLICATION == ${JSON.stringify(config.application_version)}`);
  return p;
}
const premier=await moteur();
premier.runPython(`
from personnes import textes_riches as textes_recette
from django.core.exceptions import ValidationError as ErreurTexteRecette
texte_doc_recette = {'version': 1, 'doc': {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': '<fictif>', 'marks': [{'type': 'bold'}]}]}]}}
texte_valeur_recette = textes_recette.preparer(textes_recette.ValeurTexte('', texte_doc_recette), max_length=100)
assert str(texte_valeur_recette) == '<fictif>'
assert '<strong>&lt;fictif&gt;</strong>' in textes_recette.rendre('', texte_valeur_recette.document)
assert '**ancien**' in textes_recette.rendre('**ancien**')
try:
    textes_recette.valider({'version': 1, 'doc': {'type': 'html'}})
except ErreurTexteRecette:
    pass
else:
    raise AssertionError('Format inconnu accepté')
`);
console.log('Texte enrichi v1 : validation Python, projection, échappement et texte historique dans WASM : OK');

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
// Jeu technique minimal CHRS1–4 et média opaque : aucun nouveau métier.
const sonde=fs.readFileSync(new URL('./jeu-technique-copies.py',import.meta.url),'utf8');
premier.runPython(sonde+`
from django.contrib.auth import get_user_model
preparer(get_user_model().objects.get())
(DATA := b.DATA / 'media' / 'sonde').mkdir(parents=True)
(DATA / 'fictif.txt').write_bytes(b'media fictif technique')
signature_attendue=signature()
`);
const signature=premier.runPython('signature_attendue');
const inventaire=JSON.parse(premier.runPython('b.inventory()'));
const fichiers={};
for(const nom of Object.keys(inventaire.files)){
  const f=premier.globals.get('b').file_bytes(nom);try{fichiers[nom]=f.toJs();}finally{f.destroy();}
}
const second=await moteur(fichiers);
second.runPython(sonde);
if(second.runPython('signature()')!==signature)throw new Error('Identités ou relations CHRS1–4 altérées');
second.runPython("assert (b.DATA/'media/sonde/fictif.txt').read_bytes()==b'media fictif technique'");
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

// PWA → CLI native → PWA, avec les mêmes octets de média et identités.
const {execFileSync}=await import('node:child_process');
const os=await import('node:os');
const temporaire=fs.mkdtempSync(path.join(os.tmpdir(),'chrs-echanges-'));
try{
 const zip=path.join(temporaire,'pwa.zip');
 const valeur=premier.runPython('b.export_zip()');
 try{fs.writeFileSync(zip,valeur.toJs());}finally{valeur.destroy();}
 const native=path.join(temporaire,'native');
 const env={...process.env,ACCOMPAGNEMENT_DONNEES:path.join(temporaire,'operateur')};
 const python=process.env.PWA_PYTHON||'python3';
 const manage=fileURLToPath(new URL('../manage.py',import.meta.url));
 execFileSync(python,[manage,'restaurer_copie',zip,native],{env});
 execFileSync(python,[manage,'migrate','--noinput'],{env:{...env,ACCOMPAGNEMENT_DONNEES:native}});
 execFileSync(python,[manage,'sauvegarder_paquet',path.join(temporaire,'native.zip')],{env:{...env,ACCOMPAGNEMENT_DONNEES:native}});
 const retour=await moteur();
 // moteur() initialise DATA : la préparation exige volontairement un Worker neuf.
 retour.runPython("from django.db import connections; connections.close_all(); import shutil; shutil.rmtree(b.DATA)");
 retour.globals.set('copie_native',new Uint8Array(fs.readFileSync(path.join(temporaire,'native.zip'))));
 retour.runPython("b.prepare_zip(copie_native,'https://chrs-fictif.example','/chrs/')");
 retour.runPython(sonde);
 if(Buffer.from(retour.FS.readFile('/data/secret-key')).toString()!==Buffer.from(fichiers['secret-key']).toString())throw new Error('Clé locale modifiée');
 if(retour.runPython('signature()')!==signature)throw new Error('Aller-retour natif : relations altérées');
 retour.runPython("assert (b.DATA/'media/sonde/fictif.txt').read_bytes()==b'media fictif technique'; from django.contrib.sessions.models import Session; assert not Session.objects.exists()");
 // Jeu métier réel : premier démarrage facultatif dans un autre espace WASM.
 const demo=await moteur({},true);
 demo.runPython(`
from django.test import Client
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.contrib.sessions.models import Session
from io import StringIO
from personnes.models import Personne,Sejour,AccordRepas,Menage
c=Client(enforce_csrf_checks=True,HTTP_HOST='chrs-fictif.example',secure=True)
assert c.get('/installer/',secure=True).status_code==404
assert c.login(username='nadia',password='Demonstration-fictive-2026!')
assert Personne.objects.count()==36 and Menage.objects.count()==18
assert get_user_model().objects.count()==4
assert not get_user_model().objects.filter(is_superuser=True).exists()
assert Sejour.objects.filter(fin__isnull=True).count()==1
assert c.get('/decouverte/',secure=True).status_code==200
assert c.get('/mon-compte/mot-de-passe/',secure=True).status_code==403
sortie=StringIO();call_command('dumpdata','personnes','identites.Utilisateur',stdout=sortie)
signature_demo=sortie.getvalue()
`);
 const attenduDemo=demo.runPython('signature_demo');
 const demoFichiers={};
 for(const nom of Object.keys(JSON.parse(demo.runPython('b.inventory()')).files)){
  const valeur=demo.globals.get('b').file_bytes(nom);try{demoFichiers[nom]=valeur.toJs();}finally{valeur.destroy();}
 }
 const demoReouverte=await moteur(demoFichiers,true);
 demoReouverte.runPython("from io import StringIO; from django.core.management import call_command; sortie=StringIO(); call_command('dumpdata','personnes','identites.Utilisateur',stdout=sortie)");
 if(JSON.stringify(JSON.parse(demoReouverte.runPython('sortie.getvalue()')))!==JSON.stringify(JSON.parse(attenduDemo)))throw new Error('Jeu recréé à la réouverture');
 if(premier.runPython('signature()')!==signature)throw new Error('Espace habituel altéré par l’essai');
 const demoZip=demo.runPython('b.export_zip()');
 try{fs.writeFileSync(path.join(temporaire,'demo.zip'),demoZip.toJs());}finally{demoZip.destroy();}
 const demoNative=path.join(temporaire,'demo-native');
 execFileSync(python,[manage,'restaurer_copie',path.join(temporaire,'demo.zip'),demoNative],{env});
 const signatureNative=execFileSync(python,[manage,'dumpdata','personnes','identites.Utilisateur'],
   {env:{...env,ACCOMPAGNEMENT_DONNEES:demoNative},encoding:'utf8'});
 if(JSON.stringify(JSON.parse(attenduDemo))!==JSON.stringify(JSON.parse(signatureNative)))throw new Error('Jeu métier PWA → natif altéré');
 console.log('Les Passerelles : essai WASM distinct, réouverture conservée, droits et copie native : OK');
 // Ancien schéma pré-CHRS1 et pré-TOTP, réellement créé par ses migrations.
 const ancien=path.join(temporaire,'ancien');
 const codeAncien=`import os,django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','pas_a_pas_accompagnement.settings')
django.setup()
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
executor=MigrationExecutor(connection)
cibles=[('personnes','0001_initial'),('identites','0001_initial')]
executor.migrate(cibles)
apps=executor.loader.project_state(cibles).apps
u=apps.get_model('identites','Utilisateur').objects.create(username='ancien-fictif',password='!mot-fictif-inutilisable')
apps.get_model('personnes','Personne').objects.create(id='11111111-2222-4333-8444-555555555555',designation='Ancienne personne fictive',cree_par_id=u.pk)
from pas_communs.paquets import creer_sauvegarde,ProfilPaquet
from pathlib import Path
p=Path(os.environ['ACCOMPAGNEMENT_DONNEES'])
(p/'media').mkdir();(p/'media'/'ancien.txt').write_bytes(b'ancien media fictif')
creer_sauvegarde(p,p.parent/'ancien.zip',profil=ProfilPaquet('pas-a-pas-accompagnement','pas-a-pas-accompagnement-paquet','accompagnement.sqlite3'))
`;
 execFileSync(python,['-c',codeAncien],{cwd:path.dirname(manage),env:{...env,ACCOMPAGNEMENT_DONNEES:ancien}});
 // Nouveau runtime sans état courant : seule la préparation est migrée.
 const migration=await moteur();
 migration.runPython("from django.db import connections; connections.close_all(); import shutil; shutil.rmtree(b.DATA)");
 migration.globals.set('ancienne_copie',new Uint8Array(fs.readFileSync(path.join(temporaire,'ancien.zip'))));
 migration.runPython("b.prepare_zip(ancienne_copie,'https://chrs-fictif.example','/chrs/')");
 migration.runPython(`from personnes.models import Personne,Accompagnement
from django.contrib.auth import get_user_model
assert str(Personne.objects.get().pk)=='11111111-2222-4333-8444-555555555555'
assert Personne.objects.get().cree_par_id==get_user_model().objects.get(username='ancien-fictif').pk
assert not Accompagnement.objects.exists()
assert (b.DATA/'media/ancien.txt').read_bytes()==b'ancien media fictif'
from django.db.migrations.executor import MigrationExecutor
from django.db import connection
assert not MigrationExecutor(connection).migration_plan(MigrationExecutor(connection).loader.graph.leaf_nodes())
`);
 console.log('Ancienne copie pré-CHRS1/pré-TOTP : migrations connues, identité et média conservés : OK');
 console.log('Échanges PWA ↔ natif : CHRS1–4, identités, permissions, média et reconnexion : OK');
}finally{fs.rmSync(temporaire,{recursive:true,force:true});}
