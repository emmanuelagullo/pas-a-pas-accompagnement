// Attendre le nouveau document de l'iframe, même si son URL ou son titre
// est identique au précédent. Les formulaires en place n'utilisent pas cet outil.
module.exports = async function cliquerLienPwa(cible) {
  const element = await cible.elementHandle();
  if (!element) throw new Error('Contrôle de navigation PWA absent.');
  const cadre = await element.ownerFrame();
  if (!cadre) throw new Error('Cadre de navigation PWA absent.');
  try {
    await Promise.all([
      cible.page().waitForEvent('framenavigated', {predicate: nouveau => nouveau === cadre}),
      cible.click(),
    ]);
    await cadre.waitForLoadState('domcontentloaded');
  } finally {
    await element.dispose();
  }
};
