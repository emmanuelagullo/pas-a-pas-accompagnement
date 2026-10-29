/* Amélioration progressive : même GET et mêmes permissions que sans JavaScript. */
(() => {
  const form = document.getElementById('recherche-dossiers');
  if (!form) return;
  const results = document.getElementById('resultats-dossiers');
  const status = document.getElementById('recherche-etat');
  let timer, controller, sequence = 0;
  const nouveau = form.querySelector?.('[data-nouveau-dossier]');
  function adapterCreation() {
    if (nouveau) nouveau.disabled = nouveau.dataset[form.elements.mode.value] !== 'oui';
  }
  adapterCreation();
  function invalidate() {
    sequence++;
    results.inert = true;
    nouveau?.classList.add('secondaire');
    status.textContent = 'Recherche en cours…';
    clearTimeout(timer);
    if (controller) controller.abort();
  }
  async function update(version) {
    controller = new AbortController();
    const query = new URLSearchParams(new FormData(form));
    const visible = new URL(form.action);
    visible.search = query.toString();
    query.set('fragment', '1');
    const url = new URL(form.action);
    url.search = query.toString();
    results.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch(url, {signal: controller.signal, credentials: 'same-origin'});
      if (!response.ok || response.redirected) throw new Error('Recherche indisponible');
      const html = await response.text();
      if (version !== sequence) return;
      results.innerHTML = html;
      if (nouveau) nouveau.classList.toggle('secondaire', results.querySelector('[data-creation-suggeree]')?.dataset.creationSuggeree !== 'oui');
      results.inert = false;
      history.replaceState(null, '', visible);
      document.dispatchEvent(new Event('dossier:actualise'));
      status.textContent = 'Résultats actualisés.';
    } catch (error) {
      if (version === sequence && error.name !== 'AbortError') {
        status.textContent = 'Recherche non actualisée. Utilisez le bouton Rechercher.';
      }
    } finally {
      if (version === sequence) results.removeAttribute('aria-busy');
    }
  }
  form.addEventListener('input', () => {
    adapterCreation();
    invalidate();
    const version = sequence;
    timer = setTimeout(() => update(version), 250);
  });
  form.addEventListener('submit', () => invalidate());
})();
