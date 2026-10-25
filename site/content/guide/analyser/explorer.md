---
title: "Croiser les populations et choisir un relevé"
description: "Construire un rapport sans mélanger unité, personnes et période de référence."
fiche: true
categorie: "analyser"
publics: ["equipe"]
intentions: ["explorer", "croiser", "relevé", "CSV", "filtre", "population"]
prerequis: "Un compte disposant des droits de lecture et de saisie de la rubrique concernée."
depart: "Statistiques → Explorer et croiser les populations"
statut: "disponible"
---

1. Choisir la population réellement étudiée : personnes, demandes, séjours, accords, distributions, appels ou autre population proposée.
2. Renseigner la période et la référence des données personnelles. La référence peut être commune ou suivre la date de chaque fait ou de sa saisie initiale.
3. Choisir une mesure et un premier axe. Dans **Affiner**, ajouter au besoin filtres, classes, niveaux de classement ou mesures : jusqu'à 7 axes et 9 mesures.
4. Pour examiner les lignes, choisir un relevé détaillé avec jusqu'à 11 colonnes. Depuis un dossier ouvert par ce relevé, le retour retrouve les critères du rapport ; ce retour privé expire après une journée.
5. Exporter le CSV ou le PDF de la même sélection.

**À vérifier :** plusieurs critères personnels doivent être vérifiés par la même personne. Une mission concerne la prise en charge exacte. Les totaux distincts sont recalculés : les lignes recouvrantes ne s'additionnent pas forcément. Les limites produisent un refus explicite.

Pour les définitions des indicateurs, lire les [statistiques d'activité]({{< relref "/guide/statistiques/" >}}).

## Retenir une personne à un moment du parcours

Dans **Affiner**, le premier ou dernier objet chronologique s'applique **après
les filtres**, pour les mesures de personnes distinctes des prises en charge,
demandes et prestations. Le premier objet de cette sélection n'est pas une
première admission absolue. Avec la référence à la date du fait, l'âge et les
situations sont lus à cette date. Les quantités collectives sont refusées dans
ce mode plutôt que réparties artificiellement.

Les champs d'une même déclaration restent associés : le libellé d'une ressource
et son montant proviennent du même poste, les critères d'une institution de la
même déclaration. Plusieurs déclarations d'une personne ne sont pas combinées
comme si elles n'en formaient qu'une.

L'option **Afficher les sous-totaux des niveaux de classement** recalcule les
personnes et objets de chaque partie. Une nationalité multiple peut produire
plusieurs lignes sans augmenter le sous-total distinct. Les sous-totaux sont
identifiés dans le tableau, le CSV et le PDF ; ne pas les ajouter aux détails.
