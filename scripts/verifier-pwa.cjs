// Chromium réel ; serveur statique et profil éphémères, données fictives seulement.
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict');
const {createRequire}=require('node:module');
const requirePwa=createRequire(path.resolve(__dirname,'../pwa/package.json'));
const {chromium}=process.env.PWA_PLAYWRIGHT?require(process.env.PWA_PLAYWRIGHT):requirePwa('playwright');
const root=path.resolve(__dirname,'../dist/pwa');
const types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.webmanifest':'application/manifest+json','.css':'text/css','.wasm':'application/wasm','.svg':'image/svg+xml','.png':'image/png'};
const base=process.env.PWA_BASE_PATH||'/chrs/';
const server=http.createServer((req,res)=>{
 const url=new URL(req.url,'http://localhost');
 if(!url.pathname.startsWith(base)){res.writeHead(404).end();return;}
 const relatif=url.pathname.slice(base.length)||'index.html',f=path.resolve(root,relatif);
 if(!f.startsWith(root+path.sep)){res.writeHead(403).end();return;}
 try{res.setHeader('Content-Type',types[path.extname(f)]||'application/octet-stream');res.end(fs.readFileSync(f));}
 catch{res.writeHead(404).end();}
});
(async()=>{
 let browser;
 try{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const url=`http://127.0.0.1:${server.address().port}${base}`;
  browser=await chromium.launch({headless:true,...(process.env.PWA_CHROMIUM?{executablePath:process.env.PWA_CHROMIUM}:{}),args:['--no-sandbox','--disable-dev-shm-usage']});
  const context=await browser.newContext();let page=await context.newPage();
  page.on('pageerror',e=>console.error('PAGE',String(e)));
  page.on('console',m=>{if(m.type()==='error')console.error('CONSOLE',m.text());});
  async function ouvrir(){await page.goto(url);await page.frameLocator('#app').locator('h1').waitFor({timeout:120000});}
  await ouvrir();const frame=page.frameLocator('#app');
  await frame.locator('[name=username]').fill('essai-pwa');
  await frame.locator('[name=password1]').fill('Phrase fictive navigateur-854!');
  await frame.locator('[name=password2]').fill('Phrase fictive navigateur-854!');
  await frame.getByRole('button',{name:'Créer mon compte et commencer'}).click();
  await frame.getByRole('link',{name:'Créer une personne'}).click();
  await frame.locator('[name=designation]').fill('Personne fictive conservée');
  await frame.getByRole('button',{name:'Enregistrer'}).click();
  await frame.getByRole('heading',{name:'Personne fictive conservée'}).waitFor();
  const autre=await context.newPage();await autre.goto(url);
  await autre.getByText('Cet espace est déjà ouvert dans un autre onglet.').waitFor();await autre.close();
  await context.setOffline(true);await page.reload();
  await page.frameLocator('#app').locator('[name=username]').waitFor({timeout:120000});
  const apres=page.frameLocator('#app');
  await apres.locator('[name=username]').fill('essai-pwa');
  await apres.locator('[name=password]').fill('Phrase fictive navigateur-854!');
  await apres.getByRole('button',{name:'Se connecter'}).click();
  await apres.getByRole('link',{name:'Personnes',exact:true}).click();
  await apres.getByText('Personne fictive conservée').waitFor();
  await context.setOffline(false);
  await require('./verifier-stockage-pwa.cjs')(page,url);
  console.log('Chromium CHRS : création → second onglet refusé → relance hors ligne → reconnexion et persistance : OK');
 }finally{await browser?.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);process.exitCode=1;});
