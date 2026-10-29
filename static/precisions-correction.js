/* Le serveur détermine toujours l'exigence selon l'opération réellement soumise. */
(() => {
  function actualiser(select) {
    const form=select.closest('form'), champ=form?.querySelector('[name=motif]');
    if (!champ) return;
    let etat=select._precision;
    if (!etat) {
      const bloc=champ.closest('p') || champ.parentElement;
      const details=bloc.closest('details.condition-precisions');
      const repere=document.createComment('précision de l’opération');
      (details || bloc).before(repere);
      const groupe=details || document.createElement('details');
      if (!details) {
        groupe.className='condition-precisions';
        const titre=document.createElement('summary');titre.textContent='Précisions facultatives';groupe.append(titre);
        bloc.after(groupe);
      }
      etat=select._precision={bloc,repere,groupe};
    }
    const facultatif=select.dataset.precisionOperation.split(',').includes(select.value);
    champ.required=!facultatif;
    const label=etat.bloc.querySelector('label');
    if (label) label.textContent=facultatif?(select.value==='correction'?'Précision sur la correction (facultative) :':'Précision sur l’opération (facultative) :'):'Justification de l’opération :';
    if (facultatif) etat.groupe.append(etat.bloc);
    else etat.repere.after(etat.bloc);
    etat.groupe.hidden=etat.groupe.children.length===1;
    if (etat.bloc.querySelector('.errorlist')) etat.groupe.open=true;
  }
  function initialiser(racine=document) { racine.querySelectorAll('[data-precision-operation]').forEach(actualiser); }
  document.addEventListener('change',e=>{if(e.target.matches('[data-precision-operation]'))actualiser(e.target);});
  document.addEventListener('condition:form',()=>initialiser());
  new MutationObserver(changes=>{if(changes.some(c=>[...c.addedNodes].some(n=>n.nodeType===1 && (n.matches?.('form,[data-condition-edition]') || n.querySelector?.('[data-precision-operation]')))))initialiser();}).observe(document.body,{childList:true,subtree:true});
  initialiser();
})();
