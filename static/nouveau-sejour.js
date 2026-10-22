/* Le serveur applique le même choix sans JavaScript. Écoute aussi les formulaires en place. */
(() => {
  if (window.nouveauSejourInstalle) return;
  window.nouveauSejourInstalle = true;
  document.addEventListener('change', event => {
    const choix = event.target.closest('[data-arrivee-effectuee]');
    if (!choix) return;
    choix.form.querySelectorAll('[data-champ-arrivee]').forEach(champ => {
      champ.hidden = !choix.checked;
      champ.querySelectorAll('input, select, textarea').forEach(controle => { controle.disabled = !choix.checked; });
    });
  });
})();
