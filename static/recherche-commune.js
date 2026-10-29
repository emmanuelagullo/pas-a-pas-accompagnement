/* Même temporisation pour les recherches améliorées ; le GET reste autonome. */
window.PasRecherche = {
  delai: 250,
  temporiser(faire, delai = 250) {
    let timer;
    const lancer = (...args) => {clearTimeout(timer); timer = setTimeout(() => faire(...args), delai);};
    lancer.annuler = () => clearTimeout(timer);
    return lancer;
  }
};
