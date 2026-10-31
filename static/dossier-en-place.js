/* Amélioration progressive : les mêmes URL et formulaires restent utilisables sans JS. */
(() => {
  'use strict';
  if (window.dossierEnPlace) return;
  window.dossierEnPlace = true;
  document.documentElement.classList.add('prestations-interactives');
  let retour = location.href, occupe = false, modifie = false, boiteActive = null;
  const etat = message => { const e = document.getElementById('etat-dossier'); if (e) e.textContent = message; };
  // Un contrôle nommé « action » peut masquer la propriété form.action.
  const actionFormulaire = form => new URL(form.getAttribute('action') || location.href, location.href).href;
  const locale = valeur => {
    const u = new URL(valeur, location.href);
    return u.origin === location.origin ? u : null;
  };
  function preparer(main, url) {
    main.querySelectorAll('script').forEach(e => e.remove());
    main.querySelectorAll('select[data-periode-dossier]').forEach(s => { s.dataset.periodePrecedente = s.value; });
    main.querySelectorAll('form').forEach(f => {
      if (!f.hasAttribute('action')) f.setAttribute('action', url);
    });
    return main;
  }
  async function charger(url, boite, options = {}) {
    if (occupe || !locale(url)) return;
    if (!document.dispatchEvent(new Event('condition:disponible', {cancelable: true}))) {
      etat('Terminez ou annulez la saisie de la situation sociale avant de changer de prestation.'); return;
    }
    occupe = true;
    etat('Chargement…');
    boite?.setAttribute('aria-busy', 'true');
    try {
      const reponse = await fetch(url, {credentials: 'same-origin', cache: 'no-store', ...options});
      const doc = new DOMParser().parseFromString(await reponse.text(), 'text/html');
      const main = doc.querySelector('main#contenu');
      if (!main || !reponse.ok && reponse.status !== 409) {
        throw new Error(options.method === 'POST'
          ? 'Enregistrement non confirmé. Consultez le dossier avant de recommencer.'
          : 'Impossible d’ouvrir cette action. Votre saisie est conservée.');
      }
      // Une session expirée se traite par le parcours normal de reconnexion.
      if (doc.querySelector('input[name="password"]')) {
        location.assign(reponse.url); return;
      }
      preparer(main, reponse.url);
      if (main.querySelector('[data-dossier-form2]')) {
        const y = scrollY;
        document.getElementById('contenu').replaceChildren(...main.childNodes);
        retour = reponse.url;
        history.replaceState(null, '', retour);
        modifie = false; boiteActive = null;
        document.dispatchEvent(new Event('dossier:actualise'));
        scrollTo(0, y);
        const selection = document.querySelector(`${new URL(retour).hash || '[data-dossier-form2]'} [data-prestation-url]:checked`);
        selection?.focus({preventScroll: true});
        const ancre = new URL(retour).hash;
        if (ancre.startsWith('#hebergement-prevu-')) {
          const prevu = document.getElementById(ancre.slice(1));
          prevu?.focus({preventScroll: true});
          prevu?.scrollIntoView({block: 'nearest'});
        }
        etat('Dossier actualisé.');
      } else if (boite) {
        const panneau = document.createElement('div');
        panneau.className = 'operation-en-place';
        const fermer = document.createElement('button');
        fermer.type = 'button'; fermer.className = 'secondaire retour-boite';
        fermer.dataset.dossierFermer = '1';
        fermer.textContent = '← Revenir à la liste';
        panneau.append(fermer, ...main.childNodes);
        // Les retours signés du serveur ferment également le panneau.
        panneau.querySelectorAll('a').forEach(a => {
          const u = locale(a.href);
          if (!a.getAttribute('href')?.startsWith('#') && u && (u.pathname === new URL(retour).pathname || /^Retour|^Annuler et revenir/.test(a.textContent.trim()))) a.dataset.dossierFermer = '1';
        });
        boite.replaceChildren(panneau);
        boiteActive = boite;
        modifie = options.method === 'POST';
        const titre = panneau.querySelector('h1');
        if (titre) { titre.tabIndex = -1; titre.focus({preventScroll: true}); }
        etat(reponse.status === 409 ? 'La saisie doit être vérifiée avant enregistrement.' : 'Action ouverte dans le dossier.');
        document.dispatchEvent(new Event('navigation:actualise'));
      } else location.assign(reponse.url);
      return true;
    } catch (erreur) {
      etat(options.method === 'POST' ? 'Enregistrement non confirmé. Votre saisie est conservée. Consultez le dossier avant de recommencer.' : 'Impossible d’ouvrir cette action. Votre saisie est conservée.');
      return false;
    } finally {
      occupe = false; boite?.removeAttribute('aria-busy');
    }
  }
  document.addEventListener('input', e => {
    if (e.target.hasAttribute?.('data-periode-dossier')) return;
    if (e.target.closest('.operation-en-place form')) modifie = true;
  });
  document.addEventListener('dossier:disponible', e => {
    if (occupe || boiteActive) {
      e.preventDefault(); etat('Terminez ou annulez l’action de prestation avant de modifier la situation sociale.');
    }
  });
  document.addEventListener('change', e => {
    const radio = e.target.closest('[data-prestation-url]');
    if (radio) {
      const precedent = radio.closest('[data-dossier-boite]').querySelector('.selectionnee [data-prestation-url]');
      const restaurer = () => { if (radio.isConnected) { radio.checked = false; if (precedent) precedent.checked = true; } };
      if (modifie || occupe) { restaurer(); etat('Terminez ou annulez la saisie en cours avant de changer de sélection.'); return; }
      charger(radio.dataset.prestationUrl, null).then(ok => { if (!ok) restaurer(); });
      return;
    }
    const select = e.target.closest('select[data-periode-dossier]');
    if (!select) return;
    const f = select.form, url = new URL(f.action);
    if (modifie && !confirm('Changer de période efface la saisie de ce formulaire. Continuer ?')) {
      select.value = select.dataset.periodePrecedente; return;
    }
    url.searchParams.set('accompagnement', select.value);
    charger(url.href, select.closest('[data-dossier-boite]'));
  });
  document.addEventListener('click', e => {
    if (e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    const fermer = e.target.closest('[data-dossier-fermer]');
    if (fermer) {
      e.preventDefault();
      if (!occupe && (!modifie || confirm('Abandonner la saisie et revenir à la liste ?'))) charger(retour, boiteActive);
      return;
    }
    const lien = e.target.closest('a');
    if (!lien || lien.getAttribute('href')?.startsWith('#') || lien.download || lien.target || !locale(lien.href)) return;
    const boite = lien.closest('[data-dossier-boite]');
    const action = lien.hasAttribute('data-dossier-action') || lien.closest('.operation-en-place');
    const selection = lien.hasAttribute('data-dossier-selection');
    if (!action && !selection) return;
    if (/\.pdf$|\/pdf\/?$/.test(new URL(lien.href).pathname)) return;
    e.preventDefault();
    if (modifie) { etat('Terminez ou annulez la saisie en cours avant de changer de sélection.'); return; }
    charger(lien.href, action ? boite : null);
  });
  document.addEventListener('submit', e => {
    const form = e.target;
    if (!form.closest('.operation-en-place')) return;
    if (form.method.toLowerCase() !== 'post') {
      e.preventDefault();
      const url = new URL(actionFormulaire(form));
      for (const [cle, valeur] of new FormData(form)) { if (cle !== 'csrfmiddlewaretoken') url.searchParams.set(cle, valeur); }
      charger(url.href, form.closest('[data-dossier-boite]'));
      return;
    }
    e.preventDefault();
    if (occupe) return;
    const donnees = new FormData(form);
    if (e.submitter?.name) donnees.append(e.submitter.name, e.submitter.value);
    modifie = true;
    const controles = [...form.elements].map(controle => [controle, controle.disabled]);
    controles.forEach(([controle]) => { controle.disabled = true; });
    charger(actionFormulaire(form), form.closest('[data-dossier-boite]'), {method: 'POST', body: donnees})
      .finally(() => controles.forEach(([controle, disabled]) => { controle.disabled = disabled; }));
  });
  window.addEventListener('beforeunload', e => {
    if (modifie || occupe) { e.preventDefault(); e.returnValue = ''; }
  });
})();
