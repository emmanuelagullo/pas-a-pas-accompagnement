const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function champ(value='') { return {value,disabled:false,listeners:{},addEventListener(n,f){this.listeners[n]=f;},input(v){this.value=v;this.listeners.input?.();}}; }
const debut=champ('2024-02-28'),fin=champ('2024-03-01'),duree=champ('2');
const modes=[{value:'dates',checked:true},{value:'duree',checked:false}];
const form={querySelector(s){return {'[data-periode-debut]':debut,'[data-periode-fin]':fin,'[data-periode-duree]':duree}[s];},querySelectorAll(){return modes;}};
vm.runInNewContext(fs.readFileSync(require('node:path').join(__dirname,'../static/periodes-saisie.js'),'utf8'),{document:{querySelectorAll(){return [form];}},Date,Number});
duree.input('3');assert.equal(fin.value,'2024-03-02');assert.ok(modes[1].checked);
debut.input('2026-03-29');assert.equal(fin.value,'2026-04-01');
fin.input('2026-04-05');assert.equal(duree.value,'7');assert.ok(modes[0].checked);
fin.input('2026-03-01');assert.equal(debut.value,'2026-03-29');assert.equal(duree.value,'');
fin.input('');assert.equal(duree.value,'');
debut.input('2026-01-31');duree.input('1');assert.equal(fin.value,'2026-02-01');
debut.input('9999-12-31');duree.input('2');assert.equal(fin.value,'');
console.log('Durées civiles : années bissextiles, mois, changement d’heure, erreurs et bornes : OK (banc JS, sans navigateur).');
