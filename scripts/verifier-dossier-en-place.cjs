// Le vrai script livré : aucune réémission POST, ni perte du formulaire sur panne.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
(async () => {
  const listeners = {}, pending = [], status = {textContent: ''};
  let disponible = false;
  const boite = {setAttribute() {}, removeAttribute() {}};
  const form = {matches: s => s === '[data-prestation-form]', getAttribute: () => 'https://exemple.invalid/chrs/dossiers/menage/fictif/?prestation=sejour:fictif', elements: [{disabled: false}], method: 'post', action: 'https://exemple.invalid/chrs/sortie/',
    closest: selector => selector === '[data-prestation-form]' ? form : boite};
  const context = {
    window: {addEventListener: (nom, f) => listeners[nom] = f},
    document: {querySelector: selector => selector==='[data-dossier-form2]' ? boite : null, documentElement: {classList: {add() {}}}, querySelectorAll: () => [], addEventListener: (nom, f) => { const precedent = listeners[nom]; listeners[nom] = e => { precedent?.(e); f(e); }; },
      getElementById: () => status,
      dispatchEvent: evenement => {
        assert.equal(evenement.type, 'condition:disponible');
        assert.equal(evenement.cancelable, true);
        return disponible;
      }},
    location: {href: 'https://exemple.invalid/chrs/dossiers/menage/fictif/', origin: 'https://exemple.invalid'},
    URL, Event, queueMicrotask, FormData: class { append() {} },
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
  assert.equal(form.elements[0].disabled, false, 'La saisie reste dans le DOM pendant la requête');
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
  let programmations = 0, remplacements = 0, date = '2026-11-07';
  const fin = {matches: () => true, closest: () => form, form};
  const enregistrer = {hidden: true, removeAttribute() {}};
  form.querySelector = () => ({
    querySelector: selecteur => selecteur === '[data-prestation-soumission-implicite]' ? enregistrer : true,
    replaceChildren() { remplacements++; },
  });
  fin.closest = selecteur => selecteur === '[data-prestation-url]' ? null : form;
  context.window.PasRecherche = {temporiser: () => () => { programmations++; }};
  context.FormData = class { *[Symbol.iterator]() { yield ['fin', date]; } };
  listeners.input({target: fin});
  listeners.change({target: fin});
  assert.equal(programmations, 1, 'Quitter un champ déjà vérifié ne relance pas la vérification');
  assert.equal(remplacements, 1, 'Quitter le champ ne doit pas retirer le bouton de confirmation');
  date = '2026-11-08';
  listeners.input({target: fin});
  assert.equal(programmations, 2, 'Une nouvelle valeur relance la vérification');
  console.log('NAV7 : double POST, panne sans rejeu, saisie conservée et initialisation unique : OK');
})();
