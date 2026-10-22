// Prépositionner le lien dans les deux zones défilantes (application et coque).
// Garder un vrai clic Playwright : visibilité, stabilité et absence d'obstacle.
module.exports = async function cliquerLienPwa(lien) {
  try {
    await lien.waitFor({state:'visible'});
    await lien.evaluate(element => element.scrollIntoView({block:'center', inline:'nearest', behavior:'instant'}));
    await lien.click();
  } catch (erreur) {
    // Le journal distingue un lien hors écran d'un obstacle ou d'un problème de navigation.
    try {
      console.error('Lien PWA :', await lien.evaluate(element => {
        const rect = e => {
          const r = e.getBoundingClientRect();
          return {x:r.x, y:r.y, largeur:r.width, hauteur:r.height};
        };
        const vue = element.ownerDocument.defaultView;
        return {chemin:new URL(element.href).pathname, lien:rect(element),
          fenetre:{largeur:vue.innerWidth, hauteur:vue.innerHeight, defilement:vue.scrollY},
          voletOuvert:element.closest('details')?.open,
          cadre:vue.frameElement ? rect(vue.frameElement) : null};
      }, undefined, {timeout:3000}));
    } catch { console.error('Lien PWA : diagnostic indisponible après le délai dépassé.'); }
    throw erreur;
  }
};
