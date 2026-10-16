import {creerStockage} from './socle/stockage.mjs';
import {checkStorage} from './socle/capacites.mjs';
const BASE=new URL('./',import.meta.url).pathname;
const stockage=creerStockage({application:'pas-a-pas-accompagnement',database:'pas-accompagnement-pwa-v1',
  repertoire:'pas-accompagnement-pwa',base:'accompagnement.sqlite3'},BASE);
let python,pont,config,fatal=false,initialise=false,file=Promise.resolve();
function appel(nom,...args){const f=pont[nom];try{return f(...args);}finally{f.destroy();}}
async function conserver(){
  return stockage.save(JSON.parse(appel('inventory')),nom=>{
    const valeur=appel('file_bytes',nom);try{return valeur.toJs();}finally{valeur.destroy();}
  },config.version);
}
async function traiter(message){
  if(fatal)throw new Error('Enregistrement interrompu. Fermez puis rouvrez l’application pour retrouver le dernier état confirmé.');
  if(message.kind==='init'){
    if(initialise)throw new Error('Moteur déjà ouvert');
    await checkStorage('pas-accompagnement-verification-');
    config=await(await fetch('./config.json')).json();
    if(config.application!=='pas-a-pas-accompagnement')throw new Error('Configuration étrangère');
    const etat=await stockage.load(config.version);
    self.postMessage({kind:'progress',text:'Chargement du moteur local…'});
    const {loadPyodide,version}=await import('./runtime/pyodide.mjs');
    if(version!==config.pyodide)throw new Error('Moteur incohérent');
    python=await loadPyodide({indexURL:new URL('./runtime/',location.href).href});
    await python.loadPackage(['micropip','pycryptodome']);
    const micropip=python.pyimport('micropip');
    try{await micropip.install(config.wheels.map(n=>new URL('./wheels/'+n,location.href).href));}
    finally{micropip.destroy();}
    python.unpackArchive(new Uint8Array(await(await fetch('./application.zip')).arrayBuffer()),'zip',{extractDir:'/application'});
    python.runPython("import sys;sys.path.insert(0,'/application')");
    pont=python.pyimport('pwa.bridge');
    if(etat){
      if(!etat.files)throw new Error('Format local incompatible');
      for(const [nom,entree] of Object.entries(etat.files))appel('restore_file',nom,await etat.read(entree));
    }
    appel('initialize',location.origin,BASE);
    await conserver();
    initialise=true;
    return {ready:true};
  }
  if(!initialise)throw new Error('Moteur non ouvert');
  if(message.kind==='http'){
    const requete=message.request;
    if(requete.body.byteLength>1024**2)throw new Error('Envoi supérieur à 1 Mio : non pris en charge par ce prototype.');
    const reponse=JSON.parse(appel('handle',JSON.stringify({...requete,body:undefined}),requete.body));
    const corps=appel('response_bytes');
    try{reponse.body=corps.toJs();}finally{corps.destroy();}
    await conserver(); // réponse seulement après activation durable du pointeur
    return reponse;
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
