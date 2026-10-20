import {creerStockage} from './socle/stockage.mjs';
import {checkStorage} from './socle/capacites.mjs';
const TEST=__TEST__;
const BASE=new URL('./',import.meta.url).pathname;
const stockage=creerStockage({application:'pas-a-pas-accompagnement',database:'pas-accompagnement-pwa-v1',
  repertoire:'pas-accompagnement-pwa',base:'accompagnement.sqlite3'},BASE);
let ESSAI=false;
let python,pont,config,fatal=false,initialise=false,prepare=false,file=Promise.resolve();
function appel(nom,...args){const f=pont[nom];try{return f(...args);}finally{f.destroy();}}
function octets(nom,...args){const valeur=appel(nom,...args);try{return valeur.toJs();}finally{valeur.destroy();}}
async function conserver(failpoint='',preserve=false){
  return stockage.save(JSON.parse(appel('inventory')),nom=>octets('file_bytes',nom),config.version,failpoint,preserve,false,null,!preserve);
}
async function charger(){
  if(python)return;
  await checkStorage('pas-accompagnement-verification-');
  config=await(await fetch('./config.json')).json();
  if(config.application!=='pas-a-pas-accompagnement')throw new Error('Configuration étrangère');
  self.postMessage({kind:'progress',text:'Chargement du moteur local…'});
  const {loadPyodide,version}=await import('./runtime/pyodide.mjs');
  if(version!==config.pyodide)throw new Error('Moteur incohérent');
  python=await loadPyodide({indexURL:new URL('./runtime/',location.href).href});
  await python.loadPackage(['micropip','pycryptodome','pillow']);
  const micropip=python.pyimport('micropip');
  try{await micropip.install(config.wheels.map(n=>new URL('./wheels/'+n,location.href).href));}
  finally{micropip.destroy();}
  python.unpackArchive(new Uint8Array(await(await fetch('./application.zip')).arrayBuffer()),'zip',{extractDir:'/application'});
  python.runPython("import sys;sys.path.insert(0,'/application')");
  pont=python.pyimport('pwa.bridge');
}
async function lireEtat(secours=false){
  if(secours&&!(await stockage.informations()).secours)throw new Error('Aucun état avant remplacement disponible.');
  const etat=await stockage.load(config.version,secours);
  if(etat){
    if(!etat.files)throw new Error('Format local incompatible');
    for(const [nom,entree] of Object.entries(etat.files))appel('restore_file',nom,await etat.read(entree));
  }
  return etat;
}
async function traiter(message){
  if(fatal)throw new Error('Moteur interrompu. Fermez puis rouvrez l’application.');
  if(!python){ESSAI=message.essai===true;stockage.configurerEspace(ESSAI);}
  else if((message.essai===true)!==ESSAI)throw new Error('Changement d’espace dans un moteur ouvert interdit');
  if(message.kind==='init'){
    if(python)throw new Error('Moteur déjà ouvert');
    await charger();const etat=await lireEtat();
    appel('initialize',location.origin,BASE,ESSAI,ESSAI&&!etat);
    await conserver();initialise=true;return {ready:true};
  }
  if(message.kind==='export'){
    if(python)throw new Error('La copie exige un moteur neuf');
    await charger();
    if(!await lireEtat(Boolean(message.secours)))throw new Error('Aucun état enregistré sur cet appareil.');
    return {body:octets('export_zip')};
  }
  if(message.kind==='prepare'){
    if(python)throw new Error('La vérification exige un moteur neuf');
    if(!message.body||message.body.byteLength>64*1024**2)throw new Error('ZIP supérieur à 64 Mio.');
    await charger();
    const resultat=JSON.parse(appel('prepare_zip',message.body,location.origin,BASE,ESSAI));
    prepare=true;return resultat;
  }
  if(message.kind==='activate'){
    if(!prepare)throw new Error('Aucune copie vérifiée');
    await conserver(TEST?message.failpoint||'':'',true);
    prepare=false;return {ready:true};
  }
  if(!initialise)throw new Error('Moteur non ouvert');
  if(TEST&&message.kind==='test-write'){
    python.runPython(message.code);await conserver(message.failpoint||'');return {ready:true};
  }
  if(message.kind==='http'){
    const requete=message.request;
    if(requete.body.byteLength>1024**2)throw new Error('Envoi supérieur à 1 Mio.');
    const reponse=JSON.parse(appel('handle',JSON.stringify({...requete,body:undefined}),requete.body));
    reponse.body=octets('response_bytes');
    await conserver();return reponse;
  }
  throw new Error('Opération inconnue');
}
self.onmessage=event=>{
  const port=event.ports[0];
  file=file.then(async()=>{
    try{const resultat=await traiter(event.data);port.postMessage({ok:true,value:resultat},resultat.body?[resultat.body.buffer]:[]);}
    catch(error){fatal=true;port.postMessage({ok:false,error:String(error)});}
    finally{port.close();}
  });
};
