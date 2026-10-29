import { Editor } from '@tiptap/core';
import Document from '@tiptap/extension-document';
import Text from '@tiptap/extension-text';
import Paragraph from '@tiptap/extension-paragraph';
import Bold from '@tiptap/extension-bold';
import Italic from '@tiptap/extension-italic';
import HardBreak from '@tiptap/extension-hard-break';
import Link from '@tiptap/extension-link';
import { BulletList, OrderedList, ListItem } from '@tiptap/extension-list';
import { UndoRedo } from '@tiptap/extensions';

const instances = new Map();
const urlValide = value => {
  if (!value || value.length > 2048 || /[\s\x00-\x1f\x7f\\]/.test(value)) return false;
  try { const u = new URL(value); return ['http:', 'https:'].includes(u.protocol) && !!u.hostname && !u.username && !u.password; }
  catch { return false; }
};
const paragraphes = texte => ({type: 'doc', content: texte.split('\n').map(t => ({type: 'paragraph', ...(t ? {content: [{type: 'text', text: t}]} : {})}))});
// Ne sérialiser que les attributs du format applicatif v1.
function documentV1(node) {
  const result = {type: node.type};
  if (node.text !== undefined) result.text = node.text;
  if (node.content) result.content = node.content.map(documentV1);
  if (node.type === 'orderedList') result.attrs = {start: node.attrs?.start ?? 1};
  if (node.marks?.length) result.marks = node.marks.map(m => m.type === 'link' ? {type: m.type, attrs: {href: m.attrs.href}} : {type: m.type});
  return result;
}
function projection(n) {
  if (n.type === 'text') return n.text;
  if (n.type === 'hardBreak') return '\n';
  return (n.content || []).map(projection).join(n.type === 'paragraph' ? '' : '\n');
}
function bouton(texte, action) {
  const b = document.createElement('button'); b.type = 'button'; b.className = 'secondaire'; b.textContent = texte;
  b.addEventListener('click', action); return b;
}
function initialiser(ta) {
  if (instances.has(ta)) return;
  const hidden = ta.nextElementSibling;
  if (!hidden?.matches('[data-document-riche]')) return;
  let initial;
  try { initial = hidden.value ? JSON.parse(hidden.value).doc : paragraphes(ta.value); }
  catch { return; } // Document illisible : conserver le formulaire original, jamais le réinterpréter.
  const wrapper = document.createElement('div'); wrapper.className = 'edition-texte';
  const toolbar = document.createElement('div'); toolbar.className = 'edition-outils'; toolbar.setAttribute('role', 'group'); toolbar.setAttribute('aria-label', 'Mise en forme');
  const surface = document.createElement('div');
  const etat = document.createElement('p'); etat.className = 'helptext edition-etat';
  const aide = document.createElement('p'); aide.className = 'helptext'; aide.id = ta.id + '-edition-aide'; aide.textContent = 'La mise en forme visible sera conservée. Cliquez sur Enregistrer pour confirmer.';
  const erreur = document.createElement('p'); erreur.className = 'errorlist'; erreur.setAttribute('role', 'alert');
  const lien = document.createElement('div'); lien.className = 'edition-lien'; lien.hidden = true;
  const etiquette = document.createElement('label'); etiquette.textContent = 'Adresse du lien'; etiquette.htmlFor = ta.id + '-adresse';
  const adresse = document.createElement('input'); adresse.id = etiquette.htmlFor; adresse.type = 'url'; adresse.placeholder = 'https://exemple.fr'; adresse.autocomplete = 'off';
  const aideLien = document.createElement('p'); aideLien.className = 'helptext'; aideLien.id = ta.id + '-aide-lien'; aideLien.textContent = 'Sélectionnez le texte puis indiquez une adresse web complète. Le lien s’ouvrira dans un nouvel onglet en lecture.'; adresse.setAttribute('aria-describedby', aideLien.id);
  ta.before(wrapper); wrapper.append(toolbar, surface, aide, etat, erreur, lien);
  let derniereSelection = null, editeur;
  const marques = [];
  const format = (libelle, type, methode) => {
    const b = bouton(libelle, () => {
      const {from,to}=editeur.state.selection;
      editeur.chain().focus().setTextSelection({from,to})[methode]().run();
    });
    b.setAttribute('aria-pressed', 'false'); marques.push([b, type]); toolbar.append(b);
  };
  format('Gras', 'bold', 'toggleBold'); format('Italique', 'italic', 'toggleItalic');
  format('Liste à puces', 'bulletList', 'toggleBulletList'); format('Liste numérotée', 'orderedList', 'toggleOrderedList');
  const fermerLien = () => { lien.hidden = true; editeur.commands.focus(); };
  const ouvrirLien = () => {
    derniereSelection = {from: editeur.state.selection.from, to: editeur.state.selection.to};
    adresse.value = editeur.getAttributes('link').href || '';
    lien.hidden = false; adresse.focus();
  };
  toolbar.append(bouton('Lien', ouvrirLien), bouton('Annuler', () => editeur.chain().focus().undo().run()), bouton('Rétablir', () => editeur.chain().focus().redo().run()));
  const avecSelection = () => editeur.chain().focus().setTextSelection(derniereSelection).extendMarkRange('link');
  const appliquerLien = () => {
    if (!urlValide(adresse.value)) { erreur.textContent = 'Indiquez une adresse complète commençant par https:// ou http://.'; adresse.setAttribute('aria-invalid', 'true'); return; }
    const chaine = avecSelection();
    if (derniereSelection.from === derniereSelection.to && !editeur.isActive('link')) chaine.insertContent({type: 'text', text: adresse.value, marks: [{type: 'link', attrs: {href: adresse.value}}]}).run();
    else chaine.setLink({href: adresse.value}).run();
    adresse.removeAttribute('aria-invalid'); erreur.textContent = ''; fermerLien();
  };
  lien.append(etiquette, adresse, aideLien, bouton('Appliquer le lien', appliquerLien), bouton('Retirer le lien', () => { avecSelection().unsetLink().run(); fermerLien(); }), bouton('Fermer', fermerLien));
  lien.addEventListener('keydown', e => { if (e.key === 'Escape') { e.preventDefault(); fermerLien(); } if (e.key === 'Enter') { e.preventDefault(); appliquerLien(); } });
  toolbar.addEventListener('mousedown', e => { if (e.target.closest('button')) e.preventDefault(); });
  const etiquettes = [...document.querySelectorAll('label')].filter(l => l.htmlFor === ta.id);
  const ancienId = ta.id, idEditeur = ancienId + '-visuel';
  etiquettes.forEach((l, i) => {if (!l.id) l.id = ancienId + '-etiquette-' + i;});
  const focusLabel = e => { e.preventDefault(); editeur.commands.focus(); };
  let touche = !!hidden.value;
  function synchroniser(notifier = false) {
    const doc = documentV1(editeur.getJSON());
    const texte = projection(doc).trim();
    // Une simple ouverture ne convertit pas les anciens textes.
    if (touche) { hidden.value = JSON.stringify({version: 1, doc}); ta.value = texte; }
    const max = Number(ta.dataset.maxTexte || 0), longueur = Array.from(texte).length;
    etat.textContent = max ? `${longueur} / ${max} caractères` : `${longueur} caractères`;
    erreur.textContent = max && longueur > max ? `Le texte dépasse la limite de ${max} caractères.` : '';
    marques.forEach(([b, type]) => b.setAttribute('aria-pressed', String(editeur.isActive(type))));
    if (notifier) ta.dispatchEvent(new Event('input', {bubbles: true}));
  }
  try {
    editeur = new Editor({
      element: surface,
      extensions: [Document, Text, Paragraph, Bold, Italic, HardBreak, BulletList, OrderedList, ListItem, UndoRedo,
        Link.configure({openOnClick: false, autolink: false, linkOnPaste: false, isAllowedUri: urlValide})],
      content: initial,
      enableInputRules: false, // Une frappe de * ou # ne devient pas un balisage inattendu.
      enablePasteRules: false,
      editorProps: {
        attributes: {id: idEditeur, role: 'textbox', 'aria-multiline': 'true', 'aria-labelledby': etiquettes.map(l => l.id).join(' '), lang: 'fr', spellcheck: 'true', 'aria-describedby': [ta.getAttribute('aria-describedby'), aide.id].filter(Boolean).join(' '), ...(ta.getAttribute('aria-invalid') ? {'aria-invalid': 'true'} : {})},
        handleKeyDown: (_view, e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); ouvrirLien(); return true; } return false; },
        handleDOMEvents: {drop: (_view, e) => { e.preventDefault(); return true; }},
        transformPastedHTML: html => {
          const doc = new DOMParser().parseFromString(html, 'text/html');
          doc.querySelectorAll('script,style,img,svg,iframe,object,video,audio').forEach(n => n.remove());
          doc.querySelectorAll('a').forEach(a => { if (!urlValide(a.getAttribute('href'))) a.replaceWith(...a.childNodes); });
          return doc.body.innerHTML; // ProseMirror garde seulement les nœuds du schéma.
        },
      },
      onUpdate: () => { touche = true; synchroniser(true); },
      onSelectionUpdate: () => { if (editeur) marques.forEach(([b, type]) => b.setAttribute('aria-pressed', String(editeur.isActive(type)))); },
    });
    // Aucun contenu collé n'est injecté directement dans le DOM par notre code.
    ta.hidden = true; ta.required = false;
    etiquettes.forEach(l => { l.htmlFor = idEditeur; l.addEventListener('click', focusLabel); });
    synchroniser();
    const form = ta.form;
    const avantEnvoi = e => {
      // Prendre en compte la dernière mutation DOM avant de valider le document.
      editeur.view.domObserver.flush();
      synchroniser();
      const valeur = projection(documentV1(editeur.getJSON())).trim();
      const max = Number(ta.dataset.maxTexte || 0);
      if ((ta.dataset.texteObligatoire === '1' && !valeur) || (max && Array.from(valeur).length > max) || hidden.value.length > 65536) {
        e.preventDefault(); e.stopImmediatePropagation(); erreur.textContent = !valeur ? 'Le texte est obligatoire.' : 'Le texte est trop long ou trop complexe.';
        // Un focus différé peut rétablir une sélection périmée après la frappe suivante.
        editeur.view.focus();
      }
    };
    form?.addEventListener('submit', avantEnvoi, true);
    const desactiver = new MutationObserver(() => editeur.setEditable(!ta.disabled));
    desactiver.observe(ta, {attributes: true, attributeFilter: ['disabled']});
    instances.set(ta, {wrapper, editeur, detruire() {desactiver.disconnect(); form?.removeEventListener('submit', avantEnvoi, true); etiquettes.forEach(l => {l.htmlFor = ancienId; l.removeEventListener('click', focusLabel);}); editeur.destroy(); }});
  } catch (e) {
    editeur?.destroy(); wrapper.remove(); ta.hidden = false;
    // Ne pas masquer l'erreur dans les consoles de qualification.
    console.error('Initialisation de l’éditeur impossible', e);
  }
}
window.PasTextes = {
  mention(ta) {
    const editeur = instances.get(ta)?.editeur;
    if (!editeur || !editeur.state.selection.empty) return null;
    const {from, $from} = editeur.state.selection;
    const prefixe = $from.parent.textBetween(0, $from.parentOffset, '\n');
    const trouve = prefixe.match(/(?:^|\s)@([^@\n]{0,60})$/);
    return trouve ? {from: from - trouve[1].length - 1, to: from, query: trouve[1], rect: editeur.view.coordsAtPos(from)} : null;
  },
  insererMention(ta, position, label) {
    const editeur = instances.get(ta)?.editeur;
    if (!editeur || editeur.state.doc.textBetween(position.from, position.to) !== '@' + position.query) return false;
    return editeur.chain().focus().setTextSelection({from: position.from, to: position.to}).insertContent({type: 'text', text: '@' + label + ' '}).run();
  },
  initialiser(root = document) {root.querySelectorAll('textarea[data-texte-riche]').forEach(initialiser);},
  nettoyer() { for (const [ta, instance] of instances) if (!ta.isConnected) {instance.detruire(); instances.delete(ta);} },
};
