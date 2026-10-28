/* Une préférence serveur, des fragments graphiques ; aucune saisie remplacée. */
(() => {
  let occupe = false;
  const ouverts = new Set();
  const boutons = () => document.querySelectorAll('[data-frise-choix] button').forEach(b => b.hidden = true);
  boutons();
  document.addEventListener('dossier:actualise', boutons);
  document.addEventListener('change', async event => {
    const box = event.target;
    const form = box.closest('[data-frise-choix]');
    if (!form || box.name !== 'actif') return;
    if (occupe || document.getElementById('resultats-dossiers')?.inert || !document.dispatchEvent(new Event('condition:disponible', {cancelable:true})) ||
        !document.dispatchEvent(new Event('dossier:disponible', {cancelable:true}))) {
      box.checked = !box.checked; return;
    }
    occupe = true;
    const data = new FormData(form);
    box.disabled = true;
    try {
      const r = await fetch(form.action, {method:'POST',body:data,credentials:'same-origin',headers:{'X-Frises-Pref':'1'}});
      if (!r.ok) throw new Error('Préférence non enregistrée');
      const page = await fetch(location.href, {credentials:'same-origin',cache:'no-store'});
      if (!page.ok || page.redirected) { location.assign(page.url); return; }
      const doc = new DOMParser().parseFromString(await page.text(), 'text/html');
      const nouveaux = new Map([...doc.querySelectorAll('[data-frise-slot]')].map(n => [n.dataset.friseSlot,n]));
      const anciens = [...document.querySelectorAll('[data-frise-slot]')];
      // Un changement concurrent de la liste exige sa relecture entière.
      if (anciens.length !== nouveaux.size || anciens.some(n => !nouveaux.has(n.dataset.friseSlot))) {
        location.reload(); return;
      }
      document.querySelectorAll('.frise-details[open]').forEach(d => ouverts.add(d.id));
      const y = scrollY;
      anciens.forEach(n => { n.replaceChildren(...nouveaux.get(n.dataset.friseSlot).childNodes); });
      document.querySelectorAll('.frise-details').forEach(d => { if(ouverts.has(d.id)) d.open = true; });
      document.querySelectorAll('.resultats-dossiers').forEach(l => l.classList.toggle('avec-frises',box.checked));
      scrollTo(0,y);
    } catch (_) {
      form.querySelector('button').hidden = false;
    } finally {
      box.disabled = false; occupe = false;
    }
  });
  document.addEventListener('toggle', e => {
    if(e.target.matches('.frise-details') && !e.target.open) ouverts.delete(e.target.id);
  }, true);
  document.addEventListener('focusin', e => { if(e.target.matches('[data-frise-repere]')) e.target.removeAttribute('data-ferme'); });
  document.addEventListener('pointerover', e => { e.target.closest?.('[data-frise-repere]')?.removeAttribute('data-ferme'); });
  document.addEventListener('keydown', e => {
    if(e.key === 'Escape' && e.target.matches('[data-frise-repere]')) e.target.setAttribute('data-ferme','1');
  });
})();
