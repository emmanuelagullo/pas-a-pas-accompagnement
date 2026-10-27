---
title: "Croiser les populations et choisir un relevé"
description: "Construire un rapport sans mélanger unité, personnes et période de référence."
fiche: true
categorie: "analyser"
publics: ["equipe"]
intentions: ["explorer", "croiser", "relevé", "CSV", "filtre", "population"]
prerequis: "Droits de consultation des populations, mesures et critères choisis ; les droits de modèles ne sont nécessaires que pour les conserver ou les échanger."
depart: "Statistiques → Créer un modèle"
statut: "disponible"
---

Depuis **Gérer les modèles et leurs personnalisations → Créer un modèle**, choisir **Partir de zéro** pour ouvrir directement
**Retenir**, ou partir d’une définition composable proposée ou personnelle.
**Composer à partir de ce rapport** reprend aussi la définition du rapport ouvert
quand sa traduction est fidèle. Les repas, les financements et certains appels 115
sont proposés ; les critères incompatibles ne sont jamais abandonnés.

Un rapport spécialisé conserve ses indicateurs propres : **Conserver ces
réglages…** mémorise ses critères, sans ouvrir une composition libre.

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

## Aller aux faits et revenir au rapport

Les chiffres de l’explorateur ouvrent leurs contributions. Le relevé et la fiche
justificative pointent vers l’accord, le séjour, la distribution, la remise ou la
composante financière précise, avec la version du calcul lorsqu’elle est connue.
Le lien **Revenir aux résultats du rapport** retrouve critères et page. Les menus
habituels du dossier et de la prestation restent disponibles. Le retour privé
expire après une journée et ne donne aucun droit supplémentaire.

Les liens des rapports spécialisés conservent également leur rapport d’origine.
Les chiffres sont recalculés selon les faits actuellement connus ; les modèles
enregistrent des paramètres, pas des résultats figés.

## Vérifier les unités et les contributions

Les **durées civiles des épisodes clos** restent des jours, sans multiplication
par leurs bénéficiaires. La moyenne est arrondie au dixième. Les **participations**
comptent les bénéficiaires par épisode, et peuvent dépasser le nombre de personnes
distinctes. Les **nuits distinctes** dédoublonnent les paires personne/nuit ;
l’option hors absences retire les contributions concernées, sans prouver une
présence constatée. Les liens des chiffres expliquent les contributions retenues,
les doublons et les absences. Les totaux et sous-totaux se recalculent.

Les définitions et personnalisations enregistrées s’ouvrent avec les quatre
parties de composition fermées ; choisir **Modifier** sur la partie voulue pour
l’approfondir. Les règles temporelles se choisissent sans assistant obligatoire.
