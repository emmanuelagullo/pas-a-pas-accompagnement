/* Calculs civils UTC : pas de décalage selon fuseau ou changement d'heure. */
(() => {
  if (window.periodesSaisieInstallees) return;
  window.periodesSaisieInstallees = true;
  const jour = valeur => {
    valeur = valeur.replace(/^(\d{2})\/(\d{2})\/(\d{4})$/, '$3-$2-$1');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(valeur) || valeur.startsWith('0000-')) return null;
    const d = new Date(valeur + 'T00:00:00Z');
    return Number.isFinite(d.getTime()) && d.toISOString().slice(0,10) === valeur ? d.getTime()/86400000 : null;
  };
  const iso = nombre => {
    const d = new Date(nombre*86400000);
    if (!Number.isFinite(d.getTime())) return '';
    const v = d.toISOString().slice(0,10);
    return /^\d{4}-\d{2}-\d{2}$/.test(v) && v.slice(0,4) !== '0000' ? v : '';
  };
  const enFrancais = valeur => valeur.replace(/^(\d{4})-(\d{2})-(\d{2})$/, '$3/$2/$1');

  function equiperDate(champ) {
    if (champ.disabled || champ.readOnly || champ.closest('.saisie-date')) return;
    const groupe = document.createElement('span');
    groupe.className = 'saisie-date';
    champ.before(groupe);
    groupe.append(champ);
    const nom = champ.labels?.[0]?.textContent.trim() || 'Date';
    const pas = document.createElement('span');
    pas.className = 'saisie-date-pas';
    groupe.append(pas);
    const bouton = (parent, texte, libelle) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'saisie-date-commande';
      b.textContent = texte;
      b.setAttribute('aria-label', nom + ' — ' + libelle);
      b.title = libelle;
      parent.append(b);
      return b;
    };
    const suivant = bouton(pas, '▴', 'Jour suivant');
    const precedent = bouton(pas, '▾', 'Jour précédent');
    const ouvrir = bouton(groupe, '', 'Ouvrir le calendrier');
    ouvrir.classList.add('saisie-date-ouvrir');
    ouvrir.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4m8-4v4"/></svg>';
    const calendrier = document.createElement('input');
    calendrier.type = 'date';
    calendrier.tabIndex = -1;
    calendrier.className = 'saisie-date-native';
    calendrier.setAttribute('aria-label', nom + ' — Calendrier');
    groupe.append(calendrier);

    const actualiser = () => {
      const date = jour(champ.value);
      suivant.disabled = date === null || !iso(date + 1);
      precedent.disabled = date === null || !iso(date - 1);
    };
    const choisir = valeur => {
      champ.value = enFrancais(valeur);
      champ.dispatchEvent(new Event('input', {bubbles: true}));
    };
    const decaler = pas => {
      const date = jour(champ.value);
      if (date !== null && iso(date + pas)) choisir(iso(date + pas));
    };
    groupe.addEventListener('date:actualisee', actualiser);
    champ.addEventListener('input', actualiser);
    champ.addEventListener('change', actualiser);
    champ.addEventListener('keydown', e => {
      if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown' || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
      if (jour(champ.value) === null) return;
      e.preventDefault();
      decaler(e.key === 'ArrowUp' ? 1 : -1);
    });
    suivant.addEventListener('click', () => decaler(1));
    precedent.addEventListener('click', () => decaler(-1));
    ouvrir.addEventListener('click', () => {
      const date = jour(champ.value);
      calendrier.value = date === null ? '' : iso(date);
      try {
        calendrier.showPicker();
      } catch {
        calendrier.classList.add('saisie-date-native-visible');
        calendrier.tabIndex = 0;
        calendrier.focus();
      }
    });
    calendrier.addEventListener('change', () => {
      if (calendrier.value) choisir(calendrier.value);
      calendrier.classList.remove('saisie-date-native-visible');
      calendrier.tabIndex = -1;
      champ.focus();
    });
    calendrier.addEventListener('blur', () => {
      calendrier.classList.remove('saisie-date-native-visible');
      calendrier.tabIndex = -1;
    });
    actualiser();
  }

  const initialiser = () => {
  document.querySelectorAll('input[data-date-fr]').forEach(equiperDate);
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
      if (d !== null && Number.isInteger(n) && n>0)  {
        const valeur = iso(d+n);
        fin.value = fin.hasAttribute('data-date-fr') ? enFrancais(valeur) : valeur;
      }
      else if (!duree.value) fin.value = '';
      fin.closest('.saisie-date')?.dispatchEvent(new Event('date:actualisee'));
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
  document.addEventListener('date:disponible', event => equiperDate(event.target));
  document.addEventListener('condition:form', initialiser);
  document.addEventListener('navigation:actualise', initialiser);
  initialiser();
})();
