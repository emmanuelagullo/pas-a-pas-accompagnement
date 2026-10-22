const assert = require('node:assert/strict');
const cliquer = require('./cliquer-lien-pwa.cjs');
(async () => {
  const ordre = [];
  const lien = {
    async waitFor(options) { assert.equal(options.state, 'visible'); ordre.push('visible'); },
    async evaluate(f) {
      f({scrollIntoView(options) {
        assert.deepEqual(options, {block:'center', inline:'nearest', behavior:'instant'});
        ordre.push('defilement');
      }});
    },
    async click(options) {
      assert.equal(options, undefined, 'Le clic conserve les contrôles normaux de Playwright');
      ordre.push('clic');
    },
  };
  await cliquer(lien);
  assert.deepEqual(ordre, ['visible', 'defilement', 'clic']);
  let clics = 0;
  const panne = new Error('Clic non abouti');
  const log = console.error;
  console.error = () => {};
  try {
    await assert.rejects(() => cliquer({...lien, async click() { clics++; throw panne; }}), e => e === panne);
  } finally { console.error = log; }
  assert.equal(clics, 1, 'Pas de rejeu du clic ni de masquage d’un échec');
  console.log('Clic PWA : défilement préalable, clic normal et échec conservé sans rejeu : OK');
})();
