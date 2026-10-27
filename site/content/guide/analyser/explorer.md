---
title: "Croiser les populations et choisir un relevé"
description: "Construire un rapport sans mélanger unité, personnes et période de référence."
fiche: true
categorie: "analyser"
publics: ["equipe"]
intentions: ["explorer", "croiser", "relevé", "CSV", "filtre", "population"]
prerequis: "Droits de consultation des populations, mesures et critères choisis ; les droits de modèles ne sont nécessaires que pour les conserver ou les échanger."
depart: "Statistiques → Créer un nouveau rapport"
statut: "disponible"
---

Le bloc **Composer un rapport** distingue deux départs :

- **Personnaliser ce rapport** reprend les paramètres du rapport affiché, puis
  permet de les modifier. Si sa définition n'est pas encore transposable
  intégralement, le bouton est désactivé avec une explication sur place.
- **Créer un nouveau rapport** ouvre directement **Retenir**, avec les paramètres
  de départ habituels, indépendants des filtres et du modèle précédents. Aucun
  modèle n'est enregistré tant que vous n'avez pas choisi un nom et confirmé.

Les **Autres rapports disponibles** restent séparés de ces actions. Pour retrouver
un rapport courant après personnalisation, utiliser son lien de retour.

1. Choisir la population réellement étudiée : personnes, demandes, séjours, accords, distributions, appels ou autre population proposée.
2. Renseigner la période et la référence des données personnelles. La référence peut être commune ou suivre la date de chaque fait ou de sa saisie initiale.
3. Modifier directement **Retenir**, **Afficher**, **Compter** ou **Classer** selon le besoin : jusqu'à 7 niveaux de classement et 9 mesures. Chaque partie conserve les paramètres des autres ; aucun assistant n'est imposé.
4. Pour examiner les lignes, choisir un relevé détaillé avec jusqu'à 11 colonnes. Depuis un dossier ouvert par ce relevé, le retour retrouve les critères du rapport ; ce retour privé expire après une journée.
5. Exporter le CSV ou le PDF de la même sélection.

**À vérifier :** plusieurs critères personnels doivent être vérifiés par la même personne. Une mission concerne la prise en charge exacte. Les totaux distincts sont recalculés : les lignes recouvrantes ne s'additionnent pas forcément. Les limites produisent un refus explicite.

Pour les définitions des indicateurs, lire les [statistiques d'activité]({{< relref "/guide/statistiques/" >}}).

## Retenir une personne à un moment du parcours

Dans **Retenir**, le premier ou dernier objet chronologique s'applique **après
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

## Choisir quels objets la période retient

**Retenir** distingue les objets chevauchant la période de ceux dont le début, la fin, ou les deux tombent dans cette période. La fin d’un accord est une fin d’autorisation ; elle ne prouve pas une sortie. Pour les nuitées des épisodes retenus, **Intégralité des épisodes clos** peut dépasser les bornes du rapport. Conserver **Seulement dans la période** pour comparer l’activité d’une même fenêtre.

Les paramètres, les relevés détaillés, CSV et PDF peuvent contenir des données personnelles selon les critères et colonnes choisis. Les conserver et transmettre selon leur contenu ; un export de rapport n’est ni une sauvegarde restaurable ni un document financier émis.
