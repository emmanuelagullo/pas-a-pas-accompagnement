/* Calculs civils UTC : pas de décalage selon fuseau ou changement d'heure. */
(() => {
  if (window.periodesSaisieInstallees) return;
  window.periodesSaisieInstallees = true;
  const jour = valeur => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(valeur)) return null;
    const d = new Date(valeur + 'T00:00:00Z');
    return Number.isFinite(d.getTime()) && d.toISOString().slice(0,10) === valeur ? d.getTime()/86400000 : null;
  };
  const iso = nombre => {
    const d = new Date(nombre*86400000);
    if (!Number.isFinite(d.getTime())) return '';
    const v = d.toISOString().slice(0,10);
    return /^\d{4}-\d{2}-\d{2}$/.test(v) && v.slice(0,4) !== '0000' ? v : '';
  };
  const initialiser = () => {
  for (const form of document.querySelectorAll('form')) {
    if (form.dataset.periodePreparee) continue;
    const debut = form.querySelector('[data-periode-debut]');
    const fin = form.querySelector('[data-periode-fin]');
    const duree = form.querySelector('[data-periode-duree]');
    const modes = [...form.querySelectorAll('input[data-periode-calcul]')];
    if (!debut || !fin || !duree || debut.disabled || fin.disabled) continue;
    form.dataset.periodePreparee = '1';
    const mode = valeur => { for (const m of modes) m.checked = m.value === valeur; };
    const depuisDates = () => {
      const d = jour(debut.value), f = jour(fin.value);
      duree.value = d !== null && f !== null && f>d ? String(f-d) : '';
      mode('dates');
    };
    const depuisDuree = () => {
      const d = jour(debut.value), n = Number(duree.value);
      if (d !== null && Number.isInteger(n) && n>0) fin.value = iso(d+n);
      else if (!duree.value) fin.value = '';
      mode('duree');
    };
    fin.addEventListener('input', depuisDates);
    fin.addEventListener('change', depuisDates);
    duree.addEventListener('input', depuisDuree);
    debut.addEventListener('input', () => modes.some(m => m.checked && m.value === 'duree') ? depuisDuree() : depuisDates());
    for (const m of modes) m.addEventListener('change', () => m.value === 'duree' ? depuisDuree() : depuisDates());
    // Ne jamais écraser une saisie invalide après un retour serveur.
    if (!form.querySelector('.errorlist') && !modes.some(m => m.checked && m.value === 'duree')) depuisDates();
  }
  };
  document.addEventListener('condition:form', initialiser);
  document.addEventListener('navigation:actualise', initialiser);
  initialiser();
})();
