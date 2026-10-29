// Exécute le script livré : une réponse ancienne ne doit jamais remplacer la nouvelle saisie.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const listeners = {}, timers = [], pending = [], states = [];
  const accents=[], actualisations=[];let suggestion='non';
  const nouveau={classList:{add:()=>accents.push(false),toggle:(_classe,secondaire)=>accents.push(!secondaire)},disabled:false,dataset:{personne:'oui',menage:'non'}};
  const form = {elements:{mode:{value:'menage'}},querySelector:()=>nouveau,action: 'https://exemple.invalid/chrs/app/', addEventListener: (name, callback) => listeners[name] = callback};
  const results = {querySelector:()=>({dataset:{creationSuggeree:suggestion}}),innerHTML: '', inert: false, setAttribute() {}, removeAttribute() {}};
  const status = {textContent: ''};
  let query = 'Alex';
  const context = {
    document: {dispatchEvent: event => actualisations.push(event.type), getElementById: id => ({'recherche-dossiers': form, 'resultats-dossiers': results, 'recherche-etat': status})[id]},
    FormData: class { *[Symbol.iterator]() { yield ['q', query]; yield ['mode', 'menage']; } },
    URLSearchParams, URL, AbortController, Event,
    history: {replaceState: (_a, _b, url) => states.push(String(url))},
    setTimeout: callback => { timers.push(callback); return timers.length; }, clearTimeout() {},
    fetch: (url, options) => new Promise(resolve => pending.push({url, options, resolve})),
  };
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../static/recherche-dossiers.js'), 'utf8'), context);
  assert.equal(nouveau.disabled,true);
  form.elements.mode.value='personne';
  listeners.input(); assert.equal(nouveau.disabled,false); const old = timers.pop()();
  query = 'Camille'; listeners.input(); const current = timers.pop()();
  assert.equal(pending[0].options.signal.aborted, true);
  assert.equal(results.inert, true);
  pending[0].resolve({ok: true, redirected: false, text: async () => 'Alex ancien'});
  await old;
  assert.equal(results.innerHTML, '');
  assert.deepEqual(actualisations, []);
  assert.equal(results.inert, true);
  suggestion='oui';
  pending[1].resolve({ok: true, redirected: false, text: async () => 'Camille courant'});
  await current;
  assert.equal(results.innerHTML, 'Camille courant');
  assert.deepEqual(actualisations, ['dossier:actualise']);
  assert.equal(accents.at(-1),true);
  assert.equal(results.inert, false);
  assert.match(states[0], /q=Camille/);
  assert.match(String(pending[1].url), /chrs\/app\/\?q=Camille/);
  assert.match(String(pending[1].url), /fragment=1/);
  listeners.input(); assert.equal(accents.at(-1),false); const redirected = timers.pop()();
  pending[2].resolve({ok: true, redirected: true});
  await redirected;
  assert.match(status.textContent, /bouton Rechercher/);
  assert.equal(results.innerHTML, 'Camille courant');
  assert.equal(results.inert, true);
  console.log('BD4 : réponses désordonnées, sous-préfixe, retour connexion et repli GET : OK');
})().catch(error => { console.error(error); process.exitCode = 1; });
