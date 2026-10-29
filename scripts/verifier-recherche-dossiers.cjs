// Exécute le script livré : une réponse ancienne ne doit jamais remplacer la nouvelle saisie.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const path = require('node:path');
(async () => {
  const listeners = {}, timers = new Map(), pending = [], states = [];
  let timerId = 0;
  const declencher = () => {
    assert.equal(timers.size, 1);
    const [id, callback] = timers.entries().next().value;
    timers.delete(id);
    return callback();
  };
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
    setTimeout: callback => { const id = ++timerId; timers.set(id, callback); return id; },
    clearTimeout: id => timers.delete(id),
    fetch: (url, options) => new Promise(resolve => pending.push({url, options, resolve})),
  };
  // Charger les deux scripts réels dans le même environnement, comme base.html.
  context.window = context;
  vm.createContext(context);
  for (const script of ['recherche-commune.js', 'recherche-dossiers.js']) {
    vm.runInContext(fs.readFileSync(path.join(__dirname, '../static', script), 'utf8'), context, {filename: script});
  }
  assert.equal(nouveau.disabled,true);
  form.elements.mode.value='personne';
  listeners.input(); assert.equal(nouveau.disabled,false); const old = declencher();
  query = 'Camille'; listeners.input(); const current = declencher();
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
  listeners.input(); assert.equal(accents.at(-1),false); const redirected = declencher();
  pending[2].resolve({ok: true, redirected: true});
  await redirected;
  assert.match(status.textContent, /bouton Rechercher/);
  assert.equal(results.innerHTML, 'Camille courant');
  assert.equal(results.inert, true);
  // Une frappe rapprochée remplace la précédente ; le GET annule le délai restant.
  query = 'Lou'; listeners.input();
  query = 'Louise'; listeners.input();
  assert.equal(pending.length, 3);
  const rapide = declencher();
  assert.match(String(pending[3].url), /q=Louise/);
  pending[3].resolve({ok: true, redirected: false, text: async () => 'Louise courant'});
  await rapide;
  assert.equal(results.innerHTML, 'Louise courant');
  listeners.input(); listeners.submit();
  assert.equal(timers.size, 0);
  assert.equal(pending.length, 4);
  assert.equal(pending[3].options.signal.aborted, true);
  console.log('BD4 : réponses désordonnées, sous-préfixe, retour connexion et repli GET : OK');
})().catch(error => { console.error(error); process.exitCode = 1; });
