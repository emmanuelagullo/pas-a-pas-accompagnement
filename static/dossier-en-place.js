/* NAV7 : une consultation par carte, le cadre de Form3 reste en place. */
(() => {
  if (window.dossierEnPlace) return;
  window.dossierEnPlace = true;
  document.documentElement.classList.add('prestations-interactives');
  let occupe = false, modifie = false, dernierDeclencheur;
  const etat = texte => { const e=document.getElementById('etat-dossier'); if(e)e.textContent=texte; };
  const hote = (cle, racine=document) => [...racine.querySelectorAll('[data-prestation-hote]')].find(e=>e.dataset.prestationHote===cle);
  const ouverts = () => [...document.querySelectorAll('[data-prestation-hote]')].filter(e=>e.childElementCount);
  const cibleUrl = url => new URL(url,location.href).searchParams.get('prestation') || '';
  const actionFormulaire = f => new URL(f.getAttribute('action') || location.href,location.href).href;
  function ouvrirParents(e) { for(let p=e?.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true; }
  function synchroniser(doc) {
    // Garder les autres cartes et le cadre en place, y compris leur identité DOM.
    doc.querySelectorAll('[data-prestation-liste]').forEach(liste => {
      const ancienne=[...document.querySelectorAll('[data-prestation-liste]')].find(e=>e.dataset.prestationListe===liste.dataset.prestationListe);
      if(!ancienne)return;
      const cartes=[...liste.querySelectorAll(':scope > [data-prestation-carte]')];
      const archive=ancienne.closest('[data-prestation-archive]');if(archive)archive.hidden=!cartes.length;
      ancienne.querySelectorAll(':scope > li:not([data-prestation-carte])').forEach(e=>e.remove());
      cartes.forEach(carte=>{
        let actuelle=[...ancienne.children].find(e=>e.dataset.prestationCarte===carte.dataset.prestationCarte);
        if(!actuelle){ancienne.append(carte.cloneNode(true));return;}
        actuelle.className=carte.className;
        const commandes=actuelle.querySelector(':scope > [data-hebergement-actions]'), recentes=carte.querySelector(':scope > [data-hebergement-actions]');
        if(commandes && recentes)commandes.replaceWith(recentes.cloneNode(true));
        const detail=actuelle.querySelector(':scope > .hebergement-individuels > summary'), nouveauDetail=carte.querySelector(':scope > .hebergement-individuels > summary');
        if(detail && nouveauDetail)detail.replaceChildren(...[...nouveauDetail.childNodes].map(e=>e.cloneNode(true)));
        const frise=actuelle.querySelector(':scope > .frise-slot'), fraiche=carte.querySelector(':scope > .frise-slot');
        if(frise && fraiche){const deplies=[...frise.querySelectorAll('details[open]')].map(e=>e.id);frise.replaceChildren(...[...fraiche.childNodes].map(e=>e.cloneNode(true)));deplies.forEach(id=>{const e=document.getElementById(id);if(e)e.open=true;});}
        const resume=actuelle.querySelector(':scope > a.prestation-consulter'), nouveau=carte.querySelector(':scope > a.prestation-consulter');
        if(resume && nouveau){resume.innerHTML=nouveau.innerHTML;resume.href=nouveau.href;}
        const radio=actuelle.querySelector('[data-prestation-url]'), frais=carte.querySelector('[data-prestation-url]');
        if(radio && frais){radio.checked=frais.checked;radio.dataset.prestationUrl=frais.dataset.prestationUrl;}
      });
      [...ancienne.querySelectorAll(':scope > [data-prestation-carte]')].forEach(e=>{
        if(!cartes.some(c=>c.dataset.prestationCarte===e.dataset.prestationCarte))e.remove();
      });
      if(!cartes.length)ancienne.replaceChildren(...[...liste.childNodes].map(e=>e.cloneNode(true)));
    });
    doc.querySelectorAll('[data-dossier-boite]').forEach(section=>{
      const actuelle=[...document.querySelectorAll('[data-dossier-boite]')].find(e=>e.dataset.dossierBoite===section.dataset.dossierBoite);
      if(!actuelle)return;
      const choix=actuelle.querySelector('[data-hebergement-commandes]'), nouveauChoix=section.querySelector('[data-hebergement-commandes]');
      if(choix && nouveauChoix){const ouvert=choix.querySelector('details')?.open;const frais=nouveauChoix.cloneNode(true);if(ouvert && frais.querySelector('details'))frais.querySelector('details').open=true;choix.replaceWith(frais);return;}
      const actions=actuelle.querySelector('.actions-directes'), nouvelles=section.querySelector('.actions-directes');
      if(actions && nouvelles)actions.replaceWith(nouvelles.cloneNode(true));
      else if(actions)actions.remove();
      else if(nouvelles)actuelle.append(nouvelles.cloneNode(true));
    });
  }
  async function charger(valeur, options={}) {
    if(occupe)return;
    const url=new URL(valeur,location.href);
    if(url.origin!==location.origin)return;
    if(!document.dispatchEvent(new Event('condition:disponible',{cancelable:true}))){etat('Terminez ou annulez la saisie sociale en cours.');return;}
    occupe=true;etat('Chargement…');
    const cle=cibleUrl(url), ancien=ouverts()[0], ancienneCle=ancien?.dataset.prestationHote;
    (ancien || hote(cle))?.setAttribute('aria-busy','true');
    try {
      const reponse=await fetch(url,{credentials:'same-origin',cache:'no-store',...options});
      if (reponse.ok && options.body?.get?.('nouvelle_prise') && new URL(reponse.url).pathname !== url.pathname) {
        modifie = false;
        occupe = false;
        location.assign(reponse.url);
        return;
      }
      const doc=new DOMParser().parseFromString(await reponse.text(),'text/html');
      if(doc.querySelector('input[name=password]')){location.assign(reponse.url);return;}
      if(!doc.querySelector('[data-dossier-form2]') || (!reponse.ok && ![400,409].includes(reponse.status)))throw new Error();
      const ouverte=cibleUrl(reponse.url), source=ouverte && hote(ouverte,doc);
      synchroniser(doc);
      if (options.method === 'POST') {
        const entete = ['titre', 'etat', 'actions'].map(nom => '[data-prise-entete="' + nom + '"]');
        entete.push('.fil-ariane [aria-current="page"]');
        for (const selecteur of entete) {
          const actuel = document.querySelector(selecteur), recu = doc.querySelector(selecteur);
          if (actuel && recu && !actuel.isEqualNode(recu)) actuel.replaceWith(recu.cloneNode(true));
        }
        document.title = doc.title;
      }
      let destination=source && hote(ouverte);
      if(source && !destination && ouverte.startsWith('hebergement:')){destination=source.cloneNode(false);document.querySelector('#hebergement > .boite-entete').after(destination);}
      if(source && !destination)throw new Error();
      ouverts().forEach(e=>e.replaceChildren());
      if(source){
        if(!destination)throw new Error();
        destination.replaceChildren(...[...source.childNodes].map(e=>e.cloneNode(true)));
        ouvrirParents(destination);
        modifie=options.method==='POST' && Boolean(destination.querySelector('[data-prestation-form]'));
        const cible=destination.querySelector('.errorlist,.erreurs-formulaire,h4,h1,form') || destination;
        cible.tabIndex=-1;cible.focus({preventScroll:true});cible.scrollIntoView({block:'nearest'});
      } else {
        modifie=false;
        const retourFocus=dernierDeclencheur?.isConnected ? dernierDeclencheur : hote(ancienneCle)?.closest('[data-prestation-carte]')?.querySelector('a.prestation-consulter');
        retourFocus?.focus({preventScroll:true}); retourFocus?.scrollIntoView({block:'nearest'});
      }
      const adresse=new URL(reponse.url);adresse.hash=ouverte ? 'prestation-'+ouverte.replace(':','-') : url.hash;
      history.replaceState(history.state,'',adresse);
      document.dispatchEvent(new Event('navigation:actualise'));
      if(options.method==='POST')document.dispatchEvent(new Event('frises:actualise'));
      etat(options.method==='POST' && !modifie ? 'Modification enregistrée.' : '');
    } catch(_) {
      etat(options.method==='POST' ? 'Enregistrement non confirmé. Votre saisie est conservée ; vérifiez avant de recommencer.' : 'Impossible d’ouvrir cette prestation. La page est conservée.');
    } finally {occupe=false; document.querySelectorAll('[data-prestation-hote][aria-busy]').forEach(e=>e.removeAttribute('aria-busy'));}
  }
  const formulairesSuivis = new WeakSet();
  function preparerValidation() {
    for (const form of document.querySelectorAll('[data-enregistrer-si-modifie]')) {
      if (formulairesSuivis.has(form)) continue;
      formulairesSuivis.add(form);
      const etatFormulaire = () => JSON.stringify([...new FormData(form)]);
      const initial = etatFormulaire();
      const actualiser = () => {
        const bouton = form.querySelector('button[type="submit"]:not([name]):not([hidden])');
        if (bouton) bouton.disabled = etatFormulaire() === initial;
      };
      form.addEventListener('prestation:validation', actualiser);
      form.addEventListener('input', () => queueMicrotask(actualiser));
      form.addEventListener('change', () => queueMicrotask(actualiser));
      actualiser();
    }
  }
  document.addEventListener('navigation:actualise', () => queueMicrotask(preparerValidation));
  queueMicrotask(preparerValidation);
  document.addEventListener('input',e=>{if(e.target.closest('[data-prestation-form]'))modifie=true;});
  document.addEventListener('dossier:disponible',e=>{
    if(occupe || ouverts().some(h=>h.querySelector('[data-prestation-form]'))){e.preventDefault();etat('Terminez ou annulez l’action de prestation avant de modifier la situation sociale.');}
  });
  document.addEventListener('click',e=>{
    if(e.target.closest('[data-prestation-imprimer]')){window.print();return;}
    if(e.button!==0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey)return;
    const lien=e.target.closest('a');
    if(!lien || lien.target || lien.download || !lien.matches('[data-prestation-lien],[data-prestation-fermer]'))return;
    e.preventDefault();
    const fermer=lien.matches('[data-prestation-fermer]') || lien.matches('[data-prestation-annuler]');
    if(modifie && (!fermer || !confirm('Abandonner les modifications non enregistrées ?'))){etat('Terminez ou annulez la saisie en cours.');return;}
    if(lien.matches('[data-prestation-fermer]')){
      const zone=lien.closest('[data-prestation-hote]'), carte=zone?.closest('[data-prestation-carte]');
      zone?.replaceChildren();modifie=false;history.replaceState(history.state,'',lien.href);
      const retour=dernierDeclencheur?.isConnected ? dernierDeclencheur : carte?.querySelector('a.prestation-consulter');
      retour?.focus({preventScroll:true});retour?.scrollIntoView({block:'nearest'});
      document.dispatchEvent(new Event('navigation:actualise'));return;
    }
    if(!lien.closest('[data-prestation-panneau]'))dernierDeclencheur=lien;
    charger(lien.href);
  });
  document.addEventListener('change',e=>{
    const radio=e.target.closest('[data-prestation-url]');if(!radio)return;
    if(modifie || occupe){radio.checked=false;const precedent=radio.closest('[data-dossier-boite]').querySelector('.selectionnee [data-prestation-url]');if(precedent)precedent.checked=true;etat('Terminez ou annulez la saisie en cours.');return;}
    charger(radio.dataset.prestationUrl);
  });
  const verifications = new WeakMap();
  const temporisations = new WeakMap();
  const saisiesProgrammees = new WeakMap();
  const ouverturesVerifiees = new WeakSet();
  function verifierOuvertures() {
    for (const form of document.querySelectorAll('[data-prestation-verifier-a-ouverture] [data-prestation-form]')) {
      if (ouverturesVerifiees.has(form)) continue;
      ouverturesVerifiees.add(form);
      verifierPeriode(form);
    }
  }
  document.addEventListener('navigation:actualise', () => queueMicrotask(verifierOuvertures));
  queueMicrotask(verifierOuvertures);
  const champsPeriode = '[name=debut], [name=fin], [name=fin_prevue], [name=arrivee], [name=admission], [data-periode-duree], [name=calcul_periode], [data-arrivee-effectuee]';
  function programmerVerification({target: champ}) {
    if (!champ.matches?.(champsPeriode)) return;
    const form = champ.form;
    if (!form?.matches('[data-prestation-form]') || !form.closest('[data-prestation-verifiable]')) return;
    // La sortie du champ peut émettre change après un input déjà traité.
    // Garder alors le bouton sous le pointeur et la vérification en cours.
    const saisie = JSON.stringify([...new FormData(form)]);
    if (saisiesProgrammees.get(form) === saisie) return;
    saisiesProgrammees.set(form, saisie);
    verifications.get(form)?.abort();
    const commande = form.querySelector('[data-validation-prestation]');
    if (commande?.querySelector('[name=confirmation_fin], [name=nouvelle_prise]')) {
      const enregistrer = commande.querySelector('[data-prestation-soumission-implicite]');
      if (enregistrer) {
        enregistrer.removeAttribute('data-prestation-soumission-implicite');
        enregistrer.hidden = false;
        commande.replaceChildren(enregistrer);
      }
    }
    if (!temporisations.has(form)) temporisations.set(form, window.PasRecherche.temporiser(() => verifierPeriode(form)));
    temporisations.get(form)();
  }
  document.addEventListener('input', programmerVerification);
  document.addEventListener('change', programmerVerification);
  async function verifierPeriode(form) {
    const commandes = form?.querySelector('[data-validation-prestation]');
    if (occupe || !form.isConnected) return;
    verifications.get(form)?.abort();
    const controle = new AbortController();
    verifications.set(form, controle);
    const donnees = new FormData(form);
    try {
      const reponse = await fetch(actionFormulaire(form), {
        method: 'POST', body: donnees, credentials: 'same-origin',
        headers: {'X-Verifier-Prestation': '1'}, signal: controle.signal,
      });
      if (!reponse.ok || !reponse.headers.get('Content-Type')?.startsWith('application/json')) return;
      const resultat = await reponse.json();
      if (controle.signal.aborted || !form.isConnected || occupe) return;
      for (const nom of ['debut', 'fin', 'fin_prevue', 'arrivee', 'admission', 'duree']) {
        if (String(form.elements.namedItem(nom)?.value || '') !== String(donnees.get(nom) || '')) return;
      }
      if (commandes && resultat.commandes && commandes.innerHTML.trim() !== resultat.commandes.trim()) {
        const actif = document.activeElement;
        const commandeActive = commandes.contains(actif);
        commandes.innerHTML = resultat.commandes;
        form.dispatchEvent(new Event('prestation:validation'));
        if (commandeActive) {
          const boutons = [...commandes.querySelectorAll('button:not([hidden])')];
          (boutons.find(bouton => bouton.name === actif.name) || boutons[0])?.focus({preventScroll: true});
        }
      }
      for (const nom of ['debut', 'fin', 'fin_prevue', 'arrivee', 'admission', 'duree']) {
        const entree = form.elements.namedItem(nom);
        if (!entree?.id) continue;
        const identifiant = entree.id + '-verification';
        const descriptions = (entree.getAttribute('aria-describedby') || '').split(/\s+/).filter(id => id && id !== identifiant);
        let message = document.getElementById(identifiant);
        if (!message) {
          message = document.createElement('p');
          message.id = identifiant;
          message.className = 'errorlist';
          message.setAttribute('aria-live', 'polite');
          entree.after(message);
        }
        const erreurs = resultat.erreurs[nom] || [];
        message.textContent = erreurs.join(' ');
        message.hidden = !erreurs.length;
        if (erreurs.length) descriptions.push(identifiant);
        if (descriptions.length) entree.setAttribute('aria-describedby', descriptions.join(' '));
        else entree.removeAttribute('aria-describedby');
      }
    } catch (_) {
      // L’enregistrement normal reste disponible si la vérification échoue.
    }
  }
  document.addEventListener('submit',e=>{
    const form=e.target;if(!form.matches('[data-prestation-form]'))return;
    e.preventDefault();if(occupe)return;
    if(form.method.toLowerCase()!=='post' && modifie){etat('Terminez ou annulez la saisie en cours avant de rechercher.');return;}
    const url=new URL(actionFormulaire(form)), data=new FormData(form);
    if(e.submitter?.name)data.append(e.submitter.name,e.submitter.value);
    if(form.method.toLowerCase()==='post')charger(url,{method:'POST',body:data});
    else {for(const k of new Set(data.keys()))url.searchParams.delete(k);for(const [k,v] of data)url.searchParams.append(k,v);charger(url);}
  });
  window.addEventListener('beforeunload',e=>{if(modifie || occupe){e.preventDefault();e.returnValue='';}});
})();
