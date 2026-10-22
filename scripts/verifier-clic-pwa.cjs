const assert = require('node:assert/strict');
const cliquer = require('./cliquer-lien-pwa.cjs');
(async () => {
  const ordre = [];
  let terminer, charge = false;
  const navigation = new Promise(resolve => { terminer = resolve; });
  const cadre = {async waitForLoadState(etat) {
    assert.equal(etat, 'domcontentloaded'); charge = true; ordre.push('document');
  }};
  const cible = {
    async elementHandle() { return {async ownerFrame() { return cadre; }, async dispose() { ordre.push('libere'); }}; },
    page() { return {waitForEvent(nom, options) {
      assert.equal(nom, 'framenavigated');
      assert.equal(options.predicate(cadre), true);
      assert.equal(options.predicate({}), false);
      ordre.push('attente'); return navigation;
    }}; },
    async click(options) {
      assert.equal(options, undefined, 'Conserver les contrôles normaux du clic');
      assert.equal(ordre[0], 'attente', 'Armer l’attente avant le clic'); ordre.push('clic');
    },
  };
  let fini = false;
  const resultat = cliquer(cible).then(() => { fini = true; });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(fini, false, 'Le clic seul ne garantit pas l’arrivée du nouveau document');
  assert.equal(charge, false);
  terminer(cadre); await resultat;
  assert.deepEqual(ordre, ['attente', 'clic', 'document', 'libere']);
  let clics = 0;
  const panne = new Error('Clic non abouti');
  await assert.rejects(() => cliquer({...cible, async click() { clics++; throw panne; }}), e => e === panne);
  assert.equal(clics, 1, 'Ne pas rejouer un clic en échec');
  console.log('Navigation PWA : attente armée avant le clic, cadre exact, document chargé et aucun rejeu : OK');
})();
