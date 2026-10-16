// Contrat réel OPFS/IndexedDB, profils exclusivement fictifs, hors données de l'interface.
module.exports=async function verifierStockage(page,url){
 await page.evaluate(async url=>{
  const source=`import {creerStockage} from ${JSON.stringify(new URL('socle/stockage.mjs',url).href)};
const profils={pp:{application:'petits-pas',database:'soc5-test-pp',repertoire:'soc5-test-pp',base:'carnet.sqlite3',legacy:true},
chrs:{application:'pas-a-pas-accompagnement',database:'soc5-test-chrs',repertoire:'soc5-test-chrs',base:'accompagnement.sqlite3'}};
const instances=Object.fromEntries(Object.entries(profils).map(([k,p])=>[k,creerStockage(p,'/contrat-fictif/')]));
const digest=async b=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',b)),n=>n.toString(16).padStart(2,'0')).join('');
self.onmessage=async e=>{try{
 const {profil='pp',action,valeur,version='v1',failpoint=''}=e.data,s=instances[profil],p=profils[profil];
 if(action==='save'){
  const donnees={[p.base]:new TextEncoder().encode(valeur),'secret-key':new TextEncoder().encode('cle-fictive')};
  const files={};for(const [n,b] of Object.entries(donnees))files[n]={size:b.length,hash:await digest(b)};
  await s.save({files,bytes:Object.values(donnees).reduce((a,b)=>a+b.length,0)},n=>donnees[n],version,failpoint);
  self.postMessage({ok:true});
 }else{const t=await s.load(version,action==='recovery');self.postMessage({ok:true,value:t?new TextDecoder().decode(await t.read(t.files[p.base])):null});}
}catch(error){self.postMessage({error:String(error)});}};`;
  const blob=URL.createObjectURL(new Blob([source],{type:'text/javascript'}));
  let worker;
  const ouvrir=()=>{worker=new Worker(blob,{type:'module'});};ouvrir();
  const rpc=message=>new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>reject(Error('Délai contrat OPFS dépassé')),30000);
   worker.onmessage=e=>{clearTimeout(timer);resolve(e.data);};worker.onerror=e=>{clearTimeout(timer);reject(Error(e.message));};
   worker.postMessage(message);
  });
  const egal=(a,b)=>{if(a!==b)throw Error(`Contrat OPFS : ${a} != ${b}`);};
  try{
   egal((await rpc({action:'save',valeur:'école fictive'})).ok,true);
   egal((await rpc({profil:'chrs',action:'save',valeur:'personne fictive'})).ok,true);
   egal((await rpc({action:'load'})).value,'école fictive');
   egal((await rpc({profil:'chrs',action:'load'})).value,'personne fictive');
   const avant=await rpc({action:'save',valeur:'jamais confirmé',failpoint:'pause-before-activate'});
   egal(avant.kind,'test-checkpoint');egal(avant.phase,'before-activate');
   worker.terminate();ouvrir();
   egal((await rpc({action:'load'})).value,'école fictive');
   egal((await rpc({action:'save',valeur:'état confirmé',version:'v2'})).ok,true);
   worker.terminate();ouvrir();
   egal((await rpc({action:'load',version:'v2'})).value,'état confirmé');
   egal((await rpc({action:'recovery',version:'v2'})).value,'école fictive');
   egal((await rpc({profil:'chrs',action:'load'})).value,'personne fictive');
  }finally{worker.terminate();URL.revokeObjectURL(blob);}
 },url);
 console.log('OPFS réel : profils séparés, interruption avant activation, état confirmé et secours : OK');
};
