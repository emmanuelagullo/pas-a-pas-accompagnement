import {requestWorker} from './socle/transport.mjs';
const TEST=__TEST__;
const ESSAI=new URL(location.href).searchParams.get('essai')==='oui';
const BASE=new URL('./',import.meta.url).pathname;
const status=document.querySelector('#status'),frame=document.querySelector('#app'),notice=document.querySelector('#notice');
let worker,candidate,ready=false,registration,occupations=0,operation=false,proprietaire=false;
const changement=document.querySelector('#changer-espace');
changement.textContent=ESSAI?'Revenir à mon espace habituel':'Essayer avec Les Passerelles';
changement.href=ESSAI?BASE:BASE+'essai.html';
document.querySelector('#espace').textContent=ESSAI?'Espace d’essai Les Passerelles — distinct de votre espace habituel. Vos essais sont conservés.':'Espace habituel de ce navigateur — données conservées sur cet appareil.';
document.querySelector('#comptes-essai').hidden=!ESSAI;
changement.onclick=e=>{
 if(!proprietaire||operation||occupations||candidate){e.preventDefault();notice.textContent='Terminez ou annulez l’opération en cours et fermez les autres onglets avant de changer d’espace.';}
};
function boutons(){
  document.querySelector('#update').disabled=!ready||operation||occupations!==0||!!candidate;
  for(const id of ['export','recovery','restore-file'])document.getElementById(id).disabled=!proprietaire||operation||occupations!==0||!!candidate;
  for(const id of ['confirm','cancel'])document.getElementById(id).disabled=operation;
}
function arreter(message){ready=false;worker?.terminate();worker=null;frame.hidden=true;status.textContent=message;boutons();}
function rpc(cible,message){return requestWorker(cible,{...message,essai:ESSAI},{application:'Pas à Pas',onTimeout:()=>{
  cible.terminate();if(cible===worker)arreter('Résultat incertain. Fermez puis rouvrez cette page.');
 }});}
