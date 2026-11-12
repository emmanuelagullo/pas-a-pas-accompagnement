/* Aides de saisie communes ; le calcul et les écritures restent serveur. */
(() => {
  if(window.PasCollectifInitialise)return;window.PasCollectifInitialise=true;
  const lire=(f,id)=>{try{return JSON.parse(f.querySelector('[data-collectif-json="'+id+'"]')?.value || '{}');}catch(_){return {};}};
  const formulaires=()=>document.querySelectorAll('#collectif-form form');
  const compte=new WeakMap(),delais=new WeakMap();let socialOccupe=false,socialModifie=false,rubriqueSociale=null;
  function bornes(f) {
    const midi=f.elements.dejeuner,soir=f.elements.diner;if(!midi || !soir)return;
    const disponibles=lire(f,'collectif-offres')[f.elements.offre?.value];
    for(const [cle,champ] of [['dejeuner',midi],['diner',soir]]) {
      champ.disabled=Boolean(disponibles && !disponibles[cle]);if(champ.disabled)champ.checked=false;
    }
    if(disponibles && !midi.checked && !soir.checked){if(disponibles.dejeuner)midi.checked=true;else soir.checked=true;}
    const actifs=[midi,soir].filter(e=>e.checked),seul=actifs.length===1?actifs[0].name:null;
    for(const cle of ['premier','dernier']){
      const champ=f.elements[cle];if(!champ)continue;
      if(seul){champ.value=seul;champ.dataset.automatique='1';}
      else if(champ.dataset.automatique){champ.value=cle==='premier'?'dejeuner':'diner';delete champ.dataset.automatique;}
      champ.disabled=Boolean(seul);
    }
  }
  function groupe(f) {
    const photo=lire(f,'collectif-composition');if(!photo.total)return;
    const total={...photo.total};
    if(f.elements.restreindre?.checked){
      Object.keys(total).forEach(k=>total[k]=Number(f.elements['selection_'+k]?.value || 0));
      f.querySelectorAll('[name=selection]:checked').forEach(e=>{const k=photo.identites[e.value] || 'inconnu';total[k]=(total[k] || 0)+1;});
    }
    Object.entries(total).forEach(([k,n])=>{const champ=f.elements['couverts_'+k];if(champ && !champ.dataset.personnalise)champ.value=String(n);});
  }
  function prix(f,proposes) {
    f.querySelectorAll('input[name^="prix_"]').forEach(champ=>{if(!champ.dataset.personnalise)champ.value=proposes[champ.name.slice(5)] ?? '';});
  }
  async function calculer(f,actualiserPrix=false) {
    if(!f.elements.dejeuner)return;
    const n=(compte.get(f)||0)+1;compte.set(f,n);
    const url=new URL(f.action,location.href);url.searchParams.set('apercu','1');
    const out=f.querySelector('[data-collectif-calcul]');
    try {
      const r=await fetch(url,{method:'POST',credentials:'same-origin',body:new FormData(f)});
      if(!r.ok)throw Error();const data=await r.json();if(compte.get(f)!==n || !f.isConnected)return;
      if(actualiserPrix && data.prix){prix(f,data.prix);calculer(f);return;}
      if(out)out.textContent=data.message;
    } catch(_) {if(out && compte.get(f)===n)out.textContent='Aperçu indisponible. Le calcul sera vérifié à l’enregistrement.';}
  }
  function initialiser(){formulaires().forEach(f=>{if(f.dataset.collectifInitialise)return;f.dataset.collectifInitialise='1';if(f.hasAttribute('data-prix-conserves'))f.querySelectorAll('input[name^=prix_]').forEach(e=>e.dataset.personnalise='1');bornes(f);calculer(f);});}
  document.addEventListener('input',e=>{
    const f=e.target.closest('#collectif-form form');if(!f)return;
    if(e.target.name?.startsWith('prix_') || e.target.name?.startsWith('couverts_'))e.target.dataset.personnalise='1';
    if(f.matches('[data-collectif-form]'))socialModifie=true;
    groupe(f);clearTimeout(delais.get(f));delais.set(f,setTimeout(()=>calculer(f,['debut','devise'].includes(e.target.name)),250));
  });
  document.addEventListener('change',e=>{
    const f=e.target.closest('#collectif-form form');if(!f)return;
    clearTimeout(delais.get(f));bornes(f);groupe(f);
    if(['offre','prestataire'].includes(e.target.name))prix(f,lire(f,'collectif-prix')[e.target.value] || {});
    calculer(f,['offre','prestataire','debut','devise'].includes(e.target.name));
  });
  async function social(url,options={}) {
    if(socialOccupe)return;
    if(!document.dispatchEvent(new Event('dossier:disponible',{cancelable:true})))return;
    socialOccupe=true;
    try {
      const r=await fetch(url,{credentials:'same-origin',cache:'no-store',...options});
      const doc=new DOMParser().parseFromString(await r.text(),'text/html');
      if(doc.querySelector('[name=password]')){location.assign(r.url);return;}
      const frais=doc.querySelector('[data-composition-collective]'),ancien=document.querySelector('[data-composition-collective]');
      if(frais && ancien){ancien.replaceWith(frais);history.replaceState(history.state,'',r.url);}
      else if(doc.querySelector('#collectif-form') && document.querySelector('#collectif-form'))document.querySelector('#collectif-form').replaceWith(doc.querySelector('#collectif-form'));
      else throw Error();
      socialModifie=options.method==='POST' && Boolean(document.querySelector('[data-collectif-form]'));initialiser();
      document.querySelector('#collectif-form .errorlist,#collectif-form input:not([type=hidden]),[data-composition-collective] summary')?.focus({preventScroll:true});
      document.dispatchEvent(new Event('navigation:actualise'));
      const rubrique = rubriqueSociale && document.getElementById(rubriqueSociale);
      const edition = frais?.querySelector('#collectif-form');
      if (rubrique && edition) {
        rubrique.open = true;
        rubrique.append(edition);
        edition.querySelector('[name=telephone], [name=courriel], input:not([type=hidden])')?.focus();
      }
    } catch(_) {const out=document.querySelector('[data-composition-collective] [data-collectif-etat]');if(out)out.textContent='Impossible de mettre à jour la composition. Vérifiez les informations affichées avant de réessayer.';}
    finally{socialOccupe=false;}
  }
  document.addEventListener('click',e=>{
    const a=e.target.closest('[data-collectif-lien]');if(!a || !document.querySelector('[data-composition-collective]') || e.button!==0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey)return;
    e.preventDefault();if(socialModifie && !confirm('Abandonner les modifications non enregistrées ?'))return;rubriqueSociale=a.dataset.collectifRubrique || rubriqueSociale;social(a.href);
  });
  document.addEventListener('submit',e=>{const f=e.target.closest('[data-collectif-form]');if(!f || !document.querySelector('[data-composition-collective]'))return;e.preventDefault();social(f.action,{method:'POST',body:new FormData(f)});});
  document.addEventListener('condition:disponible',e=>{if(socialOccupe || document.querySelector('[data-collectif-form]'))e.preventDefault();});
  window.addEventListener('beforeunload',e=>{if(socialModifie || socialOccupe){e.preventDefault();e.returnValue='';}});
  document.addEventListener('navigation:actualise',initialiser);initialiser();
})();
