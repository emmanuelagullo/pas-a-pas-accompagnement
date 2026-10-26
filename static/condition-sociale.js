/* Un formulaire métier à la fois ; aucun enregistrement implicite. */
(() => {
  const root = document.querySelector('[data-condition-sociale]');
  if (!root) return;
  let status = root.querySelector('[data-condition-statut]');
  let active = null, dirty = false, busy = false;
  const tell = text => { status.textContent = text; };
  const headers = { 'X-Condition-Form': '1' };
  async function evolution(url) {
    const response = await fetch(url, { headers: { 'X-Condition-Evolution': '1' }, credentials: 'same-origin' });
    if (!response.ok) throw new Error('Évolution indisponible.');
    const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
    const content = doc.querySelector('[data-condition-trajectoire]');
    if (!content) throw new Error('Évolution indisponible ou session expirée.');
    const panel = root.querySelector('[data-condition-evolution-panel]');
    panel.replaceChildren(content); panel.hidden = false;
    root.querySelector('[data-condition-situation]').hidden = true;
    root.querySelector('[data-condition-revenir]').setAttribute('aria-pressed', 'false');
  }
  function close() { if (active) active.replaceChildren(); active = null; dirty = false; }
  function install(html, target) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const content = doc.querySelector('[data-condition-edition]');
    if (!content) throw new Error('Formulaire indisponible. Ouvrez le lien dans une nouvelle page.');
    target.replaceChildren(content); active = target; dirty = false;
    const context = root.querySelector('[data-condition-contexte]').value;
    const motif = target.querySelector('[name="motif"]');
    if (context && motif && !motif.value) motif.value = context;
    const field = target.querySelector('input:not([type="hidden"]),select,textarea');
    if (field) field.focus({ preventScroll: true });
    target.dispatchEvent(new Event('condition:form', { bubbles: true }));
  }
  root.addEventListener('click', async event => {
    if (busy && event.target.closest('[data-condition-annuler],[data-condition-modifier],[data-condition-evolution],[data-condition-revenir]')) {
      event.preventDefault(); return;
    }
    if (event.target.closest('[data-condition-revenir]')) {
      root.querySelector('[data-condition-situation]').hidden = false;
      root.querySelector('[data-condition-evolution-panel]').hidden = true;
      root.querySelector('[data-condition-revenir]').setAttribute('aria-pressed', 'true');
      return;
    }
    const evolutionLink = event.target.closest('[data-condition-evolution]');
    if (evolutionLink && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
      event.preventDefault();
      if (dirty && !confirm('Abandonner les modifications non enregistrées ?')) return;
      close();
      try { await evolution(evolutionLink.href); } catch (error) { tell(error.message); }
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
    if (dirty && !confirm('Abandonner les modifications non enregistrées avant de changer de rubrique ?')) return;
    if (link.hasAttribute('data-condition-correction') && !confirm('Corriger cette information sur sa période existante ? Les autres prises en charge utilisant cette période refléteront aussi la correction.')) return;
    const target = link.closest('[data-condition-groupe]').querySelector('[data-condition-formulaire]');
    close(); busy = true;
    tell('Chargement du formulaire…');
    try {
      const response = await fetch(link.href, { headers, credentials: 'same-origin' });
      const html = await response.text();
      if (!response.ok) throw new Error('Accès au formulaire refusé ou indisponible.');
      install(html, target); tell('');
    } catch (error) { tell(error.message); }
    finally { busy = false; }
  });
  root.addEventListener('input', event => { if (event.target.closest('[data-condition-form]')) dirty = true; });
  root.addEventListener('change', event => { if (event.target.closest('[data-condition-form]')) dirty = true; });
  root.addEventListener('submit', async event => {
    if (event.target.closest('[data-condition-trajectoire]')) {
      event.preventDefault();
      const url = new URL(event.target.action, location.href);
      url.search = new URLSearchParams(new FormData(event.target)).toString();
      try { await evolution(url); } catch (error) { tell(error.message); }
      return;
    }
    const form = event.target.closest('[data-condition-form]');
    if (!form) {
      if (dirty && !confirm('Abandonner la saisie non enregistrée avant de changer de vue ?')) event.preventDefault();
      return;
    }
    event.preventDefault();
    if (busy) return;
    busy = true;
    const body = new FormData(form);
    const controls = [...form.querySelectorAll('input:enabled,select:enabled,textarea:enabled,button:enabled')];
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
        // Recharger les valeurs et jetons après chaque écriture, sans perdre le
        // contexte d'entretien ni réutiliser un ancien formulaire périmé.
        root.innerHTML = fresh.innerHTML;
        root.querySelector('[data-condition-contexte]').value = context;
        const newStatus = root.querySelector('[data-condition-statut]');
        newStatus.textContent = 'Modification enregistrée ; les autres informations sont conservées.';
        status = newStatus;
        active = null;
        if (anchor) document.getElementById(anchor)?.scrollIntoView({ block: 'nearest' });
      } else {
        const html = await response.text();
        if (response.status === 403) throw new Error('Vos droits ou votre session ne permettent plus cet enregistrement. La saisie est conservée.');
        install(html, active); dirty = true; tell('Vérifiez les erreurs. Les valeurs saisies sont conservées.');
      }
    } catch (error) { tell(error.message); }
    finally { controls.forEach(control => { control.disabled = false; }); button.disabled = false; busy = false; }
  });
  document.addEventListener('click', event => {
    const link = event.target.closest('.condition-sommaire a');
    if (!link) return;
    document.querySelectorAll('.condition-sommaire a').forEach(a => a.removeAttribute('aria-current'));
    link.setAttribute('aria-current', 'location');
  });
  window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
})();
