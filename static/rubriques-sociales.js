/* NAV3 : uniquement des identifiants de rubrique et des booléens en session. */
(() => {
  if (!document.querySelector('[data-condition-sociale]')) return;
  const scopes = new Map(), initialises = new WeakSet(), aSauver = new Set();
  let frame = 0;
  const racine = () => document.querySelector('[data-condition-sociale]');
  const rubriques = () => [...racine().querySelectorAll('[data-condition-repli]')];
  const cle = () => ['pas-a-pas-rubriques-v1', racine().dataset.conditionUtilisateur, racine().dataset.conditionCle].join('-');
  function choix() {
    const key = cle();
    if (!scopes.has(key)) {
      const etat = Object.create(null);
      try {
        const lu = JSON.parse(sessionStorage.getItem(key) || '{}');
        if (lu && typeof lu === 'object' && !Array.isArray(lu)) {
          Object.entries(lu).forEach(([nom, valeur]) => {
            if (nom.length <= 200 && typeof valeur === 'boolean') etat[nom] = valeur;
          });
        }
      } catch (_) { /* La page reste utilisable sans stockage navigateur. */ }
      scopes.set(key, etat);
    }
    return scopes.get(key);
  }
  function enregistrer() {
    frame = 0;
    aSauver.forEach(key => {
      try { sessionStorage.setItem(key, JSON.stringify(scopes.get(key))); }
      catch (_) { /* Les choix restent en mémoire pendant cette page. */ }
    });
    aSauver.clear();
  }
  function memoriser(detail) {
    choix()[(detail.dataset.conditionRepli || 'volet-social')] = detail.open;
    aSauver.add(cle());
    if (!frame) frame = requestAnimationFrame(enregistrer);
  }
  function avertir() {
    racine().querySelector('[data-condition-statut]').textContent =
      'Rubrique en cours de saisie laissée ouverte. Terminez ou annulez la saisie pour la replier.';
  }
  function ouvrirParents(element) {
    for (let parent = element; parent && racine().contains(parent); parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
  }
  function ancre() {
    try { return document.getElementById(decodeURIComponent(location.hash.slice(1))); }
    catch (_) { return null; }
  }
  function initialiser() {
    if (!racine()) return;
    const etat = choix();
    [racine(), ...rubriques()].forEach(detail => {
      if (initialises.has(detail)) return;
      detail.open = etat[(detail.dataset.conditionRepli || 'volet-social')] === true;
      if (detail.querySelector('[data-condition-form],.errorlist')) detail.open = true;
      initialises.add(detail);
    });
    racine().querySelector('[data-condition-repli-commandes]').hidden = false;
  }
  document.addEventListener('click', event => {
    const bouton = event.target.closest('[data-condition-tout]');
    if (bouton) {
      const ouvrir = bouton.dataset.conditionTout === 'ouvrir';
      let conserve = false;
      rubriques().forEach(detail => {
        if (!ouvrir && detail.querySelector('[data-condition-form]')) {
          conserve = true; detail.open = true;
        } else detail.open = ouvrir;
        memoriser(detail);
      });
      if (conserve) avertir();
      document.dispatchEvent(new Event('condition:depliements'));
      return;
    }
    const resume = event.target.closest('summary');
    const detail = resume?.parentElement;
    if (detail?.matches('[data-condition-repli][open], [data-condition-volet][open]') && detail.querySelector('[data-condition-form]')) {
      event.preventDefault(); avertir(); return;
    }
    // Inclut les liens du résumé d'erreurs, sans intercepter une navigation externe.
    const lien = event.target.closest('a[href]');
    if (lien) {
      const url = new URL(lien.href, location.href);
      if (url.hash && url.origin === location.origin && url.pathname === location.pathname && url.search === location.search) {
        let cible;
        try { cible = document.getElementById(decodeURIComponent(url.hash.slice(1))); } catch (_) {}
        if (cible && racine()?.contains(cible)) ouvrirParents(cible);
      }
    }
  }, true);
  document.addEventListener('toggle', event => {
    const detail = event.target;
    if (!detail.matches('[data-condition-repli], [data-condition-volet]') || !racine()?.contains(detail)) return;
    if (!detail.open && detail.querySelector('[data-condition-form]')) {
      detail.open = true; avertir();
    }
    memoriser(detail);
    document.dispatchEvent(new Event('condition:depliements'));
  }, true);
  ['navigation:actualise', 'dossier:actualise', 'condition:vue', 'condition:form'].forEach(nom =>
    document.addEventListener(nom, initialiser));
  window.addEventListener('pagehide', enregistrer);
  window.addEventListener('hashchange', () => {
    const cible = ancre();
    if (cible && racine()?.contains(cible)) ouvrirParents(cible);
  });
  initialiser();
  document.addEventListener('DOMContentLoaded', () => {
    const cible = ancre();
    if (cible && racine()?.contains(cible)) {
      ouvrirParents(cible);
      cible.scrollIntoView({block: 'start', behavior: 'instant'});
    }
  }, {once: true});
})();
