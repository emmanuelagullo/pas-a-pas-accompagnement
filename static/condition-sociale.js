/* Un formulaire métier à la fois ; aucun enregistrement implicite. */
(() => {
  let root = document.querySelector('[data-condition-sociale]');
  if (!root) return;
  let status = root.querySelector('[data-condition-statut]');
  let active = null, dirty = false, busy = false;
  let masques = [], declencheur = null;
  let navigationObserver = null;
  function indiquerPosition(target) {
    const person = target.closest('.condition-personne');
    document.querySelectorAll('[data-person-nav]').forEach(item => {
      item.classList.toggle('is-current', Boolean(person && item.dataset.personNav === person.id));
    });
    document.querySelectorAll('.condition-menu a').forEach(link => {
      if (link.hash === '#' + target.id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
  function observerNavigation() {
    navigationObserver?.disconnect();
    if (!window.IntersectionObserver) return;
    navigationObserver = new IntersectionObserver(entries => {
      const visible = entries.filter(entry => entry.isIntersecting).sort((a, b) => Math.abs(a.boundingClientRect.top) - Math.abs(b.boundingClientRect.top));
      if (visible.length) indiquerPosition(visible[0].target);
    }, { rootMargin: '-8% 0px -65% 0px' });
    document.querySelectorAll('.condition-groupe[id],.condition-personne[id],#condition-composition,#projet,#note-dossier,#documents-dossier,#prises,#titre-prestations,#appels-115').forEach(element => navigationObserver.observe(element));
  }
  const tell = text => { status.textContent = text; };
  const headers = { 'X-Condition-Form': '1' };
  const cleContexte = () => ['pas-a-pas-contexte', root.dataset.conditionUtilisateur, root.dataset.conditionCle, root.dataset.conditionJour].join('-');
  function memoriserContexte() {
    try { sessionStorage.setItem(cleContexte(), root.querySelector('[data-condition-contexte]').value); } catch (_) { /* stockage facultatif */ }
  }
  function choisirMode(mode) {
    root.querySelector('[data-condition-revenir]').checked=mode==='situation';
    root.querySelector('[data-condition-evolution]').checked=mode==='evolution';
  }
  function initialiserVue() {
    root.querySelector('[data-condition-evolution]').disabled=false;
    const form = root.querySelector('[data-condition-selection]');
    const select = form?.querySelector('[name="vue_sociale"]');
    const date = form?.querySelector('input[type="date"][name="date_sociale"]');
    if (!select || !date) return;
    const explicite = select.value === 'date';
    if (!explicite) date.value = select.selectedOptions[0].dataset.date || date.value;
    date.disabled = !explicite;
    const repli = form.querySelector('[data-condition-date-repli]');
    repli.value = date.value; repli.disabled = explicite;
    try {
      const contexte = root.querySelector('[data-condition-contexte]');
      if (!contexte.value) contexte.value = sessionStorage.getItem(cleContexte()) || '';
    } catch (_) { /* autocomplétion du dossier toujours disponible */ }
  }

  async function evolution(url) {
    busy = true;
    tell('Chargement de l’évolution…');
    try {
    const response = await fetch(url, { headers: { 'X-Condition-Evolution': '1' }, credentials: 'same-origin' });
    if (!response.ok) throw new Error('Évolution indisponible.');
    const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
    const content = doc.querySelector('[data-condition-trajectoire]');
    if (!content) throw new Error('Évolution indisponible ou session expirée.');
    const panel = root.querySelector('[data-condition-evolution-panel]');
    panel.replaceChildren(content); panel.hidden = false;panel.dataset.url=String(url);
    document.dispatchEvent(new Event('frises:actualise'));
    document.dispatchEvent(new Event('dossier:commandes'));
    root.querySelector('[data-condition-situation]').hidden = true;
    choisirMode('evolution');
    tell('');
    } finally { busy = false; }
  }
  function close() {
    if (active) active.replaceChildren();
    masques.forEach(element => { element.hidden = false; });
    masques = []; active = null; dirty = false;
    declencheur?.focus({ preventScroll: true }); declencheur = null;
  }
  function install(html, target) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const content = doc.querySelector('[data-condition-edition]');
    if (!content) throw new Error('Formulaire indisponible. Ouvrez le lien dans une nouvelle page.');
    target.replaceChildren(content); active = target; dirty = false;
    target.querySelector('[type="submit"]').disabled = true;
    const context = root.querySelector('[data-condition-contexte]').value;
    const champContexte = target.querySelector('[name="contexte_saisie"]');
    if (champContexte) champContexte.value = context;
    const field = target.querySelector('input:not([type="hidden"]),select,textarea');
    if (field) field.focus({ preventScroll: true });
    target.dispatchEvent(new Event('condition:form', { bubbles: true }));
  }
  document.addEventListener('click', async event => {
    const currentRoot = event.target.closest('[data-condition-sociale]');
    if (!currentRoot) return;
    root = currentRoot; status = root.querySelector('[data-condition-statut]');
    if (busy && event.target.closest('[data-condition-annuler],[data-condition-modifier],[data-condition-evolution],[data-condition-revenir]')) {
      event.preventDefault(); return;
    }
    if (event.target.closest('[data-condition-revenir]')) {
      if(dirty && !confirm('Abandonner les modifications non enregistrées ?')) {choisirMode(root.querySelector('[data-condition-evolution-panel]').hidden?'situation':'evolution');return;}
      close();
      root.querySelector('[data-condition-situation]').hidden = false;
      root.querySelector('[data-condition-evolution-panel]').hidden = true;
      choisirMode('situation');
      return;
    }
    const evolutionLink = event.target.closest('[data-condition-evolution]');
    if (evolutionLink && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
      if(evolutionLink.tagName==='A') event.preventDefault();
      if (dirty && !confirm('Abandonner les modifications non enregistrées ?')) {choisirMode(root.querySelector('[data-condition-evolution-panel]').hidden?'situation':'evolution');return;}
      close();
      try { await evolution(root.querySelector('[data-condition-evolution-panel]').dataset.url || evolutionLink.dataset.url); } catch (error) { choisirMode(root.querySelector('[data-condition-evolution-panel]').hidden?'situation':'evolution');tell(error.message); }
      return;
    }
    if (event.target.closest('[data-condition-annuler]')) {
      if (!dirty || confirm('Abandonner les modifications non enregistrées ?')) close();
      return;
    }
    const link = event.target.closest('[data-condition-modifier]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    if (busy) return;
    if (!document.dispatchEvent(new Event('dossier:disponible', { cancelable: true }))) {
      tell('Terminez ou annulez l’action de prestation avant de modifier la situation sociale.'); return;
    }
    if (dirty && !confirm('Abandonner les modifications non enregistrées avant de changer de rubrique ?')) return;
    const target = link.closest('[data-condition-groupe]').querySelector('[data-condition-formulaire]');
    close(); busy = true;
    tell('Chargement du formulaire…');
    try {
      const response = await fetch(link.href, { headers, credentials: 'same-origin' });
      const html = await response.text();
      if (!response.ok) throw new Error('Accès au formulaire refusé ou indisponible.');
      install(html, target);
      declencheur = link;
      const groupe = link.closest('[data-condition-groupe]');
      const lecture = link.closest('[data-condition-lecture]');
      const ajout = link.closest('[data-condition-ajout]');
      masques = lecture ? [lecture] : ajout ? [ajout, ...groupe.querySelectorAll(':scope > [data-condition-vide]')] : [];
      if (lecture) lecture.after(target);
      else if (ajout) ajout.before(target);
      masques.forEach(element => { element.hidden = true; });
      target.querySelector('input:not([type="hidden"]):enabled,select:enabled,textarea:enabled')?.focus({ preventScroll: true });
      tell('');
    } catch (error) { tell(error.message); }
    finally { busy = false; }
  });
  document.addEventListener('input', event => {
    if (event.target.matches('[data-condition-contexte]')) memoriserContexte();
    const form = event.target.closest('[data-condition-form]');
    if (form) { dirty = true; if (!busy) form.querySelector('[type="submit"]').disabled = false; }
  });
  document.addEventListener('change', event => {
    const form = event.target.closest('[data-evolution-selection]');
    if (!form) return;
    const mode = event.target.name;
    if (mode === 'prise') {
      // Changer de prise recalcule les raccourcis et bornes côté serveur.
      for (const name of ['vue_debut', 'vue_fin', 'debut', 'fin']) {
        form.querySelectorAll('[name="' + name + '"]').forEach(field => { field.disabled = true; });
      }
      form.requestSubmit(); return;
    }
    if (['debut', 'fin', 'beneficiaire', 'presentation_evolution'].includes(mode)) { form.requestSubmit(); return; }
    if (!['vue_debut', 'vue_fin'].includes(mode)) return;
    const borne = mode.slice(4);
    const date = form.querySelector('input[type="date"][name="' + borne + '"]');
    form.querySelector('[data-evolution-repli="' + borne + '"]')?.remove();
    date.disabled = event.target.value !== 'date';
    if (!date.disabled) { date.focus(); return; }
    date.value = form.dataset[event.target.value];
    // Le serveur recalcule les dates implicites ; le miroir sert au repli HTML.
    form.requestSubmit();
  });
  document.addEventListener('change', event => {
    const selection = event.target.closest('[data-condition-selection]');
    if (!selection) return;
    if (event.target.name === 'vue_sociale') {
      initialiserVue();
      if (event.target.value === 'date') { selection.querySelector('input[type="date"]').focus(); return; }
    }
    selection.requestSubmit();
  });
  document.addEventListener('change', event => { const form = event.target.closest('[data-condition-form]'); if (form) { dirty = true; if (!busy) form.querySelector('[type="submit"]').disabled = false; } });
  document.addEventListener('submit', async event => {
    const currentRoot = event.target.closest('[data-condition-sociale]');
    if (!currentRoot) return;
    root = currentRoot; status = root.querySelector('[data-condition-statut]');
    if (event.target.matches('[data-frise-choix]')) return;
    if (event.target.matches('[data-evolution-selection]')) {
      event.preventDefault();
      if (busy || active) {tell('Terminez ou annulez la modification en cours.');return;}
      const url = new URL(event.target.action, location.href);
      url.search = new URLSearchParams(new FormData(event.target)).toString();
      try { await evolution(url); } catch (error) { tell(error.message); }
      return;
    }
    const form = event.target.closest('[data-condition-form]');
    if (!form) {
      if (busy) { event.preventDefault(); event.target.reset(); initialiserVue(); tell('Attendez la fin de l’opération en cours.'); return; }
      if (dirty && !confirm('Abandonner la saisie non enregistrée avant de changer de vue ?')) { event.preventDefault(); event.target.reset(); initialiserVue(); }
      return;
    }
    event.preventDefault();
    if (busy) return;
    busy = true;
    const body = new FormData(form);
    if (form.querySelector('[name="contexte_saisie"]')) body.set('contexte_saisie', root.querySelector('[data-condition-contexte]').value);
    memoriserContexte();
    const controls = [...form.querySelectorAll('input:enabled,select:enabled,textarea:enabled,button:enabled'), root.querySelector('[data-condition-contexte]')];
    controls.forEach(control => { control.disabled = true; });
    const button = form.querySelector('[type="submit"]');
    button.disabled = true; tell('Enregistrement…');
    try {
      const response = await fetch(form.action, { method: 'POST', body, headers, credentials: 'same-origin' });
      if (response.headers.get('Content-Type')?.includes('application/json')) {
        const data = await response.json();
        if (!response.ok || !data.enregistre) throw new Error('Enregistrement non confirmé.');
        dirty = false;
        const context = root.querySelector('[data-condition-contexte]').value;
        const latest = await fetch(location.href, { credentials: 'same-origin' });
        if (!latest.ok) throw new Error('Enregistré, mais la vue n’a pas pu être actualisée. Rechargez la page.');
        const doc = new DOMParser().parseFromString(await latest.text(), 'text/html');
        const fresh = doc.querySelector('[data-condition-sociale]');
        if (!fresh) throw new Error('Enregistré. Rechargez la page pour consulter la nouvelle situation.');
        const anchor = active?.closest('[data-condition-groupe]')?.id;
        const evolutionUrl=active?.closest('[data-condition-evolution-panel]')?.dataset.url;
        // Recharger les valeurs et jetons après chaque écriture, sans perdre le
        // contexte d'entretien ni réutiliser un ancien formulaire périmé.
        root.innerHTML = fresh.innerHTML;
        // Les en-têtes restent non éditables, mais reflètent aussitôt une
        // correction d'identité enregistrée dans la condition sociale.
        for (const selector of ['.bd-dossier > .bd-titre', '.bd-dossier > .bd-chemin', '.condition-sommaire', '.condition-menu-mobile']) {
          const oldElement = document.querySelector(selector);
          const newElement = doc.querySelector(selector);
          if (oldElement && newElement) {
            const opened = oldElement.tagName === 'DETAILS' && oldElement.open;
            oldElement.querySelectorAll('.condition-nav-details').forEach((detail, index) => {
              const freshDetail = newElement.querySelectorAll('.condition-nav-details')[index];
              if (freshDetail) freshDetail.open = detail.open;
            });
            oldElement.replaceWith(newElement);
            if (opened) newElement.open = true;
          }
        }
        root.querySelector('[data-condition-contexte]').value = context;
        const newStatus = root.querySelector('[data-condition-statut]');
        newStatus.textContent = 'Modification enregistrée ; les autres informations sont conservées.';
        status = newStatus;
        active = null; masques = []; declencheur = null;
        initialiserVue();
        observerNavigation();
        if(evolutionUrl) {await evolution(evolutionUrl);tell('Modification enregistrée.');}
        if (anchor) {
          const groupe = document.getElementById(anchor);
          const titre = groupe?.querySelector('h4') || groupe;
          if (titre) { titre.tabIndex = -1; titre.focus({ preventScroll: true }); }
          groupe?.scrollIntoView({ block: 'nearest' });
        }
      } else {
        const html = await response.text();
        if (response.status === 403) throw new Error('Vos droits ou votre session ne permettent plus cet enregistrement. La saisie est conservée.');
        install(html, active); dirty = true; active.querySelector('[type="submit"]').disabled = false; tell('Vérifiez les erreurs. Les valeurs saisies sont conservées.');
      }
    } catch (error) { tell(error.message); }
    finally { controls.forEach(control => { control.disabled = false; }); button.disabled = false; busy = false; }
  });
  document.addEventListener('click', event => {
    const link = event.target.closest('.condition-menu a');
    if (!link) return;
    const target = document.getElementById(link.hash.slice(1));
    if (target?.closest('[data-condition-situation]')) {
      root.querySelector('[data-condition-situation]').hidden = false;
      root.querySelector('[data-condition-evolution-panel]').hidden = true;
      choisirMode('situation');
    }
    if (target) indiquerPosition(target);
    const mobile = link.closest('.condition-menu-mobile');
    if (mobile) mobile.open = false;
  });
  initialiserVue();
  observerNavigation();
  document.addEventListener('condition:disponible', event => {
    if (active || busy) {
      event.preventDefault(); tell('Terminez ou annulez la saisie de la situation sociale avant de changer de prestation.');
    }
  });
  document.addEventListener('dossier:actualise', () => {
    const contexte = root.querySelector('[data-condition-contexte]')?.value || '';
    root = document.querySelector('[data-condition-sociale]');
    if (!root) return;
    status = root.querySelector('[data-condition-statut]');
    root.querySelector('[data-condition-contexte]').value = contexte;
    active = null; dirty = false; masques = []; declencheur = null;
    initialiserVue();
    observerNavigation();
  });
  window.addEventListener('beforeunload', event => { if (dirty || busy) { event.preventDefault(); event.returnValue = ''; } });
})();
