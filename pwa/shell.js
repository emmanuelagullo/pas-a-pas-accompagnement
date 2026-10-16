import {requestWorker} from './socle/transport.mjs';
const BASE=new URL('./',import.meta.url).pathname;
const status=document.querySelector('#status'),frame=document.querySelector('#app');
let worker,ready=false,registration,occupations=0;
function arreter(message){ready=false;worker?.terminate();worker=null;frame.hidden=true;status.textContent=message;}
function rpc(message){return requestWorker(worker,message,{application:'Pas à Pas',onTimeout:()=>arreter('Résultat incertain. Fermez puis rouvrez cette page.')});}
async function ouvrir(){
  if(!isSecureContext||!navigator.serviceWorker||!navigator.locks||!navigator.storage?.getDirectory)throw new Error('Ce navigateur ne propose pas les fonctions locales requises.');
  registration=await navigator.serviceWorker.register('./sw.js',{scope:'./'});
  await navigator.serviceWorker.ready;
  if(navigator.serviceWorker.controller?.scriptURL!==new URL('./sw.js',location.href).href){
    await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(new Error('Téléchargement incomplet. Rouvrez la page après vérification du réseau.')),120000);
      navigator.serviceWorker.addEventListener('controllerchange',()=>{clearTimeout(timer);resolve();},{once:true});
    });
  }
  const miseAJour=()=>{document.querySelector('#update').hidden=!registration.waiting;};
  registration.addEventListener('updatefound',()=>{
    registration.installing?.addEventListener('statechange',miseAJour);
  });miseAJour();
  worker=new Worker('./worker.js',{type:'module'});
  worker.onmessage=e=>{if(e.data.kind==='progress')status.textContent=e.data.text;};
  await rpc({kind:'init'});
  ready=true;status.textContent='Prêt. Données fictives uniquement.';frame.hidden=false;frame.src=BASE+'app/';
}
navigator.serviceWorker?.addEventListener('message',async e=>{
  if(e.data.kind==='owner'){e.ports[0].postMessage(ready);return;}
  if(e.data.kind==='http'){
    const port=e.ports[0];
    occupations++;document.querySelector('#update').disabled=true;
    try{if(!ready)throw new Error('Moteur fermé');const r=await rpc(e.data);port.postMessage({ok:true,...r},r.body?[r.body.buffer]:[]);}
    catch(error){arreter('Enregistrement interrompu. Fermez puis rouvrez la page.');port.postMessage({ok:false,error:String(error)});}
    finally{occupations--;document.querySelector('#update').disabled=occupations!==0;port.close();}
  }
});
document.querySelector('#update').onclick=async()=>{
  if(!registration.waiting||occupations)return;
  arreter('Mise à jour en cours…');
  navigator.serviceWorker.addEventListener('controllerchange',()=>location.reload(),{once:true});
  registration.waiting.postMessage({kind:'activate-update'});
};
document.querySelector('#persist').onclick=async()=>{
  const oui=await navigator.storage.persist();
  document.querySelector('#storage').textContent=oui?'Protection du stockage accordée.':'Protection non accordée. Ne conservez que des données fictives.';
};
if(navigator.locks){
  navigator.locks.request('pas-accompagnement-pwa-owner-'+BASE,{ifAvailable:true},async verrou=>{
    if(!verrou){status.textContent='Cet espace est déjà ouvert dans un autre onglet.';return;}
    try{await ouvrir();await new Promise(()=>{});}catch(error){arreter(String(error));}
  });
}else status.textContent='Navigateur incompatible : verrou local absent.';
