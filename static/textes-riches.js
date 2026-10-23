/* Chargement local à la première zone d’édition, y compris après remplacement. */
(() => {
  if (window.chargeurTextesRiches) return;
  window.chargeurTextesRiches = true;
  const script = document.querySelector('script[data-editeur-source]');
  const source = script?.dataset.editeurSource;
  let chargement = null, planifie = false;
  const actualiser = () => {
    planifie = false;
    window.PasTextes?.nettoyer();
    if (!document.querySelector('textarea[data-texte-riche]')) return;
    if (!chargement) chargement = new Promise((resolve, reject) => {
      const s = document.createElement('script'); s.src = source;
      s.onload = resolve; s.onerror = () => reject(new Error('Éditeur indisponible'));
      document.head.append(s);
    });
    chargement.then(() => window.PasTextes.initialiser()).catch(() => {
      // Les textarea simples restent utilisables ; les textes enrichis restent protégés.
      document.querySelectorAll('textarea[data-texte-riche][readonly]').forEach(ta => {
        if (ta.dataset.erreurEditeur) return;
        ta.dataset.erreurEditeur = '1';
        const p = document.createElement('p'); p.setAttribute('role', 'status');
        p.textContent = 'L’éditeur n’a pas pu être chargé. Le texte enrichi reste consultable ; rechargez la page pour le modifier.';
        ta.before(p);
      });
    });
  };
  const planifier = () => {if (!planifie) {planifie = true; queueMicrotask(actualiser);}};
  new MutationObserver(changes => {
    // La frappe dans l’éditeur ne relance pas le parcours de tous les champs.
    if (changes.some(c => [...c.addedNodes, ...c.removedNodes].some(n => n.nodeType === 1 &&
      (n.matches?.('textarea[data-texte-riche], .edition-texte') || n.querySelector?.('textarea[data-texte-riche], .edition-texte'))))) planifier();
  }).observe(document.body, {childList: true, subtree: true});
  document.addEventListener('htmx:load', planifier);
  document.addEventListener('htmx:afterSwap', planifier);
  document.addEventListener('htmx:beforeCleanupElement', e => {
    // Le nettoyage effectif intervient après retrait du DOM, via l'observateur.
    planifier();
  });
  actualiser();
})();
