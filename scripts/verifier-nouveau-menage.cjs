const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm'), assert = require('node:assert/strict');
const fields = Object.fromEntries(['personne', 'designation', 'prenom'].map(name => [name, {
  disabled: false, required: false, paragraph: {hidden: false},
  closest(selector) { assert.equal(selector, 'p'); return this.paragraph; }
}]));
let changed;
const choix = {value: 'existante', addEventListener(name, action) { assert.equal(name, 'change'); changed = action; }};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../static/nouveau-menage.js'), 'utf8'), {
  document: {getElementById: id => id === 'id_premiere_personne' ? choix : fields[id.replace('id_', '')]}
});
assert.equal(fields.personne.required, true);
assert.equal(fields.designation.disabled, true);
assert.equal(fields.designation.paragraph.hidden, true);
choix.value = 'nouvelle'; changed();
assert.equal(fields.personne.disabled, true);
assert.equal(fields.personne.required, false);
assert.equal(fields.designation.disabled, false);
assert.equal(fields.designation.required, true);
assert.equal(fields.designation.paragraph.hidden, false);
assert.equal(fields.prenom.required, false);
choix.value = 'existante'; changed();
assert.equal(fields.personne.required, true);
assert.equal(fields.designation.required, false);
console.log('BD4 : champs actifs et obligatoires selon le choix de la première personne : OK');
