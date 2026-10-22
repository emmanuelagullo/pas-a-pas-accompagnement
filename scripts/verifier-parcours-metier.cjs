// Parcours fictif BD6 et CHRS5–7 dans le vrai navigateur/Pyodide.
const cliquerLienPwa = require('./cliquer-lien-pwa.cjs');
module.exports = async function verifierParcoursMetier(app) {
  await cliquerLienPwa(app.getByRole('link', {name:'Dossiers', exact:true}));
  await app.getByLabel('Nom, prénom ou libellé du dossier', {exact:true}).fill('Thomas');
  await app.getByText('Résultats actualisés.', {exact:true}).waitFor();
  await cliquerLienPwa(app.locator('#resultats-dossiers ul.resultats-dossiers').getByRole('link', {name:/Thomas — Les Passerelles \(fictif\)/}));
  await app.getByRole('heading', {name:/Dossier — Thomas/}).waitFor();
  await app.getByText('Composition du ménage et changements', {exact:true}).click();
  await cliquerLienPwa(app.locator('nav[aria-label="Dossiers liés"] a').first());
  await cliquerLienPwa(app.getByRole('link', {name:/Revenir au ménage/}));
  // Commentaire append-only dans le dossier, avant d’ouvrir sa prise.
  await cliquerLienPwa(app.locator('.bd-commentaire').getByRole('link', {name:'Modifier', exact:true}));
  await app.getByLabel('Commentaire libre', {exact:false}).fill('Commentaire fictif de la recette BD6.');
  await cliquerLienPwa(app.getByRole('button', {name:'Enregistrer', exact:true}));
  await app.getByText('Commentaire fictif de la recette BD6.', {exact:true}).waitFor();
  await cliquerLienPwa(app.getByRole('button', {name:'Ouvrir', exact:true}));
  await app.getByRole('heading', {name:/Prise en charge du/}).waitFor();
  // Form3 : ouvrir puis annuler sans créer de prestation et sans quitter la prise.
  await app.getByRole('link', {name:'Nouveau séjour', exact:true}).click();
  const hebergement = app.locator('#hebergement');
  await hebergement.locator('form[data-prestation-dossier]').waitFor();
  await app.getByRole('heading', {name:/Prise en charge du/}).waitFor();
  await app.locator('#repas').waitFor();
  await hebergement.getByRole('button', {name:'← Revenir à la liste', exact:true}).click();
  await app.getByText('Dossier actualisé.', {exact:true}).waitFor();
  const historique = app.locator('details').filter({has: app.locator('summary').filter({hasText: /^Projet, notes et historique de la prise$/})});
  await historique.locator('summary').click();
  await cliquerLienPwa(historique.getByRole('link', {name:'Situation et parcours sociaux', exact:true}));
  await app.getByRole('heading', {name:/Situation et parcours sociaux — Thomas/}).waitFor();
  await cliquerLienPwa(app.getByRole('link', {name:'Corriger cet événement', exact:true}));
  await app.locator('[name=texte]').fill('Installation fictive — texte rectifié pendant l’essai.');
  await app.locator('[name=motif]').fill('Correction fictive du parcours navigateur');
  await cliquerLienPwa(app.getByRole('button', {name:'Enregistrer', exact:true}));
  await app.getByRole('heading', {name:/Prise en charge du/}).waitFor();
  await historique.locator('summary').click();
  await cliquerLienPwa(historique.getByRole('link', {name:'Consulter l’avant/après des corrections', exact:true}));
  await app.getByText('Correction fictive du parcours navigateur', {exact:false}).waitFor();
  await app.getByText('Installation dans un logement autonome fictif.', {exact:false}).waitFor();
  await cliquerLienPwa(app.getByRole('link', {name:'Travail du jour', exact:true}));
  await app.locator('input[name$="-quantite"]').first().fill('1');
  await cliquerLienPwa(app.getByRole('button', {name:'Enregistrer les distributions renseignées', exact:true}));
  await app.getByText('1 distribution(s) enregistrée(s).', {exact:true}).waitFor();
  console.log('BD6 et CHRS5–7 : dossier, prise, formulaire en place, correction et distribution : OK');
};
