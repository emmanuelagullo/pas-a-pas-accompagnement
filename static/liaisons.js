/* Cahier intégré : même endpoint et mêmes contrôles qu'en pleine page. */
(() => {
  if (window.pasLiaisons) return;
  window.pasLiaisons = true;
  const vivants = new Set(), states = new WeakMap(), initialized = new WeakSet();
  const state = root => {
    if (!states.has(root)) {const s={seq:0,controller:null,drafts:new Map()};states.set(root,s);vivants.add(s);}
    return states.get(root);
  };
  const focus = root => {
    const key = root.querySelector('[data-liaison-focus]')?.dataset.liaisonFocus;
    const target = key && document.getElementById('liaison-' + key);
    if (target && root.contains(target)) target.scrollIntoView({block: 'center'});
  };
  async function load(root, raw, form = null, abandonner = false) {
    const s = state(root); if (s.posting) return;
    const seq = ++s.seq;
    s.controller?.abort(); s.controller = new AbortController();
    const url = new URL(raw, location.href); url.searchParams.set('lia_fragment', '1');
    const draft = root.querySelector('[data-liaisons-message]');
    const publication = busy => root.querySelectorAll('[data-liaisons-message] button[type=submit]').forEach(b => {b.disabled = busy;});
    if (!form) publication(true);
    const garder = () => {
      const f = root.querySelector('[data-liaisons-message]'); if (!f) return;
      const valeurs = ['contenu','contenu_document','date_fait'].map(n => [n,f.elements.namedItem(n)?.value]);
      const mentions = [...f.querySelectorAll('[name=lia_mentions]')].map(x => ({token:x.value,label:x.closest('[data-mention-label]').dataset.mentionLabel}));
      s.drafts.set(f.dataset.liaisonParent || '', {valeurs,mentions});
    };
    if (!abandonner) garder();
    const options = {credentials: 'same-origin', signal: s.controller.signal};
    if (form) {options.method = 'POST'; options.body = new FormData(form); form.inert = true; s.posting = true; root.inert = true;}
    root.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch(url, options);
      if (s.seq !== seq) return;
      if ([401, 403, 404].includes(response.status) || new URL(response.url).pathname !== url.pathname) {
        const own = draft?.elements.namedItem('contenu')?.value;
        root.textContent = 'Ce cahier n’est plus accessible. Rechargez la page pour vérifier votre accès.';
        if (own) {const p = document.createElement('p'); p.textContent = 'Votre brouillon non confirmé, à conserver avant de recharger :'; const ta = document.createElement('textarea'); ta.readOnly = true; ta.value = own; root.append(p, ta);}
        return;
      }
      if (![200, 400, 409].includes(response.status)) throw new Error('chargement');
      const html = await response.text();
      if (s.seq !== seq) return;
      if (!form && !abandonner) garder();
      else if (form && response.ok) s.drafts.delete(form.dataset.liaisonParent || '');
      const active = document.activeElement;
      const caret = active?.name === 'lia_q' && root.contains(active) ? [active.selectionStart,active.selectionEnd] : null;
      root.innerHTML = html;
      const nouveau = root.querySelector('[data-liaisons-message]');
      if(form && !response.ok && nouveau)nouveau.dataset.dirty='1';
      const sauvegarde = nouveau && s.drafts.get(nouveau.dataset.liaisonParent || '');
      if (sauvegarde && (!form || form.dataset.liaisonParent !== nouveau.dataset.liaisonParent)) {
        for (const [name,value] of sauvegarde.valeurs) {const champ=nouveau.elements.namedItem(name);if(champ && value !== undefined) champ.value=value;}
        if (nouveau.elements.namedItem('contenu')?.value) {nouveau.dataset.dirty='1';nouveau.closest('details')?.setAttribute('open','');}
        for (const m of sauvegarde.mentions) ajouterMention(nouveau.querySelector('[data-mentions-selection]'),m.token,m.label);
      }
      if (caret) {const q=root.querySelector('[name=lia_q]');q?.focus();q?.setSelectionRange(...caret);}
      root.dataset.liaisonsLoaded = '1'; focus(root);
    } catch (e) {
      if (e.name !== 'AbortError' && s.seq === seq) {
        let p = root.querySelector('[data-liaisons-erreur]');
        if (!p) {p = document.createElement('p'); p.dataset.liaisonsErreur = '1'; p.setAttribute('role', 'alert'); root.prepend(p);}
        p.textContent = 'Chargement non confirmé. Votre saisie est conservée ; vous pouvez réessayer.';
      }
    } finally {
      if (s.seq === seq) {root.removeAttribute('aria-busy');publication(false);}
      if (form) {form.inert = false; root.inert = false; s.posting = false;}
    }
  }
  function ajouterMention(selection, token, label) {
    if ([...selection.querySelectorAll('input')].some(x => x.value === token)) return;
    const l = document.createElement('span'), c = document.createElement('input'), b=document.createElement('button');
    c.type = 'hidden'; c.name = 'lia_mentions'; c.value = token;
    b.type='button';b.dataset.mentionRetirer='';b.textContent='Retirer la notification';
    l.dataset.mentionLabel = label; l.append(c, document.createTextNode(label + ' sera notifié '),b); selection.append(l);
  }
  function nettoyerMentions(form) {
    const texte=form.elements.namedItem('contenu')?.value || '';
    form.querySelectorAll('[data-mention-label]').forEach(x => {
      const nom=x.dataset.mentionLabel;
      let depuis=0, present=false, i;
      while ((i=texte.indexOf(nom,depuis))>=0) {if(!/[A-Za-z0-9_À-ÿ]/.test(texte[i+nom.length] || '')){present=true;break;}depuis=i+nom.length;}
      if(!present)x.remove();
    });
  }

  const recherches = new WeakMap();
  function positionMention(form) {
    const ta = form.elements.namedItem('contenu');
    if (ta.hidden) return window.PasTextes?.mention(ta);
    if (ta.selectionStart !== ta.selectionEnd) return null;
    const trouve = ta.value.slice(0, ta.selectionStart).match(/(?:^|\s)@([^@\n]{0,60})$/);
    return trouve ? {from: ta.selectionStart - trouve[1].length - 1, to: ta.selectionStart, query: trouve[1]} : null;
  }
  function proposerMentions(form) {
    const box = form.querySelector('[data-mentions-propositions]');
    if (!box) return;
    const ancien = recherches.get(form); if (ancien) {clearTimeout(ancien.timer); ancien.controller.abort();}
    const position = positionMention(form), controller = new AbortController(), etat = {controller, position, actif: 0};
    recherches.set(form, etat); box.hidden = true; box.replaceChildren();
    if (!position) return;
    etat.timer = setTimeout(async () => {
      try {
        const url = new URL(form.dataset.mentionsUrl, location.href); url.searchParams.set('q', position.query.trim());
        const response = await fetch(url, {credentials: 'same-origin', signal: controller.signal});
        if (recherches.get(form) !== etat) return;
        if ([401,403,404].includes(response.status)) {load(form.closest('.liaisons-contenu'), form.action); return;}
        if (!response.ok) throw new Error('mentions');
        const data = await response.json(); if (recherches.get(form) !== etat || !form.isConnected) return;
        box.setAttribute('role', 'listbox'); box.setAttribute('aria-label', 'Collègues à mentionner');
        for (const candidat of data.collegues) {
          const b = document.createElement('button'); b.type = 'button'; b.textContent = candidat.label;
          b.setAttribute('role', 'option'); b.setAttribute('aria-selected', String(!box.children.length));
          b.addEventListener('mousedown', e => e.preventDefault());
          b.addEventListener('click', () => {
            const ta = form.elements.namedItem('contenu'); let ok;
            if (ta.hidden) ok = window.PasTextes.insererMention(ta, position, candidat.label);
            else if (ta.value.slice(position.from, position.to) === '@' + position.query) {
              ta.setRangeText('@' + candidat.label + ' ', position.from, position.to, 'end'); ta.focus(); ta.dispatchEvent(new Event('input', {bubbles:true})); ok = true;
            }
            if (ok) ajouterMention(form.querySelector('[data-mentions-selection]'), candidat.jeton, '@' + candidat.label);
            controller.abort(); box.hidden = true; recherches.delete(form);
          });
          box.append(b);
        }
        if (!box.children.length) {box.removeAttribute('role'); box.textContent = 'Aucun collègue autorisé proposé pour cette recherche.';}
        const rect = position.rect || form.elements.namedItem('contenu').getBoundingClientRect();
        box.style.left = Math.max(8,Math.min(rect.left,innerWidth-330))+'px';
        box.style.top = Math.max(8,Math.min(rect.bottom+5,innerHeight-200))+'px';
        box.hidden = false;
      } catch(e) {if (e.name !== 'AbortError' && recherches.get(form) === etat) {box.removeAttribute('role'); box.textContent = 'Propositions indisponibles ; aucun collègue ne sera ajouté automatiquement.'; box.hidden = false;}}
    }, 180);
  }
  document.addEventListener('input', e => {
    const form = e.target.closest('[data-liaisons-message]');
    if (form && (e.target.name === 'contenu' || e.target.closest('.ProseMirror'))) {nettoyerMentions(form);proposerMentions(form);}
  });
  document.addEventListener('keydown', e => {
    const form = e.target.closest('[data-liaisons-message]'), etat = form && recherches.get(form), box = form?.querySelector('[data-mentions-propositions]');
    if (!etat || !box || box.hidden) return;
    const options = [...box.querySelectorAll('button')];
    if (e.key === 'Escape') {box.hidden = true; etat.controller.abort(); recherches.delete(form); e.preventDefault();}
    if (options.length && ['ArrowDown','ArrowUp','Enter'].includes(e.key)) {
      e.preventDefault(); e.stopPropagation();
      if (e.key === 'Enter') options[etat.actif]?.click();
      else {etat.actif = (etat.actif + (e.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length; options.forEach((b,i) => b.setAttribute('aria-selected',String(i === etat.actif)));}
    }
  }, true);
  function init() {
    document.querySelectorAll('[data-liaisons-url]').forEach(details => {
      if (initialized.has(details)) return;
      initialized.add(details);
      const open = () => {
        const root = details.querySelector('.liaisons-contenu');
        if (details.open && !root.dataset.liaisonsLoaded) load(root, details.dataset.liaisonsUrl);
      };
      details.addEventListener('toggle', open); open();
    });
  }
  document.addEventListener('input', e => { const f = e.target.closest('[data-liaisons-message]'); if (f) f.dataset.dirty = '1'; });
  window.addEventListener('beforeunload', e => { if (document.querySelector('[data-liaisons-message][data-dirty="1"]') || [...vivants].some(s => [...s.drafts.values()].some(d => d.valeurs.some(([n,v]) => n==='contenu' && v)))) {e.preventDefault(); e.returnValue = ''; } });
  document.addEventListener('submit', e => {
    const form = e.target;
    if (!form.matches('[data-liaisons-filtres],[data-liaisons-message]')) return;
    if (e.defaultPrevented) return;
    e.preventDefault();
    form._rechercheDifferee?.annuler();
    const root = form.closest('.liaisons-contenu');
    if (form.matches('[data-liaisons-message]')) load(root, form.action, form);
    else {
      const url = new URL(form.action); url.search = new URLSearchParams(new FormData(form));
      load(root, url);
    }
  });
  document.addEventListener('input', e => {
    const form=e.target.closest('[data-liaisons-filtres]');
    if (form && e.target.name==='lia_q') {
      form._rechercheDifferee ||= window.PasRecherche.temporiser(() => {if(form.isConnected)form.requestSubmit();});
      form._rechercheDifferee();
    }
  });
  document.addEventListener('change', e => {
    const form = e.target.closest('[data-liaisons-filtres]');
    if (e.target.matches('[data-liaison-borne]') && e.target.value) form.elements.namedItem(e.target.dataset.liaisonBorne).value = e.target.value;
    if (form) form.requestSubmit();
  });
  document.addEventListener('click', e => {
    const annuler=e.target.closest('[data-liaison-annuler]');
    if(annuler && !e.ctrlKey && !e.metaKey && !e.shiftKey && !e.altKey){
      e.preventDefault();
      const form=annuler.closest('form'),root=form.closest('.liaisons-contenu'),s=state(root);
      if(s.posting)return;
      if(form.dataset.dirty==='1' && !confirm('Abandonner les modifications non enregistrées ?'))return;
      const recherche=recherches.get(form);if(recherche){clearTimeout(recherche.timer);recherche.controller.abort();recherches.delete(form);}
      s.drafts.delete(form.dataset.liaisonParent || '');delete form.dataset.dirty;
      load(root,annuler.href,null,true);
      return;
    }
    const retirer=e.target.closest('[data-mention-retirer]');if(retirer){retirer.closest('[data-mention-label]').remove();return;}
    const ecrire=e.target.closest('[data-liaison-ecrire]');
    if(ecrire){const root=ecrire.closest('.liaisons-contenu');if(root.querySelector('[data-liaison-parent]:not([data-liaison-parent=""])')){load(root,ecrire.dataset.nouveauUrl).then(() => {const d=root.querySelector('.liaison-rediger');if(d)d.open=true;});return;}const details=root.querySelector('.liaison-rediger');if(details){details.open=true;details.querySelector('.ProseMirror,textarea')?.focus();details.scrollIntoView({block:'nearest'});}return;}
    const link = e.target.closest('[data-liaisons-page]');
    if (link && !e.ctrlKey && !e.metaKey && !e.shiftKey && !e.altKey) {e.preventDefault(); load(link.closest('.liaisons-contenu'), link.href);}
  });
  const start = () => {document.documentElement.classList.add('pas-liaisons-js');init(); document.querySelectorAll('.liaisons-contenu').forEach(focus); new MutationObserver(init).observe(document.body, {childList: true, subtree: true});};
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
