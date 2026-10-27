// Le vrai script livré : aucune réémission POST, ni perte du formulaire sur panne.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
(async () => {
  const listeners = {}, pending = [], status = {textContent: ''};
  let disponible = false;
  const boite = {setAttribute() {}, removeAttribute() {}};
  const form = {elements: [{disabled: false}], method: 'post', action: 'https://exemple.invalid/chrs/sortie/',
    closest: selector => selector === '.operation-en-place' ? {} : boite};
  const context = {
    window: {addEventListener: (nom, f) => listeners[nom] = f},
    document: {addEventListener: (nom, f) => listeners[nom] = f,
      getElementById: () => status,
      dispatchEvent: evenement => {
        assert.equal(evenement.type, 'condition:disponible');
        assert.equal(evenement.cancelable, true);
        return disponible;
      }},
    location: {href: 'https://exemple.invalid/chrs/dossiers/menage/fictif/', origin: 'https://exemple.invalid'},
    URL, Event, FormData: class { append() {} },
    fetch: (url, options) => new Promise((resolve, reject) => pending.push({url, options, resolve, reject})),
  };
  const code = fs.readFileSync(path.join(__dirname, '../static/dossier-en-place.js'), 'utf8');
  vm.runInNewContext(code, context);
  listeners.input({target: form});
  const evenement = {target: form, preventDefault() {}};
  listeners.submit(evenement);
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(pending.length, 0, 'Une saisie sociale ouverte doit bloquer le POST de prestation');
  assert.equal(form.elements[0].disabled, false, 'Le refus de coordination doit réactiver le formulaire');
  assert.match(status.textContent, /Terminez ou annulez la saisie/);
  disponible = true;
  listeners.submit(evenement);
  listeners.submit(evenement);
  assert.equal(pending.length, 1, 'Un double clic ne doit produire qu’un POST');
  assert.equal(pending[0].options.method, 'POST');
  assert.equal(form.elements[0].disabled, true);
  pending[0].reject(new TypeError('Network error'));
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(form.elements[0].disabled, false);
  assert.equal(pending.length, 1, 'Une panne ne doit jamais réémettre une écriture');
  assert.match(status.textContent, /Enregistrement non confirmé/);
  assert.match(status.textContent, /saisie est conservée/);
  let protege = false;
  listeners.beforeunload({preventDefault() { protege = true; }});
  assert.equal(protege, true, 'La saisie reste protégée après une panne');
  const initial = listeners.submit;
  vm.runInNewContext(code, context);
  assert.equal(listeners.submit, initial, 'Pas de double gestionnaire au retour du dossier');
  console.log('Form2 : double POST, panne sans rejeu, saisie conservée et initialisation unique : OK');
})();
