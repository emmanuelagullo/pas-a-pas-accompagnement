/* Aperçu indicatif ; le montant conservé est recalculé en Decimal côté serveur. */
(() => {
  const form = document.getElementById('calcul-financement');
  if (!form) return;
  function actualiser() {
    const devise = form.querySelector('[name=devise]').value;
    form.querySelectorAll('.total-ligne').forEach(sortie => {
      const bloc = sortie.closest('fieldset');
      const lire = suffixe => bloc.querySelector(`[name$="-${suffixe}"]`).value.trim().replace(',', '.');
      const q = lire('quantite'), p = lire('prix');
      const total = Number(q) * Number(p);
      sortie.textContent = q && p && Number.isFinite(total) ? `Aperçu : ${total.toLocaleString('fr-FR', {minimumFractionDigits: 2, maximumFractionDigits: 2})} ${devise}. Arrondi définitif à l’enregistrement.` : '';
    });
  }
  form.addEventListener('input', actualiser);
  actualiser();
})();
