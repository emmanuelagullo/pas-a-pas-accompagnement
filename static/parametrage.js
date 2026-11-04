/* Paramétrage sur place, repli HTML normal sans JavaScript. */
(() => {
  if(window.PasParametrage)return;window.PasParametrage=true;
  let occupe=false,modifie=false;
  async function charger(url,options={}) {
    if(occupe)return;occupe=true;
    const ancien=document.getElementById('parametrage');ancien?.setAttribute('aria-busy','true');
    try {
      const r=await fetch(url,{credentials:'same-origin',cache:'no-store',...options});
      const doc=new DOMParser().parseFromString(await r.text(),'text/html');
      if(doc.querySelector('[name=password]')){location.assign(r.url);return;}
      const frais=doc.getElementById('parametrage');
      if(!frais || !r.ok && ![400,409].includes(r.status))throw Error();
      const ouverts=[...ancien.querySelectorAll('details[open][id]')].map(x=>x.id);
      const formulaire=frais.querySelector('form');
      let racine=frais;
      if(formulaire && ancien.querySelector('h2')) {
        let hote=ancien.querySelector('#parametrage-editeur');
        if(!hote){hote=document.createElement('section');hote.id='parametrage-editeur';hote.className='carte operation-en-place';ancien.append(hote);}
        const titre=frais.querySelector('h1');hote.replaceChildren(...(titre?[titre]:[]),formulaire);
        formulaire.action=r.url;racine=ancien;hote.scrollIntoView({block:'nearest'});
      } else {ancien.replaceWith(frais);frais.querySelectorAll('form').forEach(f=>f.action=r.url);}
      ouverts.forEach(id=>{const d=document.getElementById(id);if(d)d.open=true;});
      modifie=options.method==='POST' && Boolean(racine.querySelector('form'));history.replaceState(history.state,'',r.url);
      const cible=racine.querySelector('.errorlist,h1');if(cible){cible.tabIndex=-1;cible.focus({preventScroll:true});}
      document.dispatchEvent(new Event('navigation:actualise'));
    } catch(_) {const e=document.getElementById('etat-parametrage');if(e)e.textContent='Opération non confirmée. Votre saisie est conservée ; vérifiez avant de recommencer.';}
    finally{occupe=false;document.getElementById('parametrage')?.removeAttribute('aria-busy');}
  }
  document.addEventListener('click',e=>{
    const a=e.target.closest('#parametrage a');if(!a || a.target || e.button!==0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || new URL(a.href).origin!==location.origin)return;
    e.preventDefault();if(modifie && !confirm('Abandonner les modifications non enregistrées ?'))return;charger(a.href);
  });
  document.addEventListener('input',e=>{if(e.target.closest('#parametrage form'))modifie=true;});
  document.addEventListener('submit',e=>{const f=e.target.closest('#parametrage form');if(!f)return;e.preventDefault();charger(f.action || location.href,{method:'POST',body:new FormData(f)});});
  window.addEventListener('beforeunload',e=>{if(modifie || occupe){e.preventDefault();e.returnValue='';}});
})();
