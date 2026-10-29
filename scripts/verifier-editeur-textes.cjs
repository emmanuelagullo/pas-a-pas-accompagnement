// Composant réel : saisie, sécurité du collage, clavier, rechargement et repli.
const fs = require('node:fs'), path = require('node:path'), http = require('node:http'), assert = require('node:assert/strict');
const {createRequire} = require('node:module');
const requirePwa = createRequire(path.resolve(__dirname, '../pwa/package.json'));
const {chromium} = process.env.PWA_PLAYWRIGHT ? require(process.env.PWA_PLAYWRIGHT) : requirePwa('playwright');
const racine = path.resolve(__dirname, '../static');
const formulaire = (texte='**ancien** <à compléter>', doc='') => `<form><label for="id_texte">Commentaire libre</label><textarea id="id_texte" name="texte" data-texte-riche="1" data-max-texte="100" data-texte-obligatoire="1"${doc?' readonly':''}>${texte.replaceAll('&','&amp;').replaceAll('<','&lt;')}</textarea><input type="hidden" name="texte_document" data-document-riche value="${doc.replaceAll('&','&amp;').replaceAll('"','&quot;')}"><button type="submit">Enregistrer</button></form>`;
const pageHTML = `<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>textarea {display:block}</style><link rel="stylesheet" href="/textes-riches.css"><script src="/textes-riches.js" data-editeur-source="/editeur/texte-riche.js" defer></script></head><body><main>${formulaire()}</main></body></html>`;
const serveur = http.createServer((req,res) => {
  if (req.url === '/') {res.setHeader('Content-Type','text/html; charset=utf-8');res.end(pageHTML);return;}
  const fichier = path.resolve(racine, '.' + req.url);
  if (!fichier.startsWith(racine + path.sep)) {res.writeHead(403).end();return;}
  try {res.setHeader('Content-Type', fichier.endsWith('.css')?'text/css':'text/javascript');res.end(fs.readFileSync(fichier));}
  catch {res.writeHead(404).end();}
});
(async()=>{
 let navigateur;
 try {
  await new Promise(r=>serveur.listen(0,'127.0.0.1',r));
  const origine=`http://127.0.0.1:${serveur.address().port}`;
  navigateur=await chromium.launch({headless:true,...(process.env.PWA_CHROMIUM?{executablePath:process.env.PWA_CHROMIUM}:{}),args:['--no-sandbox','--disable-dev-shm-usage']});
  const contexte=await navigateur.newContext(), page=await contexte.newPage();
  const erreurs=[], externes=[];
  page.on('pageerror', e=>erreurs.push(e.message));
  page.on('console', m=>{if(m.type()==='error')erreurs.push(m.text());});
  await page.route('**/*',route=>{if(!route.request().url().startsWith(origine+'/')){externes.push(route.request().url());return route.abort();}return route.continue();});
  await page.goto(origine);
  const zone=page.getByRole('textbox',{name:'Commentaire libre',exact:true});
  await page.locator('.ProseMirror').waitFor();
  assert.equal(await page.locator('textarea[data-texte-riche]').isVisible(),false);
  assert.equal(await zone.innerText(),'**ancien** <à compléter>');
  assert.equal(await page.locator('[name=texte_document]').inputValue(),'','aucune conversion à l’ouverture');
  await zone.fill('Texte fictif');await zone.press('ControlOrMeta+a');await page.getByRole('button',{name:'Gras',exact:true}).click();
  let document=JSON.parse(await page.locator('[name=texte_document]').inputValue());
  assert.equal(document.doc.content[0].content[0].marks[0].type,'bold');
  await page.getByRole('button',{name:'Italique',exact:true}).focus();await page.keyboard.press('Enter');
  assert(await zone.locator('em').count());
  await page.getByRole('button',{name:'Liste à puces',exact:true}).click();assert(await zone.locator('ul li').count());
  await page.getByRole('button',{name:'Liste à puces',exact:true}).click();
  await zone.press('ControlOrMeta+a');await zone.press('ControlOrMeta+k');
  await page.getByLabel('Adresse du lien',{exact:true}).fill('javascript:alert(1)');
  await page.getByRole('button',{name:'Appliquer le lien',exact:true}).click();
  assert((await page.locator('[role=alert]').textContent()).includes('https://'));
  await page.getByLabel('Adresse du lien',{exact:true}).fill('https://example.org/accueil');
  await page.getByRole('button',{name:'Appliquer le lien',exact:true}).click();
  assert.equal(await zone.locator('a').getAttribute('href'),'https://example.org/accueil');
  await zone.press('ControlOrMeta+a');
  await zone.evaluate(e=>{const presse=new DataTransfer();presse.setData('text/html','<p style="font-size:40pt"><b>Collage Word</b> <i>fictif</i><img src="https://example.org/photo"><a href="javascript:alert(1)">lien interdit</a><script>window.piratage=1</script></p>');presse.setData('text/plain','Collage Word fictif');e.dispatchEvent(new ClipboardEvent('paste',{clipboardData:presse,bubbles:true,cancelable:true}));});
  assert(await zone.locator('strong').count());assert.equal(await zone.locator('img,script,[style]').count(),0);
  assert.equal(await page.evaluate(()=>window.piratage),undefined);
  assert.equal(await zone.locator('a[href^="javascript:"]').count(),0);
  // Persistance simulée puis remplacement de formulaire, comme Form2/HTMX.
  document=JSON.parse(await page.locator('[name=texte_document]').inputValue());
  const sauvegarde=JSON.stringify(document);
  await page.evaluate(html=>{document.querySelector('main').innerHTML=html;},formulaire('projection',sauvegarde));
  await page.locator('.ProseMirror strong').first().waitFor();
  assert((await zone.innerText()).includes('Collage Word'));
  assert.equal(await page.locator('.edition-texte').count(),1);
  await zone.fill('*pas de Markdown*');assert.equal(await zone.locator('em').count(),0);
  // Une liste ne doit pas englober les paragraphes voisins du curseur.
  await zone.fill('Premier');await zone.press('Enter');await page.keyboard.insertText('Deuxième');await zone.press('Enter');await page.keyboard.insertText('Troisième');
  await zone.press('ArrowUp');await zone.press('Home');
  await page.getByRole('button',{name:'Liste à puces',exact:true}).click();
  assert.equal(await zone.locator(':scope > ul > li').count(),1);
  assert.equal(await zone.locator(':scope > ul').innerText(),'Deuxième');
  assert.equal(await zone.locator(':scope > p').count(),2);
  await page.getByRole('button',{name:'Liste numérotée',exact:true}).click();
  assert.equal(await zone.locator(':scope > ol > li').count(),1);
  assert.equal(await zone.locator(':scope > p').count(),2);
  await page.getByRole('button',{name:'Liste numérotée',exact:true}).click();
  await zone.evaluate(e => {const ps=e.querySelectorAll(':scope > p'), r=document.createRange();r.setStart(ps[1],0);r.setEnd(ps[2],ps[2].childNodes.length);const selection=getSelection();selection.removeAllRanges();selection.addRange(r);});
  await page.getByRole('button',{name:'Liste à puces',exact:true}).click();
  assert.equal(await zone.locator(':scope > ul > li').count(),2);
  assert.equal(await zone.locator(':scope > p').count(),1);

  // La validation cliente n’envoie pas un texte obligatoire vide.
  await page.evaluate(()=>{window.envoye=false;document.querySelector('form').addEventListener('submit',e=>{e.preventDefault();window.envoye=true;});});
  await zone.press('ControlOrMeta+a');await zone.press('Backspace');
  await page.locator('.edition-etat').filter({hasText:/^0 \/ 100 caractères$/}).waitFor();
  await page.getByRole('button',{name:'Enregistrer',exact:true}).click();
  assert.equal(await page.evaluate(()=>window.envoye),false);
  await zone.fill('x'.repeat(101));
  await page.locator('.edition-etat').filter({hasText:/^101 \/ 100 caractères$/}).waitFor();
  await page.getByRole('button',{name:'Enregistrer',exact:true}).click();
  assert.equal(await page.evaluate(()=>window.envoye),false);
  await zone.fill('Texte valide');
  await page.locator('.edition-etat').filter({hasText:/^12 \/ 100 caractères$/}).waitFor();
  await page.getByRole('button',{name:'Enregistrer',exact:true}).click();
  assert.equal(await page.evaluate(()=>window.envoye),true,'un texte valide reste envoyable');
  await page.setViewportSize({width:360,height:900});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  const sansJS=await navigateur.newContext({javaScriptEnabled:false});const repli=await sansJS.newPage();await repli.goto(origine);
  await repli.getByLabel('Commentaire libre',{exact:true}).fill('Texte simple sans JavaScript');
  assert.equal(await repli.locator('[name=texte]').inputValue(),'Texte simple sans JavaScript');
  assert.deepEqual(externes,[]);assert.deepEqual(erreurs,[]);
  console.log('Éditeur : ancien texte littéral, gras/italique/listes/liens au clavier, collage filtré, remplacement, limites, 360px et repli sans JS : OK');
 } finally {await navigateur?.close();await new Promise(r=>serveur.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
