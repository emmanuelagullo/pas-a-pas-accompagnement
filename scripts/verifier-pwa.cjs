// Chromium réel ; serveur statique et profil éphémères, données fictives seulement.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {createRequire}=require('node:module');
const requirePwa=createRequire(path.resolve(__dirname,'../pwa/package.json'));
const {chromium}=process.env.PWA_PLAYWRIGHT?require(process.env.PWA_PLAYWRIGHT):requirePwa('playwright');
const root=process.env.PWA_BUNDLE?path.resolve(process.env.PWA_BUNDLE):path.resolve(__dirname,'../dist/pwa');
let servedRoot=process.env.PWA_OLD_BUNDLE?path.resolve(process.env.PWA_OLD_BUNDLE):root;
const types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.webmanifest':'application/manifest+json','.css':'text/css','.wasm':'application/wasm','.svg':'image/svg+xml','.png':'image/png'};
const base=process.env.PWA_BASE_PATH||'/chrs/';
const tls=process.env.PWA_TEST_HTTPS==='oui';let certificat;
let options={};
if(tls){
 certificat=fs.mkdtempSync(path.join(require('node:os').tmpdir(),'chrs-tls-fictif-'));
 require('node:child_process').execFileSync('openssl',['req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost','-keyout',path.join(certificat,'key.pem'),'-out',path.join(certificat,'cert.pem')],{stdio:'ignore'});
 options={key:fs.readFileSync(path.join(certificat,'key.pem')),cert:fs.readFileSync(path.join(certificat,'cert.pem'))};
}
const sorties=[];
let publication=null;const hash=b=>require('node:crypto').createHash('sha256').update(b).digest('hex');
const server=(tls?require('node:https'):http).createServer(options,(req,res)=>{
 const url=new URL(req.url,'http://localhost');sorties.push(url.pathname);
 if(!url.pathname.startsWith(base)){res.writeHead(404).end();return;}
 const relatif=url.pathname.slice(base.length)||'index.html',f=path.resolve(servedRoot,relatif);
 if(!f.startsWith(servedRoot+path.sep)){res.writeHead(403).end();return;}
 try{res.setHeader('Content-Type',types[path.extname(f)]||'application/octet-stream');res.end(publication?.get(relatif)||fs.readFileSync(f));}
 catch{res.writeHead(404).end();}
});
(async()=>{
 let browser;
 try{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const url=`${tls?'https':'http'}://127.0.0.1:${server.address().port}${base}`;
  browser=await chromium.launch({headless:true,...(process.env.PWA_CHROMIUM?{executablePath:process.env.PWA_CHROMIUM}:{}),args:['--no-sandbox','--disable-dev-shm-usage',...(tls?['--ignore-certificate-errors']:[])]});
  const context=await browser.newContext({ignoreHTTPSErrors:tls});let page=await context.newPage();
  page.on('pageerror',e=>console.error('PAGE',String(e)));
  page.on('console',m=>{if(m.type()==='error')console.error('CONSOLE',m.text());});
  async function ouvrir(){await page.goto(url);await page.frameLocator('#app').locator('h1').waitFor({timeout:120000});}
  await ouvrir();const frame=page.frameLocator('#app');
  await frame.locator('[name=username]').fill('essai-pwa');
  await frame.locator('[name=password1]').fill('Phrase fictive navigateur-854!');
  await frame.locator('[name=password2]').fill('Phrase fictive navigateur-854!');
  await frame.getByRole('button',{name:'Créer mon compte et commencer'}).click();
  await frame.getByRole('link',{name:'Créer une personne'}).click();
  await frame.locator('[name=designation]').fill('Personne fictive conservée');
  await frame.getByRole('button',{name:'Enregistrer'}).click();
  await frame.getByRole('heading',{name:'Personne fictive conservée'}).waitFor();
  const autre=await context.newPage();await autre.goto(url);
  await autre.getByText('Cet espace est déjà ouvert dans un autre onglet.').waitFor();await autre.close();
  await context.setOffline(true);await page.reload();
  await page.frameLocator('#app').locator('[name=username]').waitFor({timeout:120000});
  const apres=page.frameLocator('#app');
  await apres.locator('[name=username]').fill('essai-pwa');
  await apres.locator('[name=password]').fill('Phrase fictive navigateur-854!');
  await apres.getByRole('button',{name:'Se connecter'}).click();
  await apres.getByRole('link',{name:'Personnes',exact:true}).click();
  await apres.getByText('Personne fictive conservée').waitFor();
  // Le PDF doit être un téléchargement réel, y compris sans réseau.
  await apres.getByText('Personne fictive conservée',{exact:true}).click();
  const pdfFini=page.waitForEvent('download',{timeout:120000});
  await apres.getByRole('link',{name:'Télécharger la fiche PDF'}).click();
  const pdf=await pdfFini;
  assert.match(pdf.suggestedFilename(),/^fiche-personne-[a-f0-9-]+\.pdf$/);
  assert.equal(fs.readFileSync(await pdf.path()).subarray(0,5).toString(),'%PDF-');
  await apres.getByRole('link',{name:'Retour aux personnes'}).click();
  await context.setOffline(false);
  if(process.env.PWA_PRODUCTION==='oui'){
   assert.equal(await page.evaluate(()=>typeof window.pwaTest),'undefined');
   for(const nom of ['worker.js','shell.js']){
    const source=fs.readFileSync(path.join(root,nom),'utf8');assert(source.includes('const TEST=false;'));assert(!source.includes('__TEST__'));
   }
   await require('./verifier-stockage-pwa.cjs')(page,url);
   console.log('Construction normale : compte/personne/reprise hors ligne, protocole de test désactivé : OK');return;
  }
  async function connexion(){
   const f=page.frameLocator('#app');await f.locator('[name=username]').waitFor({timeout:120000});
   await f.locator('[name=username]').fill('essai-pwa');await f.locator('[name=password]').fill('Phrase fictive navigateur-854!');
   await f.getByRole('button',{name:'Se connecter'}).click();await f.getByRole('link',{name:'Personnes',exact:true}).click();
   await f.getByText('Personne fictive conservée').waitFor();
   // Le banc enchaîne plus de cinq connexions dans la même fenêtre fictive.
   // Réinitialisation par le protocole de test, jamais par le produit normal.
   await page.waitForFunction(()=>!!window.pwaTest);
   await page.evaluate(()=>window.pwaTest({kind:'test-write',code:'from identites.models import LimiteAuthentification; LimiteAuthentification.objects.all().delete()'}));
  }
  async function telecharger(id){const fini=page.waitForEvent('download',{timeout:120000});await page.locator('#'+id).click();return await (await fini).path();}
  const {execFileSync}=require('node:child_process');
  const python=process.env.PWA_PYTHON||'python3';
  function verifierZip(fichier,nombre){
   execFileSync(python,['-c',`import sys,zipfile,json,sqlite3,tempfile
from pathlib import Path
with zipfile.ZipFile(sys.argv[1]) as z,tempfile.TemporaryDirectory() as t:
 m=json.loads(z.read('manifest.json'));assert m['application']=='pas-a-pas-accompagnement'
 assert z.read('media/fictif.txt')==b'media fictif technique'
 z.extract('accompagnement.sqlite3',t)
 with sqlite3.connect(Path(t)/'accompagnement.sqlite3') as db:
  assert db.execute('SELECT count(*) FROM personnes_personne').fetchone()[0]==int(sys.argv[2])
  assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
  assert db.execute('PRAGMA foreign_key_check').fetchone() is None
  assert db.execute('SELECT count(*) FROM personnes_accompagnement_beneficiaires').fetchone()[0]==1
  assert db.execute('SELECT count(*) FROM personnes_affectation').fetchone()[0]==1
  assert db.execute('SELECT count(*) FROM personnes_situationsociale').fetchone()[0]==1
`,fichier,String(nombre)]);
  }
  if(process.env.PWA_OLD_BUNDLE){
   servedRoot=root;await page.evaluate(async()=>{await(await navigator.serviceWorker.getRegistration()).update();});
   await page.locator('#update').waitFor({state:'visible',timeout:120000});await page.locator('#update').click();await connexion();
   console.log('Transition réelle #SOC5a → #SOC5b : compte et personne conservés : OK');
  }
  await page.locator('summary').click();
  await page.evaluate(code=>window.pwaTest({kind:'test-write',code}),
   fs.readFileSync(path.join(__dirname,'jeu-technique-copies.py'),'utf8')+"\nfrom django.contrib.auth import get_user_model; preparer(get_user_model().objects.get()); from pathlib import Path; Path('/data/media').mkdir(exist_ok=True); Path('/data/media/fictif.txt').write_bytes(b'media fictif technique')");
  const copie=await telecharger('export');verifierZip(copie,1);
  // Variantes privées, jamais dans le bundle publié.
  const tmp=fs.mkdtempSync(path.join(require('node:os').tmpdir(),'chrs-copies-fictives-'));
  try{
   const native=path.join(tmp,'copie-native');
   const env={...process.env,ACCOMPAGNEMENT_DONNEES:native};
   execFileSync(python,[path.resolve(__dirname,'../manage.py'),'restaurer_copie',copie,native],{env:{...env,ACCOMPAGNEMENT_DONNEES:path.join(tmp,'operateur')}});
   execFileSync(python,[path.resolve(__dirname,'../manage.py'),'sauvegarder_paquet',path.join(tmp,'native.zip')],{env});
   verifierZip(path.join(tmp,'native.zip'),1);
   execFileSync(python,['-c',`import sys,zipfile,json,hashlib,sqlite3
from pathlib import Path
with zipfile.ZipFile(sys.argv[1]) as z:files={n:z.read(n) for n in z.namelist()}
root=Path(sys.argv[2])
for mode in ['etranger','altere','future']:
 v=files.copy();m=json.loads(v['manifest.json'])
 if mode=='etranger':m['application']='petits-pas'
 if mode=='altere':v['secret-key']=b'cle-alteree'
 if mode=='future':
  dbpath=root/'future.sqlite3';dbpath.write_bytes(v['accompagnement.sqlite3'])
  with sqlite3.connect(dbpath) as db:db.execute("INSERT INTO django_migrations(app,name,applied) VALUES ('identites','future_inconnue','2026-01-01')")
  v['accompagnement.sqlite3']=dbpath.read_bytes();m['files']['accompagnement.sqlite3']=hashlib.sha256(v['accompagnement.sqlite3']).hexdigest()
 v['manifest.json']=json.dumps(m).encode()
 with zipfile.ZipFile(root/(mode+'.zip'),'w') as z:
  for n,b in v.items():z.writestr(n,b)
`,copie,tmp]);
   await page.frameLocator('#app').getByRole('link',{name:'Créer une personne'}).click();
   await page.frameLocator('#app').locator('[name=designation]').fill('Personne fictive après copie');
   await page.frameLocator('#app').getByRole('button',{name:'Enregistrer'}).click();
   await page.frameLocator('#app').getByRole('heading',{name:'Personne fictive après copie'}).waitFor();
   for(const [mode,texte] of [['etranger','autre application'],['altere','altéré'],['future','plus récente']]){
    await page.locator('#restore-file').setInputFiles(path.join(tmp,mode+'.zip'));
    await page.locator('#notice').filter({hasText:texte}).waitFor({timeout:120000});
    assert(await page.locator('#preview').isHidden());
   }
   await page.locator('#restore-file').setInputFiles(copie);
   await page.locator('#summary').filter({hasText:'1 personne(s)'}).waitFor({timeout:120000});
   await page.locator('#cancel').click();
   await page.frameLocator('#app').getByRole('heading',{name:'Personne fictive après copie'}).waitFor();
   await page.locator('#restore-file').setInputFiles(copie);
   await page.locator('#confirm').waitFor({state:'visible',timeout:120000});
   await page.locator('#confirm').click();await connexion();
   assert.equal(await page.frameLocator('#app').getByText('Personne fictive après copie').count(),0);
   await page.locator('summary').click();verifierZip(await telecharger('recovery'),2);
   console.log('ZIP : sauvegarde native lisible, archives étrangère/altérée/future refusées, annulation intacte, restauration et secours : OK');
   // Arrêts réels du Worker de l'application aux deux côtés du commit OPFS.
   await page.waitForFunction(()=>!!window.pwaTest);
   async function interrompre(phase,nom){
    await page.evaluate(({phase,nom})=>{
     window.phaseSoc5=null;window.erreurSoc5=null;
     window.addEventListener('pwa-checkpoint',e=>{window.phaseSoc5=e.detail;},{once:true});
     window.pwaTest({kind:'test-write',code:`from personnes.models import Personne; Personne.objects.create(designation=${JSON.stringify(nom)},cree_par_id=Personne.objects.first().cree_par_id)`,failpoint:'pause-'+phase}).catch(e=>{window.erreurSoc5=String(e);});
    },{phase,nom});
    await page.waitForFunction(p=>window.phaseSoc5===p||window.erreurSoc5,phase,{timeout:30000});
    assert.equal(await page.evaluate(()=>window.erreurSoc5),null);
    await page.reload();await connexion();
   }
   await interrompre('before-activate','Écriture non confirmée');
   assert.equal(await page.frameLocator('#app').getByText('Écriture non confirmée').count(),0);
   await interrompre('after-activate','Écriture confirmée');
   await page.frameLocator('#app').getByText('Écriture confirmée').waitFor();
   const erreur=await page.evaluate(async()=>{
    try{await window.pwaTest({kind:'test-write',code:"from personnes.models import Personne; Personne.objects.create(designation='Quota non confirmé',cree_par_id=Personne.objects.first().cree_par_id)",failpoint:'quota'});return '';}
    catch(e){return String(e);}
   });assert.match(erreur,/Quota/);
   await page.reload();await connexion();assert.equal(await page.frameLocator('#app').getByText('Quota non confirmé').count(),0);
   console.log('Application : interruption avant/après activation, quota, réouverture du dernier état confirmé : OK');
   // Une ressource altérée interdit l'installation ; la bonne version attend confirmation.
   const original=JSON.parse(fs.readFileSync(path.join(root,'config.json')));
   function publier(suffixe,alteree=false){
    const c=structuredClone(original);c.version=original.version+'-'+suffixe;
    const sw=Buffer.from(fs.readFileSync(path.join(root,'sw.js'),'utf8').replaceAll(original.version,c.version));
    c.assets.find(a=>a.url==='/sw.js').sha256=hash(sw);
    if(alteree)c.assets.find(a=>a.url==='/shell.js').sha256='0'.repeat(64);
    publication=new Map([['sw.js',sw],['config.json',Buffer.from(JSON.stringify(c))]]);
   }
   publier('invalide',true);
   await page.evaluate(async()=>{
    const r=await navigator.serviceWorker.getRegistration();
    await new Promise(async(resolve,reject)=>{
     const timer=setTimeout(()=>reject(Error('Installation invalide non terminée')),60000);
     r.addEventListener('updatefound',()=>{const sw=r.installing;sw.addEventListener('statechange',()=>{if(sw.state==='redundant'){clearTimeout(timer);resolve();}});},{once:true});
     try{await r.update();}catch(e){clearTimeout(timer);reject(e);}
    });
   });assert(await page.locator('#update').isHidden());
   publier('qualifiee');
   await page.evaluate(async()=>{await(await navigator.serviceWorker.getRegistration()).update();});
   await page.locator('#update').waitFor({state:'visible',timeout:120000});
   // Une vérification en cours bloque l'activation de la nouvelle version.
   await page.locator('summary').click();await page.locator('#restore-file').setInputFiles(copie);
   await page.locator('#confirm').waitFor({state:'visible',timeout:120000});assert(await page.locator('#update').isDisabled());
   await page.locator('#cancel').click();await page.locator('#update').click();await connexion();
   await page.frameLocator('#app').getByText('Écriture confirmée').waitFor();
   await context.setOffline(true);await page.reload();await connexion();await context.setOffline(false);
   console.log('Mise à jour : ressource altérée refusée, activation explicite hors restauration, données/reconnexion/hors ligne conservés : OK');
   // Base plus récente : pas d'espace vide, copie brute et retour explicite au ZIP.
   await page.evaluate(()=>window.pwaTest({kind:'test-write',code:"from django.db import connection; connection.cursor().execute(\"INSERT INTO django_migrations(app,name,applied) VALUES ('identites','future_inconnue','2026-01-01')\")"}));
   await page.reload();await page.locator('#status').filter({hasText:'plus récente'}).waitFor({timeout:120000});
   assert(await page.locator('#app').isHidden());await page.locator('summary').click();verifierZip(await telecharger('export'),2);
   await page.locator('#restore-file').setInputFiles(copie);await page.locator('#confirm').waitFor({state:'visible',timeout:120000});
   await page.locator('#confirm').click();await connexion();
   console.log('Base future : ouverture refusée, export sans migration et restauration explicite : OK');
   // Un octet altéré dans le blob confirmé n'entraîne pas la création d'une base vide.
   await page.evaluate(async()=>{
    const r=indexedDB.open('pas-accompagnement-pwa-v1'+(location.pathname==='/'?'':'-'+encodeURIComponent(location.pathname)));
    const actif=await new Promise((resolve,reject)=>{r.onsuccess=()=>{const db=r.result;const q=db.transaction('state').objectStore('state').get('active');q.onsuccess=()=>{db.close();resolve(q.result);};q.onerror=()=>reject(q.error);};r.onerror=()=>reject(r.error);});
    const dir=await(await navigator.storage.getDirectory()).getDirectoryHandle('pas-accompagnement-pwa'+(location.pathname==='/'?'':'-'+encodeURIComponent(location.pathname)));
    const manifeste=JSON.parse(await(await(await dir.getFileHandle(actif.file)).getFile()).text());
    const f=await dir.getFileHandle(manifeste.files['accompagnement.sqlite3'].file);
    const w=await f.createWritable({keepExistingData:true});await w.write({type:'write',position:0,data:new Uint8Array([0])});await w.close();
   });
   await page.reload();await page.locator('#status').filter({hasText:'endommagé'}).waitFor({timeout:120000});
   assert(await page.locator('#app').isHidden());await page.locator('summary').click();
   await page.locator('#export').click();await page.locator('#notice').filter({hasText:'endommagé'}).waitFor({timeout:120000});
   // Restaurer une copie issue du programme natif, même après échec de démarrage.
   await page.locator('#restore-file').setInputFiles(path.join(tmp,'native.zip'));
   await page.locator('#confirm').waitFor({state:'visible',timeout:120000});await page.locator('#confirm').click();await connexion();
   console.log('Corruption : ouverture/export courant refusés, copie native restaurée explicitement, aucune base vide : OK');
  }finally{fs.rmSync(tmp,{recursive:true,force:true});}
  await require('./verifier-stockage-pwa.cjs')(page,url);
  assert(!sorties.some(p=>p.startsWith(base+'app/')),'Requête métier sortie vers le serveur statique');
  console.log('Chromium CHRS : création → second onglet refusé → relance hors ligne → reconnexion et persistance : OK');
 }finally{await browser?.close();await new Promise(r=>server.close(r));if(certificat)fs.rmSync(certificat,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
