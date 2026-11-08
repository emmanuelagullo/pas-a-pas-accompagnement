const assert = require('node:assert/strict');
const path = require('node:path');
const {createRequire} = require('node:module');
const requirePwa = createRequire(path.resolve(__dirname, '../pwa/package.json'));
const {chromium} = process.env.PWA_PLAYWRIGHT ? require(process.env.PWA_PLAYWRIGHT) : requirePwa('playwright');

(async () => {
  const navigateur = await chromium.launch({
    executablePath: process.env.PWA_CHROMIUM || undefined,
    args: ['--no-sandbox'],
  });
  try {
    const page = await navigateur.newPage({locale: 'en-US'});
    await page.setContent(`<main data-dossier-form2 data-prestation-verifiable><form data-prestation-form action="https://example.invalid/prestation">
      <label for="debut">Début</label><input id="debut" name="debut" value="28/02/2028" data-date-fr data-periode-debut>
      <label for="fin">Fin</label><input id="fin" name="fin" value="29/02/2028" data-date-fr data-periode-fin>
      <input name="duree" type="number" data-periode-duree>
      <input type="radio" name="calcul_periode" value="dates" data-periode-calcul checked>
      <input type="radio" name="calcul_periode" value="duree" data-periode-calcul>
    <div data-validation-prestation><button type="submit">Enregistrer</button></div>
    </form></main>`);
    await page.evaluate(() => {
      window.fetch = async (_url, {body}) => new Response(JSON.stringify({
        commandes: body.get('fin') === '01/03/2028'
          ? '<button type="submit" name="confirmation_fin">Ajuster la prise</button>'
          : '<button type="submit">Enregistrer</button>',
        erreurs: {},
      }), {headers: {'Content-Type': 'application/json'}});
    });
    await page.addScriptTag({path: path.resolve(__dirname, '../static/recherche-commune.js')});
    await page.addScriptTag({path: path.resolve(__dirname, '../static/dossier-en-place.js')});
    await page.addScriptTag({path: path.resolve(__dirname, '../static/periodes-saisie.js')});
    const fin = page.locator('#fin');
    const duree = page.locator('[name=duree]');
    await page.getByRole('button', {name: 'Fin — Jour suivant', exact: true}).click();
    assert.equal(await fin.inputValue(), '01/03/2028');
    assert.equal(await duree.inputValue(), '2');
    await page.getByRole('button', {name: 'Ajuster la prise'}).waitFor();
    await fin.press('ArrowDown');
    assert.equal(await fin.inputValue(), '29/02/2028');
    await page.getByRole('button', {name: 'Enregistrer'}).waitFor();
    await fin.fill('');
    assert.equal(await page.getByRole('button', {name: 'Fin — Jour précédent', exact: true}).isDisabled(), true);
    assert.equal(await duree.inputValue(), '');
    await duree.fill('3');
    assert.equal(await fin.inputValue(), '02/03/2028');

    // Le sélecteur système est externe au DOM. Vérifier l’appel natif, puis le
    // repli et le report du choix par le véritable champ date du navigateur.
    await page.evaluate(() => {
      const original = HTMLInputElement.prototype.showPicker;
      HTMLInputElement.prototype.showPicker = function () {
        document.body.dataset.calendrier = this.value;
        original?.call(this);
        throw new DOMException('Repli testé', 'NotAllowedError');
      };
    });
    await page.getByRole('button', {name: 'Fin — Ouvrir le calendrier', exact: true}).click();
    assert.equal(await page.locator('body').getAttribute('data-calendrier'), '2028-03-02');
    await page.keyboard.press('Escape');
    await page.locator('.saisie-date-native-visible').fill('2028-03-03');
    assert.equal(await fin.inputValue(), '03/03/2028');
    assert.equal(await duree.inputValue(), '4');
    assert.deepEqual(await page.locator('form').evaluate(form => [...new FormData(form).keys()]),
      ['debut', 'fin', 'duree', 'calcul_periode']);
    console.log('Dates des prestations : saisie FR, pas civil, durée, calendrier et repli : OK');
  } finally {
    await navigateur.close();
  }
})().catch(erreur => { console.error(erreur); process.exitCode = 1; });
