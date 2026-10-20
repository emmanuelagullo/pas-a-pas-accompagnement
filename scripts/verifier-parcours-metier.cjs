// Parcours fictif CHRS5–7, appelé dans le vrai navigateur/Pyodide du banc PWA.
module.exports = async function verifierParcoursMetier(app) {
  await app.getByRole('link', {name:'Personnes', exact:true}).click();
  await app.getByRole('link', {name:'Thomas (fictif)', exact:true}).click();
  await app.locator('a[href*="/accompagnements/"]').first().click();
  await app.getByRole('heading', {name:/Accompagnement — Thomas/}).waitFor();
  await app.getByRole('link', {name:'Situation et parcours sociaux', exact:true}).click();
  await app.getByRole('link', {name:'Corriger cet événement', exact:true}).click();
  await app.locator('[name=texte]').fill('Installation fictive — texte rectifié pendant l’essai.');
  await app.locator('[name=motif]').fill('Correction fictive du parcours navigateur');
  await app.getByRole('button', {name:'Enregistrer', exact:true}).click();
  await app.getByRole('heading', {name:/Accompagnement — Thomas/}).waitFor();
  await app.getByRole('link', {name:'Consulter l’avant/après des corrections', exact:true}).click();
  await app.getByText('Correction fictive du parcours navigateur', {exact:false}).waitFor();
  await app.getByText('Installation dans un logement autonome fictif.', {exact:false}).waitFor();
  await app.getByRole('link', {name:'Travail du jour', exact:true}).click();
  await app.locator('input[name$="-quantite"]').first().fill('1');
  await app.getByRole('button', {name:'Enregistrer les distributions renseignées', exact:true}).click();
  await app.getByText('1 distribution(s) enregistrée(s).', {exact:true}).waitFor();
  console.log('CHRS5–7 : fiche accompagnement, correction avant/après et distribution du jour : OK');
};
