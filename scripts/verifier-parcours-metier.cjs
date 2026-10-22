// Parcours fictif CHRS5–7, appelé dans le vrai navigateur/Pyodide du banc PWA.
const cliquerLienPwa = require('./cliquer-lien-pwa.cjs');
module.exports = async function verifierParcoursMetier(app) {
  await app.getByRole('link', {name:'Dossiers', exact:true}).click();
  await app.getByLabel('Nom, prénom ou libellé du dossier', {exact:true}).fill('Thomas');
  await app.getByText('Résultats actualisés.', {exact:true}).waitFor();
  await app.locator('#resultats-dossiers ul.resultats-dossiers').getByRole('link', {name:/Thomas — Les Passerelles \(fictif\)/}).click();
  await app.getByRole('heading', {name:/Dossier — Thomas/}).waitFor();
  // Form2 dans le vrai Pyodide : ouvrir puis annuler sans créer de prestation.
  await app.getByRole('link', {name:'Nouveau séjour', exact:true}).click();
  const hebergement = app.locator('#hebergement');
  await hebergement.locator('form[data-prestation-dossier]').waitFor();
  await app.getByRole('heading', {name:/Dossier — Thomas/}).waitFor();
  await app.locator('#repas').waitFor();
  await hebergement.getByRole('button', {name:'← Revenir à la liste', exact:true}).click();
  await app.getByText('Dossier actualisé.', {exact:true}).waitFor();
  await app.locator('nav[aria-label="Dossiers liés"] a').first().click();
  await app.getByRole('link', {name:/Revenir au ménage/}).click();
  await app.getByText('Suivi social et périodes de suivi', {exact:true}).click();
  const periodes = app.locator('details').filter({has: app.locator('summary').filter({hasText: /^Suivi social et périodes de suivi$/})});
  await cliquerLienPwa(periodes.getByRole('link', {name:'Situation et parcours sociaux', exact:true}).first());
  await app.getByRole('heading', {name:/Situation et parcours sociaux — Thomas/}).waitFor();
  await app.getByRole('link', {name:'Corriger cet événement', exact:true}).click();
  await app.locator('[name=texte]').fill('Installation fictive — texte rectifié pendant l’essai.');
  await app.locator('[name=motif]').fill('Correction fictive du parcours navigateur');
  await app.getByRole('button', {name:'Enregistrer', exact:true}).click();
  await app.getByRole('heading', {name:/Dossier — Thomas/}).waitFor();
  await app.getByText('Suivi social et périodes de suivi', {exact:true}).click();
  await cliquerLienPwa(periodes.getByRole('link', {name:'Consulter l’avant/après des corrections', exact:true}).first());
  await app.getByText('Correction fictive du parcours navigateur', {exact:false}).waitFor();
  await app.getByText('Installation dans un logement autonome fictif.', {exact:false}).waitFor();
  await app.getByRole('link', {name:'Travail du jour', exact:true}).click();
  await app.locator('input[name$="-quantite"]').first().fill('1');
  await app.getByRole('button', {name:'Enregistrer les distributions renseignées', exact:true}).click();
  await app.getByText('1 distribution(s) enregistrée(s).', {exact:true}).waitFor();
  console.log('CHRS5–7 : fiche accompagnement, correction avant/après et distribution du jour : OK');
};
