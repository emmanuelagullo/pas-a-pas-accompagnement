import { build } from 'esbuild';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { gzipSync } from 'node:zlib';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
const root = path.dirname(fileURLToPath(import.meta.url));
const sortie = path.resolve(root, '../../static/editeur/texte-riche.js');
await build({entryPoints: [path.join(root, 'edition.js')], outfile: sortie, bundle: true, minify: true, format: 'iife', target: ['es2020'], legalComments: 'eof', supported: {'template-literal': false}});
const contenu = readFileSync(sortie);
console.log(JSON.stringify({octets: contenu.length, gzip: gzipSync(contenu).length, sha256: createHash('sha256').update(contenu).digest('hex')}));
// Conserver toutes les licences transitives des composants distribués.
const lock = JSON.parse(readFileSync(path.join(root, 'package-lock.json')));
let licences = 'Composants de l’éditeur embarqué — versions épinglées dans package-lock.json\n\n';
for (const [nom, paquet] of Object.entries(lock.packages)) {
  if (!nom || nom.includes('esbuild')) continue;
  const dossier = path.join(root, nom);
  for (const fichier of ['LICENSE', 'LICENSE.md', 'LICENSE.txt', 'license']) {
    try { licences += `\n=== ${nom} ${paquet.version} ===\n` + readFileSync(path.join(dossier, fichier), 'utf8'); break; } catch {}
  }
}
writeFileSync(path.join(path.dirname(sortie), 'LICENCES.txt'), licences);
