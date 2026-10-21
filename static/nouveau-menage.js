/* Le serveur valide aussi sans JavaScript ; les champs inactifs restent sans effet. */
(() => {
  const choix = document.getElementById('id_premiere_personne');
  if (!choix) return;
  function afficher() {
    const nouvelle = choix.value === 'nouvelle';
    for (const nom of ['personne', 'designation', 'prenom']) {
      const champ = document.getElementById('id_' + nom);
      if (!champ) continue;
      const actif = nom === 'personne' ? !nouvelle : nouvelle;
      champ.disabled = !actif;
      // Chaque champ est rendu par Django dans son paragraphe avec son aide et ses erreurs.
      champ.closest('p').hidden = !actif;
      champ.required = actif && nom !== 'prenom';
    }
  }
  choix.addEventListener('change', afficher);
  afficher();
})();
