/* Une préférence serveur, des fragments graphiques ; aucune saisie remplacée. */
(() => {
  let occupe = false;
  const ouverts = new Set();
  const boutons = () => document.querySelectorAll('[data-frise-choix] button').forEach(b => b.hidden = true);
  boutons();
  document.addEventListener('dossier:actualise', boutons);
  document.addEventListener('dossier:commandes', boutons);
  document.addEventListener('change', async event => {
    const box = event.target;
    const form = box.closest('[data-frise-choix]');
    if (!form || box.name !== 'actif') return;
    if (occupe || document.getElementById('resultats-dossiers')?.inert || !document.dispatchEvent(new Event('condition:disponible', {cancelable:true})) ||
        !document.dispatchEvent(new Event('dossier:disponible', {cancelable:true}))) {
      box.checked = !box.checked; return;
    }
    occupe = true;
    const data = new FormData(form);
    box.disabled = true;
    try {
      const r = await fetch(form.action, {method:'POST',body:data,credentials:'same-origin',headers:{'X-Frises-Pref':'1'}});
      if (!r.ok) throw new Error('Préférence non enregistrée');
      const page = await fetch(location.href, {credentials:'same-origin',cache:'no-store'});
      if (!page.ok || page.redirected) { location.assign(page.url); return; }
      const doc = new DOMParser().parseFromString(await page.text(), 'text/html');
      const nouveaux = new Map([...doc.querySelectorAll('[data-frise-slot]')].map(n => [n.dataset.friseSlot,n]));
      const anciens = [...document.querySelectorAll('[data-frise-slot]')];
      // Un changement concurrent de la liste exige sa relecture entière.
      if (anciens.length !== nouveaux.size || anciens.some(n => !nouveaux.has(n.dataset.friseSlot))) {
        location.reload(); return;
      }
      document.querySelectorAll('.frise-details[open],.frise-objectif-details[open]').forEach(d => ouverts.add(d.id));
      const y = scrollY;
      anciens.forEach(n => { n.replaceChildren(...nouveaux.get(n.dataset.friseSlot).childNodes); });
      document.querySelectorAll('.frise-details,.frise-objectif-details').forEach(d => { if(ouverts.has(d.id)) d.open = true; });
      document.querySelectorAll('.resultats-dossiers').forEach(l => l.classList.toggle('avec-frises',box.checked));
      document.querySelectorAll('[data-frise-choix] input[name=actif]').forEach(c => c.checked=box.checked);
      document.querySelectorAll('[data-frise-aide]').forEach(d => {d.hidden=!box.checked;if(!box.checked) d.open=false;});
      document.querySelectorAll('[data-frise-outils]').forEach(g => g.classList.toggle('frise-active',box.checked));
      document.querySelectorAll('[data-elements-dates]').forEach(l => l.classList.toggle('avec-frise',box.checked));
      scrollTo(0,y);
      document.dispatchEvent(new Event('frises:actualise'));
    } catch (_) {
      form.querySelector('button').hidden = false;
    } finally {
      box.disabled = false; occupe = false;
    }
  });
  document.addEventListener('toggle', e => {
    if(e.target.matches('.frise-details,.frise-objectif-details') && !e.target.open) ouverts.delete(e.target.id);
  }, true);
  function expliquer(zone) {
    if (!zone) return;
    zone.removeAttribute('data-ferme');
    const bulle=zone.querySelector('.frise-explication');
    if (bulle) {
      const gauche=zone.getBoundingClientRect().left, largeur=bulle.getBoundingClientRect().width;
      zone.style.setProperty('--aide-decalage', `${Math.max(8,Math.min(gauche,innerWidth-largeur-8))-gauche}px`);
    }
  }
  document.addEventListener('focusin', e => { expliquer(e.target.closest?.('[data-frise-repere],[data-frise-explication]')); });
  document.addEventListener('pointerover', e => { const zone=e.target.closest?.('[data-frise-repere],[data-frise-explication]'); if(zone && !zone.contains(e.relatedTarget)) expliquer(zone); });
  document.addEventListener('keydown', e => {
    if(e.key === 'Escape') document.querySelectorAll('[data-frise-explication]:hover,[data-frise-explication]:focus-within,[data-frise-repere]:focus').forEach(zone => zone.setAttribute('data-ferme','1'));
  });
})();
/* Cadrage local : seules les marques déjà autorisées sont reprojetées. */
(() => {
  const jour = s => Date.parse(s + 'T00:00:00Z') / 86400000;
  const iso = n => new Date(Math.round(n)*86400000).toISOString().slice(0,10);
  const date = n => new Date(Math.round(n)*86400000).toLocaleDateString('fr-FR', {timeZone:'UTC'});
  const anneeAvant = n => {
    const d=new Date(n*86400000), y=d.getUTCFullYear()-1, m=d.getUTCMonth(), j=d.getUTCDate();
    return Date.UTC(y,m,Math.min(j,new Date(Date.UTC(y,m+1,0)).getUTCDate()))/86400000;
  };
  const memoire = new Map();
  function preparer(zone) {
    if(zone.friseFenetre) return zone.friseFenetre;
    const debut=jour(zone.dataset.debut), fin=jour(zone.dataset.fin);
    const comprimee=zone.dataset.comprimee==='1', annee=fin-anneeAvant(fin);
    const distance=a => !comprimee || a<=annee ? a : annee+90*Math.log1p((a-annee)/90);
    const inverse=d => !comprimee || d<=annee ? d : annee+90*Math.expm1((d-annee)/90);
    const total=distance(fin-debut);
    const marques=[...zone.querySelectorAll('[data-frise-dessin] .frise-marque')].map(el => {
      const x=parseFloat(el.style.left), w=parseFloat(el.style.width);
      return {el,point:el.hasAttribute('data-frise-point'),a:fin-inverse(total*(1-x/100)),b:fin-inverse(total*(1-(x+w)/100)),style:el.getAttribute('style')};
    });
    const lignes=[...zone.querySelectorAll('[data-frise-periode]')].map(el => ({el,a:jour(el.dataset.debut),b:el.dataset.fin?jour(el.dataset.fin):fin}));
    const cle='pas-frise:'+zone.dataset.compte+':'+location.pathname+':'+zone.closest('.frise-details').id+':'+iso(debut)+':'+iso(fin);
    const etat={debut,fin,marques,lignes,cle,legende:zone.querySelector('[data-frise-cadrage]').textContent};
    zone.friseFenetre=etat;
    const reglages=zone.querySelector('[data-frise-reglages]');reglages.hidden=false;
    for(const borne of ['debut','fin']) {
      const champ=zone.querySelector(`[data-frise-date="${borne}"]`);
      champ.value=iso(etat[borne]);champ.max=iso(fin);champ.min=iso(debut);
    }
    let stock= memoLire(cle);
    if(stock) {
      for(const el of zone.querySelectorAll('[data-frise-cadre],[data-frise-borne],[data-frise-date],[data-frise-zoom],[data-frise-position]')) {
        const attribut=['data-frise-cadre','data-frise-borne','data-frise-date','data-frise-zoom','data-frise-position'].find(a=>el.hasAttribute(a));
        const selecteur=`[${attribut}${el.getAttribute(attribut)?'="'+el.getAttribute(attribut)+'"':''}]`;
        if(typeof stock[selecteur]==='string') el.value=stock[selecteur];
      }
    }
    afficher(zone,false);
    return etat;
  }
  function memoLire(cle) {
    if(memoire.has(cle)) return memoire.get(cle);
    try {return JSON.parse(sessionStorage.getItem(cle));}catch(_){return null;}
  }
  function afficher(zone,sauver=true) {
    const e=zone.friseFenetre;if(!e) return;
    const cadre=zone.querySelector('[data-frise-cadre]').value;
    zone.querySelector('.frise-bornes').hidden=cadre!=='dates';
    let a=e.debut,b=e.fin;
    for(const borne of ['debut','fin']) {
      const choix=zone.querySelector(`[data-frise-borne="${borne}"]`).value;
      zone.querySelector(`[data-frise-date="${borne}"]`).disabled=cadre!=='dates'||choix!=='date';
      if(cadre==='dates') {
        const valeur=choix==='date'?jour(zone.querySelector(`[data-frise-date="${borne}"]`).value):choix==='annee'?anneeAvant(e.fin):e[borne];
        if(borne==='debut') a=valeur;else b=valeur;
      }
    }
    if(cadre==='annee') a=Math.max(e.debut,anneeAvant(e.fin));
    if(cadre==='semaine') a=Math.max(e.debut,e.fin-7);
    if(cadre==='mois'||cadre==='trimestre') {
      const d=new Date(e.fin*86400000), mois=d.getUTCMonth()-(cadre==='mois'?1:3);
      const premier=new Date(Date.UTC(d.getUTCFullYear(),mois,1));
      const dernier=new Date(Date.UTC(premier.getUTCFullYear(),premier.getUTCMonth()+1,0)).getUTCDate();
      a=Math.max(e.debut,Date.UTC(premier.getUTCFullYear(),premier.getUTCMonth(),Math.min(d.getUTCDate(),dernier))/86400000);
    }
    const message=zone.querySelector('[data-frise-message]');
    if(!Number.isFinite(a)||!Number.isFinite(b)||b<=a||a<e.debut||b>e.fin) {
      message.textContent='Choisissez deux dates ordonnées dans la période initiale.';return;
    }
    const zoom=Number(zone.querySelector('[data-frise-zoom]').value);
    const position=zone.querySelector('[data-frise-position]');position.disabled=zoom===0;
    const largeur=Math.max(1,(b-a)/Math.pow(64,zoom/100));
    a+=(b-a-largeur)*Number(position.value)/100;b=a+largeur;
    const initial=cadre==='initial'&&zoom===0;
    const placer=(el,x,y)=>{
      const visible=y>a&&x<b;
      el.hidden=!visible;
      if(visible) {el.style.left=100*(Math.max(a,x)-a)/(b-a)+'%';el.style.width=100*(Math.min(b,y)-Math.max(a,x))/(b-a)+'%';}
    };
    for(const m of e.marques) {
      if(initial) {m.el.hidden=false;m.el.setAttribute('style',m.style);} else if(m.point) {
        m.el.hidden=!(e.fin>=a&&e.fin<=b);
        m.el.style.left=Math.min(99.4,100*(e.fin-a)/(b-a))+'%';m.el.style.width='0.6%';
      } else placer(m.el,m.a,m.b);
    }
    for(const l of e.lignes) {
      const marque=l.el.querySelector('.frise-marque');
      if(marque) {
        // Les détails sont déjà linéaires seulement dans les prises ; réutiliser
        // les positions serveur à la réinitialisation, sinon dates exactes.
        if(!l.style) l.style=marque.getAttribute('style');
        if(initial) {marque.hidden=false;marque.setAttribute('style',l.style);}else placer(marque,l.a,l.b);
      }
    }
    zone.querySelector('[data-frise-reperes-initial]').hidden=!initial;
    zone.querySelector('[data-frise-cadrage]').textContent=initial?e.legende:`Période affichée : ${date(a)} → ${date(b)}`;
    const image=zone.querySelector('[data-frise-dessin] .frise-mini');
    if(!e.aria) e.aria=image.getAttribute('aria-label');
    image.setAttribute('aria-label',initial?e.aria:`Fenêtre du ${date(a)} au ${date(b)}. Détails textuels ci-dessous.`);
    message.textContent='';
    for(const controle of zone.querySelectorAll('[data-frise-zoom],[data-frise-position]')) controle.setAttribute('aria-valuetext',`${date(a)} au ${date(b)}`);
    if(sauver) {
      const stock={};
      zone.querySelectorAll('[data-frise-cadre],[data-frise-borne],[data-frise-date],[data-frise-zoom],[data-frise-position]').forEach(el=>{
        const attribut=['data-frise-cadre','data-frise-borne','data-frise-date','data-frise-zoom','data-frise-position'].find(a=>el.hasAttribute(a));
        stock[`[${attribut}${el.getAttribute(attribut)?'="'+el.getAttribute(attribut)+'"':''}]`]=el.value;
      });
      memoire.set(e.cle,stock);try{sessionStorage.setItem(e.cle,JSON.stringify(stock));}catch(_){}
    }
  }
  document.addEventListener('toggle',ev=>{
    if(ev.target.matches('.frise-details')&&ev.target.open) preparer(ev.target.querySelector('[data-frise-fenetre]'));
  },true);
  function init() {document.querySelectorAll('.frise-details[open] [data-frise-fenetre]').forEach(preparer);}
  document.addEventListener('input',ev=>{const zone=ev.target.closest('[data-frise-fenetre]');if(zone&&ev.target.matches('input[type=range]')) afficher(zone);});
  document.addEventListener('change',ev=>{const zone=ev.target.closest('[data-frise-fenetre]');if(zone&&ev.target.matches('select,input[type=date]')) afficher(zone);});
  document.addEventListener('click',ev=>{
    if(!ev.target.matches('[data-frise-reset]')) return;
    const zone=ev.target.closest('[data-frise-fenetre]'),e=zone.friseFenetre;
    zone.querySelector('[data-frise-cadre]').value='initial';zone.querySelector('[data-frise-zoom]').value='0';zone.querySelector('[data-frise-position]').value='100';
    for(const borne of ['debut','fin']) {zone.querySelector(`[data-frise-borne="${borne}"]`).value=borne;zone.querySelector(`[data-frise-date="${borne}"]`).value=iso(e[borne]);}
    afficher(zone);
  });
  init();document.addEventListener('dossier:actualise',init);document.addEventListener('frises:actualise',init);
})();

/* Retrouver les prestations dépliées après une consultation ou un retour. */
(() => {
  const cle = d => 'pas-frise-prestations:'+d.closest('[data-frise-fenetre]').dataset.compte+':'+location.pathname+':'+d.id;
  const restaurer = () => document.querySelectorAll('.frise-prestations').forEach(d => {
    try {d.open=sessionStorage.getItem(cle(d))==='1';} catch (_) {}
  });
  restaurer();
  document.addEventListener('frises:actualise',restaurer);
  document.addEventListener('toggle',e => {
    if(e.target.matches('.frise-prestations')) {
      try {sessionStorage.setItem(cle(e.target),e.target.open?'1':'0');} catch (_) {}
    }
  },true);
})();
