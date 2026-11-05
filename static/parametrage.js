/* Même emplacement de lecture et d'édition ; repli HTML sans JavaScript. */
(() => {
  if(window.PasParametrage)return;window.PasParametrage=true;
  let occupe=false,modifie=false,blocActif='';
  function collecte(){document.querySelectorAll('.collecte-table tr').forEach(ligne=>{const portee=ligne.querySelector('select[name$="_portee"]'), population=ligne.querySelector('select[name$="_population"]');if(portee && population)population.disabled=!['personne','deux'].includes(portee.value);});}
  collecte();
  function dire(texte, bloc) {
    const hote = bloc?.querySelector('[data-parametrage-hote]');
    if (!hote) {
      const etat = document.getElementById('etat-parametrage');
      if (etat) etat.textContent = texte;
      return;
    }
    let etat = hote.querySelector('[data-etat-parametrage]');
    if (!etat) {
      etat = document.createElement('p');
      etat.dataset.etatParametrage = '';
      etat.setAttribute('role', 'status');
      hote.prepend(etat);
    }
    etat.textContent = texte;
  }
  function liberer(){blocActif='';modifie=false;}
  async function charger(url,options={},bloc=null) {
    if(occupe)return;occupe=true;
    const ancien=document.getElementById('parametrage');ancien?.setAttribute('aria-busy','true');
    const courant = bloc || (blocActif && document.getElementById(blocActif));
    if (bloc) dire('Ouverture du formulaire…', bloc);
    try {
      const r=await fetch(url,{credentials:'same-origin',cache:'no-store',...options});
      const doc=new DOMParser().parseFromString(await r.text(),'text/html');
      if(doc.querySelector('[name=password]')){location.assign(r.url);return;}
      const frais=doc.getElementById('parametrage');
      if(!frais){if(r.redirected && r.ok){location.assign(r.url);return;}throw Error();}
      if(!r.ok && ![400,409].includes(r.status))throw Error();
      const formulaire=frais.querySelector('form');
      const actuel = courant;
      let cible;
      if(formulaire && actuel){
        blocActif=actuel.id;
        const hote=actuel.querySelector('[data-parametrage-hote]');if(!hote)throw Error();
        const titre = frais.querySelector('h1')?.textContent.trim();
        const rubrique = actuel.querySelector('h2, h3')?.textContent.trim();
        if (titre && (!rubrique || !titre.startsWith(rubrique))) {
          const sousTitre = document.createElement('h4');
          sousTitre.textContent = titre;
          hote.replaceChildren(sousTitre, formulaire);
        } else {
          hote.replaceChildren(formulaire);
        }
        formulaire.action=r.url;hote.id='parametrage-editeur';hote.classList.add('operation-en-place');
        actuel.querySelectorAll('[data-parametrage-modifier]').forEach(e=>e.hidden=true);
        actuel.querySelectorAll('[data-parametrage-hote] a').forEach(e=>e.dataset.parametrageAnnuler='');
        modifie=options.method==='POST';
        cible=hote.querySelector('.errorlist,input:not([type=hidden]),select,textarea,h4');
      }else{
        const remplace=actuel && doc.getElementById(actuel.id);
        if(remplace){
          actuel.replaceWith(remplace);
          const composition = ancien.querySelector('[data-parametrage-composition]');
          const compositionFraiche = frais.querySelector('[data-parametrage-composition]');
          if (composition && compositionFraiche &&
              composition.dataset.parametrageComposition !== compositionFraiche.dataset.parametrageComposition) {
            composition.replaceWith(compositionFraiche);
          }
          cible=remplace.querySelector('[data-parametrage-modifier],h2,h3');
        }else{ancien.replaceWith(frais);cible=frais.querySelector('h1');}
        liberer();
      }
      if (formulaire && actuel) {
        history.replaceState(history.state, '', '#' + blocActif);
      } else {
        const destination = new URL(r.url);
        if (actuel && doc.getElementById(actuel.id)) destination.hash = actuel.id;
        history.replaceState(history.state, '', destination);
      }
      if(cible){if(!cible.matches('input,select,textarea,a,button'))cible.tabIndex=-1;cible.focus({preventScroll:true});cible.scrollIntoView({block:'nearest'});}
      collecte();
      document.dispatchEvent(new Event('navigation:actualise'));
      dire(options.method==='POST' && !modifie ? 'Modification enregistrée.' : '');
    }catch(_){
      dire(bloc ? 'Impossible d’ouvrir le formulaire.' : 'Opération non confirmée. Votre saisie est conservée.', courant);
    }
    finally{occupe=false;document.getElementById('parametrage')?.removeAttribute('aria-busy');}
  }
  document.addEventListener('click',e=>{
    const a=e.target.closest('#parametrage a');if(!a || a.target || e.button!==0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || new URL(a.href).origin!==location.origin)return;
    if (a.getAttribute('href')?.startsWith('#') || e.defaultPrevented) return;
    if (!a.matches('[data-parametrage-modifier], [data-parametrage-annuler]')) return;
    if(occupe){e.preventDefault();return;}
    const bloc=a.matches('[data-parametrage-modifier]')?a.closest('[data-parametrage-bloc]'):null;
    if(a.matches('[data-parametrage-modifier]') && !bloc)return; // Repli complet pour les autres vues.
    e.preventDefault();if(modifie && !confirm('Abandonner les modifications non enregistrées ?'))return;
    if(blocActif && bloc && bloc.id!==blocActif){dire('Enregistrez ou annulez le formulaire ouvert.', bloc);return;}
    charger(a.href,{},bloc);
  });
  document.addEventListener('input',e=>{if(e.target.closest('#parametrage-editeur form'))modifie=true;});
  document.addEventListener('change',e=>{if(e.target.closest('#parametrage-editeur form'))modifie=true;collecte();});
  document.addEventListener('submit',e=>{
    const f=e.target.closest('#parametrage-editeur form');if(!f)return;
    e.preventDefault();const body=new FormData(f);
    if(e.submitter?.name)body.set(e.submitter.name,e.submitter.value);
    charger(f.action || location.href,{method:'POST',body});
  });
  window.addEventListener('beforeunload',e=>{if(modifie || occupe){e.preventDefault();e.returnValue='';}});
})();