function nouveau(){
  const moteur=new Worker('./worker.js',{type:'module'});
  moteur.onmessage=e=>{if(e.data.kind==='progress')status.textContent=e.data.text;
    if(TEST&&e.data.kind==='test-checkpoint')window.dispatchEvent(new CustomEvent('pwa-checkpoint',{detail:e.data.phase}));};return moteur;
}
async function exclusif(travail){
  if(!proprietaire||operation||occupations)return;
  operation=true;frame.hidden=true;notice.textContent='';boutons();
  try{await travail();}catch(error){notice.textContent=String(error);}
  finally{operation=false;frame.hidden=!ready||!!candidate;status.textContent=ready?'Prêt. Données fictives uniquement.':status.textContent;boutons();}
}
async function ouvrir(){
  if(!isSecureContext||!navigator.serviceWorker||!navigator.storage?.getDirectory)throw new Error('Ce navigateur ne propose pas les fonctions locales requises.');
  registration=await navigator.serviceWorker.register('./sw.js',{scope:'./'});
  await navigator.serviceWorker.ready;
  if(navigator.serviceWorker.controller?.scriptURL!==new URL('./sw.js',location.href).href){
    await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(new Error('Téléchargement incomplet. Rouvrez la page après vérification du réseau.')),120000);
      navigator.serviceWorker.addEventListener('controllerchange',()=>{clearTimeout(timer);resolve();},{once:true});
    });
  }
  const miseAJour=()=>{document.querySelector('#update').hidden=!registration.waiting;};
  registration.addEventListener('updatefound',()=>{registration.installing?.addEventListener('statechange',miseAJour);});miseAJour();
  worker=nouveau();await rpc(worker,{kind:'init'});
  ready=true;status.textContent='Prêt. Données fictives uniquement.';frame.hidden=false;frame.src=BASE+'app/';boutons();
  if(TEST)window.pwaTest=async message=>{
    try{return await rpc(worker,message);}catch(error){arreter('Enregistrement interrompu. Fermez puis rouvrez la page.');throw error;}
  };
}
navigator.serviceWorker?.addEventListener('message',async e=>{
  if(e.data.kind==='owner'){e.ports[0].postMessage(ready);return;}
  if(e.data.kind==='http'){
    const port=e.ports[0];occupations++;boutons();
    try{if(!ready)throw new Error('Moteur fermé');const r=await rpc(worker,e.data);port.postMessage({ok:true,...r},r.body?[r.body.buffer]:[]);}
    catch(error){arreter('Enregistrement interrompu. Fermez puis rouvrez la page.');port.postMessage({ok:false,error:String(error)});}
    finally{occupations--;boutons();port.close();}
  }
});
for(const [id,secours] of [['export',false],['recovery',true]]){
 document.getElementById(id).onclick=()=>exclusif(async()=>{
  const lecteur=nouveau();
  try{
   const r=await rpc(lecteur,{kind:'export',secours});const lien=document.createElement('a');
   const url=URL.createObjectURL(new Blob([r.body],{type:'application/zip'}));
   lien.href=url;lien.download='pas-a-pas-'+(secours?'avant-remplacement-':'')+new Date().toISOString().replaceAll(':','-')+'.zip';
   lien.click();setTimeout(()=>URL.revokeObjectURL(url),60000);
   notice.textContent='Copie préparée. Vérifiez le téléchargement et conservez-la hors de cet appareil.';
  }finally{lecteur.terminate();}
 });
}
document.querySelector('#restore-file').onchange=e=>{
 const fichier=e.target.files[0];e.target.value='';if(!fichier)return;
 exclusif(async()=>{
  if(fichier.size>64*1024**2)throw new Error('Choisissez un ZIP de 64 Mio maximum.');
  const moteur=nouveau();
  try{
   const r=await rpc(moteur,{kind:'prepare',body:new Uint8Array(await fichier.arrayBuffer())});
   candidate=moteur;document.querySelector('#preview').hidden=false;
   document.querySelector('#summary').textContent=`Copie vérifiée : ${r.personnes} personne(s), ${r.comptes} compte(s), ${r.medias} média(s). Date : ${r.date||'non indiquée'}.`;
  }catch(error){moteur.terminate();throw error;}
 });
};
document.querySelector('#cancel').onclick=()=>{
 if(operation)return;candidate?.terminate();candidate=null;document.querySelector('#preview').hidden=true;
 frame.hidden=!ready;notice.textContent='Restauration annulée. L’espace courant est conservé.';boutons();
};
document.querySelector('#confirm').onclick=()=>exclusif(async()=>{
 if(!candidate)return;
 arreter('Installation de la copie…');
 try{await rpc(candidate,{kind:'activate'});location.reload();}
 catch(error){candidate.terminate();candidate=null;document.querySelector('#preview').hidden=true;throw error;}
});
document.querySelector('#update').onclick=async()=>{
 if(!ready||!registration.waiting||occupations||operation||candidate)return;
 arreter('Mise à jour en cours…');
 navigator.serviceWorker.addEventListener('controllerchange',()=>location.reload(),{once:true});
 registration.waiting.postMessage({kind:'activate-update'});
};
document.querySelector('#persist').onclick=async()=>{
 try{const oui=await navigator.storage.persist();document.querySelector('#storage').textContent=oui?'Protection du stockage accordée.':'Protection non accordée. Conservez une copie ZIP hors appareil.';}
 catch(error){notice.textContent=String(error);}
};
boutons();
if(navigator.locks){
 navigator.locks.request('pas-accompagnement-pwa-owner-'+BASE,{ifAvailable:true},async verrou=>{
  if(!verrou){status.textContent='Cet espace est déjà ouvert dans un autre onglet.';return;}
  proprietaire=true;
  try{await ouvrir();}catch(error){arreter(String(error));}finally{boutons();}
  await new Promise(()=>{});
 });
}else status.textContent='Navigateur incompatible : verrou local absent.';
