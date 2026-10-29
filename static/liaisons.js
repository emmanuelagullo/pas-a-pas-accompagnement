/* Cahier intégré : même endpoint et mêmes contrôles qu'en pleine page. */
(() => {
  if (window.pasLiaisons) return;
  window.pasLiaisons = true;
  const states = new WeakMap(), initialized = new WeakSet();
  const state = root => {
    if (!states.has(root)) states.set(root, {seq: 0, controller: null});
    return states.get(root);
  };
  const focus = root => {
    const key = root.querySelector('[data-liaison-focus]')?.dataset.liaisonFocus;
    const target = key && document.getElementById('liaison-' + key);
    if (target && root.contains(target)) target.scrollIntoView({block: 'center'});
  };
  async function load(root, raw, form = null) {
    const s = state(root); if (s.posting) return;
    const seq = ++s.seq;
    s.controller?.abort(); s.controller = new AbortController();
    const url = new URL(raw, location.href); url.searchParams.set('lia_fragment', '1');
    const draft = root.querySelector('[data-liaisons-message]');
    const saved = draft && !form ? ['contenu', 'contenu_document', 'date_fait'].map(n => [n, draft.elements.namedItem(n)?.value]) : [];
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
      root.innerHTML = html;
      for (const [name, value] of saved) {
        const input = root.querySelector('[data-liaisons-message]')?.elements.namedItem(name);
        if (input && value !== undefined) input.value = value;
        if (name === 'contenu' && value) root.querySelector('[data-liaisons-message]').dataset.dirty = '1';
      }
      if (saved.some(([n,v]) => n === 'contenu' && v)) root.querySelector('.liaison-rediger')?.setAttribute('open', '');
      root.dataset.liaisonsLoaded = '1'; focus(root);
    } catch (e) {
      if (e.name !== 'AbortError' && s.seq === seq) {
        let p = root.querySelector('[data-liaisons-erreur]');
        if (!p) {p = document.createElement('p'); p.dataset.liaisonsErreur = '1'; p.setAttribute('role', 'alert'); root.prepend(p);}
        p.textContent = 'Chargement non confirmé. Votre saisie est conservée ; vous pouvez réessayer.';
      }
    } finally {
      if (s.seq === seq) root.removeAttribute('aria-busy');
      if (form) {form.inert = false; root.inert = false; s.posting = false;}
    }
  }
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
  window.addEventListener('beforeunload', e => { if (document.querySelector('[data-liaisons-message][data-dirty="1"]')) {e.preventDefault(); e.returnValue = ''; } });
  document.addEventListener('submit', e => {
    const form = e.target;
    if (!form.matches('[data-liaisons-filtres],[data-liaisons-message]')) return;
    if (e.defaultPrevented) return;
    e.preventDefault();
    const root = form.closest('.liaisons-contenu');
    if (form.matches('[data-liaisons-message]')) load(root, form.action, form);
    else {
      const url = new URL(form.action); url.search = new URLSearchParams(new FormData(form));
      load(root, url);
    }
  });
  document.addEventListener('change', e => {
    const form = e.target.closest('[data-liaisons-filtres]');
    if (e.target.matches('[data-liaison-borne]') && e.target.value) form.elements.namedItem(e.target.dataset.liaisonBorne).value = e.target.value;
    if (form) form.requestSubmit();
  });
  document.addEventListener('click', e => {
    const link = e.target.closest('[data-liaisons-page]');
    if (link && !e.ctrlKey && !e.metaKey && !e.shiftKey && !e.altKey) {e.preventDefault(); load(link.closest('.liaisons-contenu'), link.href);}
  });
  const start = () => {init(); document.querySelectorAll('.liaisons-contenu').forEach(focus); new MutationObserver(init).observe(document.body, {childList: true, subtree: true});};
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
