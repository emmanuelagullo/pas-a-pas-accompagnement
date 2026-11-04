if (!window.PasCollectifInitialise) {
window.PasCollectifInitialise = true;
/* Formulaire commun : même validation serveur ; repli HTML sans JavaScript. */
document.addEventListener('input', event => {
  if (event.target.name?.startsWith('prix_')) event.target.dataset.personnalise = '1';
});
document.addEventListener('change', event => {
  if (event.target.name !== 'prestataire') return;
  const form = event.target.closest('form');
  const node = form?.querySelector('#collectif-prix');
  if (!node) return;
  const prix = JSON.parse(node.textContent)[event.target.value] || {};
  form.querySelectorAll('input[name^="prix_"]').forEach(input => {
    if (!input.dataset.personnalise) input.value = prix[input.name.slice(5)] ?? '';
  });
});
document.addEventListener('submit', async event => {
  const form = event.target.closest('[data-collectif-form]');
  if (!form) return;
  event.preventDefault();
  const button = form.querySelector('button');
  button.disabled = true;
  try {
    const response = await fetch(form.action, {method: 'POST', body: new FormData(form), credentials: 'same-origin'});
    if (response.redirected) { window.location.assign(response.url); return; }
    const doc = new DOMParser().parseFromString(await response.text(), 'text/html');
    const panel = doc.querySelector('#collectif-form');
    if (panel) {
      const current = form.closest('#collectif-form');
      current.replaceWith(panel);
      panel.querySelector('form')?.setAttribute('data-collectif-form', '');
      panel.querySelector('.errorlist,input,select,textarea')?.focus();
    } else throw new Error('Réponse inattendue.');
  } catch (_) {
    let message = form.querySelector('[data-collectif-erreur]');
    if (!message) { message = document.createElement('p'); message.dataset.collectifErreur = ''; message.setAttribute('role','alert'); form.prepend(message); }
    message.textContent = 'Enregistrement non confirmé. Rechargez la page avant de réessayer.';
  } finally { button.disabled = false; }
});

}
