/* Une seule soumission du rapport ; aucune autorisation décidée ici. */
(() => {
  const form = document.querySelector('[data-criteres-statistiques]');
  if (!form) return;
  const rapport = form.querySelector('[name="rapport"]');
  const portee = form.querySelector('[name="portee_statistiques"]');
  const dossiers = form.querySelector('[data-dossiers-statistiques] fieldset');
  function adapter() {
    const compatible = ['synthese', 'hebergement', 'repas', 'mensuel'].includes(rapport.value);
    if (portee) {
      if (!compatible) portee.value = '';
      portee.disabled = !compatible;
      portee.closest('[data-portee-statistiques]').hidden = !compatible;
    }
    if (dossiers) {
      dossiers.disabled = !!(portee && !portee.disabled && portee.value);
      dossiers.closest('[data-dossiers-statistiques]').hidden = dossiers.disabled;
    }
  }
  rapport.addEventListener('change', adapter);
  portee?.addEventListener('change', adapter);
  adapter();
})();
