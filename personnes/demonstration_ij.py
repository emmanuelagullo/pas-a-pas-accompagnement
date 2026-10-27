from acteurs.contexte import service_metier
"""Un fait erroné conservé, exclusivement lors de la génération du jeu neuf."""
from datetime import timedelta
from . import models as m,hebergement as h,annulations_arrivees as erreurs,accords


@service_metier
def completer(acteur,personnes,suivis,jour):
    prise=suivis['Robin A'];prise.refresh_from_db()
    debut=max(prise.debut,min(jour-timedelta(days=3),prise.fin-timedelta(days=1)) if prise.fin else jour-timedelta(days=3))
    accord=h.accorder(acteur,prise,[personnes['Robin A']],debut,prise.fin)
    sejour=h.admettre(acteur,accord,[personnes['Robin A']],debut)
    lieu=m.LieuHebergement.objects.order_by('pk').first()
    if lieu:h.ajouter_periode(acteur,sejour,debut,None,lieu)
    erreurs.annuler(acteur,sejour,erreurs.jeton(sejour),'Homonymes fictifs confondus : cette arrivée n’a jamais eu lieu ; périodes conservées pour la recette')
    accord.refresh_from_db()
    accords.annuler(acteur,accord,'Autorisation fictive saisie pour le mauvais homonyme',accords.jeton(accord))
