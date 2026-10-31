/* Déplacements locaux uniquement : aucune lecture serveur et aucune mutation de vue. */
(() => {
  if (!document.querySelector('.condition-acces')) return;
  const large = matchMedia('(min-width: 80rem)');
  const html = document.documentElement;
  let ouvert = false, observer, frame = 0, mesure = 0;
  const tailles = window.ResizeObserver ? new ResizeObserver(mesurer) : null;
  let visibles = new Set(), liens = [], barre, dernier, ancienSommaire, branches;
  let hauteurNormale = innerHeight, sommaireParcouru = false;
  function suivreSommaire() {
    const nav = panneau();
    if (!large.matches || !nav || nav.hidden || sommaireParcouru || nav.contains(document.activeElement)) return;
    let repere = nav.querySelector('a[aria-current="location"]');
    if (!repere) return;
    for (let parent = repere.parentElement; parent && parent !== nav; parent = parent.parentElement) {
      if (parent.matches("details:not([open])")) repere = parent.querySelector(":scope > summary");
    }
    const cadre = nav.getBoundingClientRect(), rect = repere.getBoundingClientRect();
    // Déplacer uniquement le panneau, sans animation ni changement du focus.
    if (rect.top < cadre.top + 8) nav.scrollTop += rect.top - cadre.top - 8;
    else if (rect.bottom > cadre.bottom - 8) nav.scrollTop += rect.bottom - cadre.bottom + 8;
  }
  let ancreInitiale = location.hash.startsWith('#evolution-') ? location.hash : '';
  const panneau = () => document.getElementById('sommaire-dossier');
  const bouton = () => document.querySelector('[data-sommaire-ouvrir]');
  const visible = element => element && !element.closest('[hidden]') &&
    !element.parentElement?.closest('details:not([open])') && element.getClientRects().length;
  const cible = hash => {
    try { return document.getElementById(decodeURIComponent(hash.slice(1))); }
    catch (_) { return null; }
  };
  function fermer(revenir = false) {
    ouvert = false;
    appliquerPanneau();
    if (revenir && !large.matches) bouton()?.focus({preventScroll: true});
  }
  function appliquerPanneau() {
    const nav = panneau();
    if (!nav) return;
    nav.hidden = !large.matches && !ouvert;
    bouton()?.setAttribute('aria-expanded', String(ouvert && !large.matches));
    nav.querySelector('[data-sommaire-fermer]').hidden = large.matches;
  }
  function position(element) {
    if (!element) return;
    dernier = element;
    const social = element.closest('#condition-sociale');
    document.querySelectorAll('[data-navigation-bloc]').forEach(link => {
      const bloc = cible(link.hash);
      const rubrique = bloc?.id === 'titre-prestations' ? bloc.parentElement : bloc;
      const courant = social ? bloc?.id === 'condition-sociale' :
        Boolean(rubrique && (rubrique === element || rubrique.contains(element)));
      if (courant) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    liens.forEach(link => {
      if (link.hash === '#' + element.id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    document.querySelectorAll('.condition-nav-details').forEach(detail => {
      const dedans = Boolean(detail.querySelector('a[aria-current="location"]'));
      detail.toggleAttribute('data-navigation-active', dedans);
      const resume = detail.querySelector(':scope > summary');
      if (dedans && !detail.open) resume.setAttribute('aria-current', 'location');
      else resume.removeAttribute('aria-current');
    });
    const personne = element.closest('.condition-personne');
    document.querySelectorAll('[data-person-nav]').forEach(item =>
      item.classList.toggle('is-current', Boolean(personne && item.dataset.personNav === personne.id)));
    suivreSommaire();
  }
  function observerPosition() {
    observer?.disconnect();
    visibles = new Set();
    liens = [...document.querySelectorAll('.condition-menu a')].filter(link => !link.closest('.condition-menu [hidden]'));
    // Inclure les liens des dépliants fermés, mais jamais ceux de l'autre vue.
    const elements = [...new Set(liens.map(link => cible(link.hash)).filter(visible))];
    if (!window.IntersectionObserver) return;
    observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) visibles.add(entry.target);
        else visibles.delete(entry.target);
      });
      const courants = [...visibles].filter(visible);
      courants.sort((a, b) => {
        // Favoriser la sous-rubrique plutôt que son conteneur.
        if (a.contains(b)) return 1;
        if (b.contains(a)) return -1;
        return Math.abs(a.getBoundingClientRect().top - innerHeight * .15) -
          Math.abs(b.getBoundingClientRect().top - innerHeight * .15);
      });
      if (courants.length) position(courants[0]);
    }, {rootMargin: '-10% 0px -65% 0px'});
    elements.forEach(element => observer.observe(element));
  }
  function rafraichir() {
    const nav = panneau();
    if (!nav) return;
    if (nav !== ancienSommaire && branches) {
      nav.querySelectorAll('.condition-nav-details').forEach((detail, index) => { detail.open = Boolean(branches[index]); });
    }
    ancienSommaire = nav;
    html.classList.add('navigation-interactive');
    const nouvelleBarre = document.querySelector('.condition-acces');
    if (barre !== nouvelleBarre) {
      tailles?.disconnect();
      barre = nouvelleBarre;
      if (barre) tailles?.observe(barre);
    }
    bouton().hidden = false;
    document.querySelector('[data-sommaire-repli]').hidden = true;
    const evolution = document.querySelector('[data-condition-evolution-panel]');
    const enEvolution = evolution && !evolution.hidden;
    nav.querySelector('[data-navigation-situation]').hidden = Boolean(enEvolution);
    nav.querySelector('[data-navigation-evolution]').hidden = !enEvolution;
    nav.querySelectorAll('[data-navigation-evolution] a').forEach(link => {
      link.closest('li').hidden = !cible(link.hash);
    });
    appliquerPanneau();
    observerPosition();
    const actuel = cible(location.hash);
    if (visible(actuel)) position(actuel);
    else if (actuel?.closest('[data-condition-volet]:not([open])')) position(document.querySelector('[data-condition-volet]'));
    mesurer();
    if (ancreInitiale && cible(ancreInitiale) && !cible(ancreInitiale).closest('[hidden]')) {
      const hash = ancreInitiale; ancreInitiale = '';
      rejoindre(hash, false);
    }
  }
  function planifier() {
    if (frame) return;
    frame = requestAnimationFrame(() => { frame = 0; rafraichir(); });
  }
  function rejoindre(hash, historique = true) {
    let element = cible(hash);
    // Une ancienne ancre ne doit jamais abandonner une édition ni changer de vue.
    if (element?.closest('[hidden]')) element = document.getElementById('condition-sociale');
    if (!element) return;
    for (let parent = element; parent; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
    fermer();
    if (historique) {
      const url = new URL(location.href);
      url.hash = element.id;
      history.replaceState(history.state, '', url);
    }
    const titre = element.matches('h1,h2,h3,h4') ? element :
      element.querySelector('h1,h2,h3,h4') || element;
    if (!titre.hasAttribute('tabindex')) titre.tabIndex = -1;
    titre.focus({preventScroll: true});
    element.scrollIntoView({block: 'start', behavior: 'instant'});
    position(element);
  }
  function assurerFocus() {
    const element = document.activeElement;
    if (!element || element === document.body || element.closest('.condition-acces,.condition-sommaire')) return;
    const rect = element.getBoundingClientRect();
    const viewport = window.visualViewport;
    const haut = viewport?.offsetTop || 0;
    const bas = haut + (viewport?.height || innerHeight) - (!large.matches && !html.classList.contains('condition-clavier') ? barre?.offsetHeight || 0 : 0);
    if (rect.bottom > bas - 12 || rect.top < haut + 12) element.scrollIntoView({block: 'nearest', behavior: 'instant'});
  }
  function mesurer() {
    if (mesure) return;
    mesure = requestAnimationFrame(() => {
      mesure = 0;
      const edition = document.activeElement?.matches('input:not([type=radio]):not([type=checkbox]),textarea,select,[contenteditable=true]');
      const viewport = window.visualViewport;
      if (!edition) hauteurNormale = innerHeight;
      const clavier = edition && (!viewport || viewport.scale === 1) &&
        Math.max(hauteurNormale, innerHeight) - (viewport?.height || innerHeight) > 150;
      html.classList.toggle('condition-clavier', Boolean(clavier));
      if (barre?.offsetHeight) html.style.setProperty('--navigation-hauteur', barre.offsetHeight + 'px');
      assurerFocus();
    });
  }
  document.addEventListener('click', event => {
    if (event.target.closest('[data-sommaire-ouvrir]')) {
      ouvert = !ouvert;
      appliquerPanneau();
      if (ouvert) document.getElementById('titre-sommaire').focus({preventScroll: true});
      return;
    }
    if (event.target.closest('[data-sommaire-fermer]')) { fermer(true); return; }
    const link = event.target.closest('.condition-menu a,.condition-acces a,.condition-ancres a,.condition-sommaire .retour-haut');
    if (link && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey && event.button === 0) {
      event.preventDefault();
      rejoindre(link.hash);
    } else if (ouvert && !event.target.closest('.condition-sommaire,.condition-acces')) fermer();
  });
  document.addEventListener('toggle', event => {
    if (event.target.matches('.condition-nav-details')) {
      branches = [...panneau().querySelectorAll('.condition-nav-details')].map(detail => detail.open);
      if (dernier?.isConnected) position(dernier);
    }
  }, true);
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && ouvert) { event.preventDefault(); fermer(true); }
  });
  // Fermer un panneau non modal lorsque le clavier quitte sa navigation.
  document.addEventListener('focusin', event => {
    if (ouvert && !event.target.closest('.condition-sommaire,.condition-acces')) fermer();
    mesurer();
  });
  document.addEventListener('pointerover', event => {
    const nav = panneau();
    if (nav?.contains(event.target)) sommaireParcouru = true;
  });
  document.addEventListener('pointerout', event => {
    const nav = panneau();
    if (nav?.contains(event.target) && !nav.contains(event.relatedTarget)) {
      sommaireParcouru = false; suivreSommaire();
    }
  });
  document.addEventListener('focusout', () => { mesurer(); requestAnimationFrame(suivreSommaire); });
  ['condition:vue', 'navigation:actualise', 'dossier:actualise', 'condition:depliements'].forEach(nom =>
    document.addEventListener(nom, planifier));
  large.addEventListener('change', () => {
    const focusPanneau = panneau()?.contains(document.activeElement);
    ouvert = false;
    rafraichir();
    if (!large.matches && focusPanneau) bouton()?.focus({preventScroll: true});
  });
  window.addEventListener('hashchange', () => rejoindre(location.hash, false));
  window.addEventListener('resize', mesurer);
  window.visualViewport?.addEventListener('resize', mesurer);
  // Un lien direct vers Évolution demande explicitement cette vue au chargement,
  // avant toute saisie. Les déplacements ultérieurs ne changent jamais de vue.
  document.addEventListener('DOMContentLoaded', () => {
    if (ancreInitiale) document.querySelector('[data-condition-evolution]:not(:disabled)')?.click();
  }, {once: true});
  rafraichir();
  if (location.hash && cible(location.hash) && !location.hash.startsWith('#frise-')) rejoindre(location.hash, false);
})();
