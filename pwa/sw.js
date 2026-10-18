const BASE=new URL('./',self.location.href).pathname;
const PREFIX='pas-accompagnement-pwa-'+BASE;
const VERSION='__BUILD__';
const CACHE=PREFIX+VERSION;
self.addEventListener('install',e=>e.waitUntil((async()=>{
  const config=await(await fetch(BASE+'config.json',{cache:'no-store'})).json();
  if(config.application!=='pas-a-pas-accompagnement'||config.version!==VERSION)throw new Error('Produit incorrect');
  const cache=await caches.open(CACHE);
  try{
    for(const asset of config.assets){
      const reponse=await fetch(BASE+asset.url.replace(/^\//,''),{cache:'no-store'});
      if(!reponse.ok)throw new Error('Ressource absente');
      const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await reponse.clone().arrayBuffer())),b=>b.toString(16).padStart(2,'0')).join('');
      if(hash!==asset.sha256)throw new Error('Ressource altérée');
      await cache.put(BASE+asset.url.replace(/^\//,''),reponse);
    }
    await cache.put(BASE+'config.json',new Response(JSON.stringify(config),{headers:{'Content-Type':'application/json'}}));
  }catch(error){await caches.delete(CACHE);throw error;}
})()));
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
async function proprietaire(){
  const candidats=(await self.clients.matchAll({type:'window'})).filter(c=>[BASE,BASE+'index.html'].includes(new URL(c.url).pathname));
  let actif=null;
  for(const candidat of candidats){
    const oui=await new Promise(resolve=>{
      const canal=new MessageChannel();
      const timer=setTimeout(()=>{canal.port1.close();resolve(false);},1000);
      canal.port1.onmessage=e=>{clearTimeout(timer);canal.port1.close();resolve(e.data===true);};
      candidat.postMessage({kind:'owner'},[canal.port2]);
    });
    if(oui){if(actif)throw new Error('Plusieurs propriétaires');actif=candidat;}
  }
  return actif;
}
async function local(requete){
  const client=await proprietaire();
  if(!client)return new Response('Ouvrez l’application depuis son accueil.',{status:503});
  const body=['GET','HEAD'].includes(requete.method)?new Uint8Array():new Uint8Array(await requete.arrayBuffer());
  if(body.length>1024**2)return new Response('Envoi supérieur à 1 Mio.',{status:413});
  const headers=[...requete.headers];
  if(!requete.headers.has('referer')&&/^https?:\/\//.test(requete.referrer))headers.push(['Referer',requete.referrer]);
  return new Promise(resolve=>{
    const canal=new MessageChannel();
    const timer=setTimeout(()=>{canal.port1.close();resolve(new Response('Résultat incertain. Fermez puis rouvrez l’application.',{status:503}));},16*60*1000);
    canal.port1.onmessage=e=>{
      clearTimeout(timer);canal.port1.close();const r=e.data;
      if(!r.ok){resolve(new Response('Enregistrement interrompu. Fermez puis rouvrez l’application.',{status:507}));return;}
      resolve(new Response(requete.method==='HEAD'||[204,304].includes(r.status)?null:r.body,{status:r.status,headers:r.headers}));
    };
    client.postMessage({kind:'http',request:{url:requete.url,method:requete.method,headers,body}},[canal.port2,body.buffer]);
  });
}
self.addEventListener('fetch',e=>{
  const url=new URL(e.request.url);
  if(url.origin!==self.location.origin||!url.pathname.startsWith(BASE))return;
  if(url.pathname.startsWith(BASE+'app/'))e.respondWith(local(e.request).catch(()=>new Response('Moteur interrompu.',{status:503})));
  else e.respondWith((async()=>{
    const cache=await caches.open(CACHE);
    return await cache.match(url.pathname===BASE?BASE+'index.html':url.pathname)||new Response('Ressource locale absente.',{status:404});
  })());
});
// La coque a déjà arrêté le runtime ; aucun effacement des données OPFS.
self.addEventListener('message',e=>{if(e.data?.kind==='activate-update')e.waitUntil(self.skipWaiting());});
