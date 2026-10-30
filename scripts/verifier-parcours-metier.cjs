// Parcours fictif BD6 et CHRS5–7 dans le vrai navigateur/Pyodide.
const assert = require('node:assert/strict');
const cliquerLienPwa = require('./cliquer-lien-pwa.cjs');
module.exports = async function verifierParcoursMetier(app) {
  async function rejoindreBloc(ancre) {
    const acces = app.locator('.condition-acces');
    const navigation = await acces.isVisible() ? acces : app.locator('.condition-sommaire');
    // Une ancre ne recharge pas l'iframe : ne pas attendre framenavigated.
    await navigation.locator('a[href="#' + ancre + '"]').click();
  }
  await cliquerLienPwa(app.getByRole('navigation', {name:'Navigation principale', exact:true}).getByRole('link', {name:'Dossiers', exact:true}));
  await app.getByLabel('Nom, prénom ou libellé du dossier', {exact:true}).fill('Thomas');
  await app.getByText('Résultats actualisés.', {exact:true}).waitFor();
  await cliquerLienPwa(app.locator('#resultats-dossiers ul.resultats-dossiers').getByRole('link', {name:/Thomas — Établissement Les Passerelles \(fictif\)/}));
  await app.getByRole('heading', {name:/Dossier — Thomas/}).waitFor();
  await rejoindreBloc('prises');
  await cliquerLienPwa(app.locator('.condition-personne').first().getByRole('link', {name:'Dossier individuel', exact:true}));
  await cliquerLienPwa(app.getByRole('link', {name:/Revenir au ménage/}));
  // La recette de saisie complète ouvre les rubriques par leur commande.
  await app.getByRole('button', {name:'Tout déplier', exact:true}).click();
  // Commentaire append-only dans le dossier, avant d’ouvrir sa prise.
  await cliquerLienPwa(app.locator('.bd-commentaire').getByRole('link', {name:'Modifier', exact:true}));
  const commentaire = app.locator('.edition-texte .ProseMirror');
  await commentaire.waitFor();
  await commentaire.fill('Commentaire fictif de la recette BD6.');
  await commentaire.press('ControlOrMeta+a');
  await app.getByRole('button', {name:'Gras', exact:true}).click();
  await cliquerLienPwa(app.getByRole('button', {name:'Enregistrer', exact:true}));
  await app.locator('.texte-narratif strong').filter({hasText:'Commentaire fictif de la recette BD6.'}).waitFor();
  await cliquerLienPwa(app.getByRole('button', {name:'Ouvrir', exact:true}));
  await app.getByRole('heading', {name:/Prise en charge du/}).waitFor();
  await rejoindreBloc('titre-prestations');
  await rejoindreBloc('condition-sociale');
  // Form3 : ouvrir puis annuler sans créer de prestation et sans quitter la prise.
  await app.getByRole('link', {name:'Nouveau séjour', exact:true}).click();
  const hebergement = app.locator('#hebergement');
  await hebergement.locator('form[data-prestation-dossier]').waitFor();
  await app.getByRole('heading', {name:/Prise en charge du/}).waitFor();
  await app.locator('#repas').waitFor();
  await hebergement.getByRole('button', {name:'← Revenir à la liste', exact:true}).click();
  await app.getByText('Dossier actualisé.', {exact:true}).waitFor();
  // Même formulaire pour l’accueil prévu, puis confirmation de l’arrivée.
  await app.getByRole('link', {name:'Nouveau séjour', exact:true}).click();
  await hebergement.getByLabel('Arrivée déjà effectuée', {exact:false}).uncheck();
  await hebergement.getByRole('button', {name:'Enregistrer le séjour', exact:true}).click();
  await app.getByText('Dossier actualisé.', {exact:true}).waitFor();
  await app.getByText('Prévu — arrivée à confirmer', {exact:true}).waitFor();
  await app.getByRole('link', {name:'Enregistrer l’arrivée', exact:true}).click();
  await hebergement.getByRole('button', {name:'Enregistrer l’arrivée', exact:true}).click();
  await app.getByText('Dossier actualisé.', {exact:true}).waitFor();
  await app.getByText('Prévu — arrivée à confirmer', {exact:true}).waitFor({state:'hidden'});
  const historique = app.locator('.bd-dossier');
  await cliquerLienPwa(historique.getByRole('link', {name:'Informations conservées des anciens suivis', exact:true}));
  await app.getByRole('heading', {name:/Situation et parcours sociaux — Thomas/}).waitFor();
  await cliquerLienPwa(app.getByRole('link', {name:'Corriger cet événement', exact:true}));
  // L’événement social reste un texte simple ; seuls les commentaires et
  // bilans de ce parcours activent l’éditeur enrichi.
  await app.getByRole('heading', {name:/Corriger une saisie/}).waitFor();
  const evenement = app.locator('textarea[name=texte]:not([data-texte-riche])');
  await evenement.waitFor();
  await evenement.fill('Installation fictive — texte rectifié pendant l’essai.');
  // Une correction ordinaire peut être enregistrée sans précision. Ici on
  // choisit d’en fournir une pour vérifier sa restitution dans l’historique.
  const precision = app.locator('[name=motif]');
  assert.equal(await precision.isVisible(), false);
  assert.equal(await precision.getAttribute('required'), null);
  await precision.locator('xpath=ancestor::details[1]').locator(':scope > summary').click();
  await precision.fill('Correction fictive du parcours navigateur');
  await cliquerLienPwa(app.getByRole('button', {name:'Enregistrer', exact:true}));
  await app.getByRole('heading', {name:/Prise en charge du/}).waitFor();
  await cliquerLienPwa(historique.getByRole('link', {name:'Historique des corrections', exact:true}));
  await app.getByText('Correction fictive du parcours navigateur', {exact:false}).waitFor();
  await app.getByText('Installation dans un logement autonome fictif.', {exact:false}).waitFor();
  await app.locator('.menu-chantiers > summary').click();
  await cliquerLienPwa(app.getByRole('link', {name:'Travail du jour', exact:true}));
  await app.locator('input[name$="-quantite"]').first().fill('1');
  await cliquerLienPwa(app.getByRole('button', {name:'Enregistrer les distributions renseignées', exact:true}));
  await app.getByText('1 distribution(s) enregistrée(s).', {exact:true}).waitFor();
  console.log('BD6 et CHRS5–7 : dossier, prise, formulaire en place, correction et distribution : OK');
};
