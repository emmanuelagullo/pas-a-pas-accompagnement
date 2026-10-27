---
title: "Lire les statistiques d’activité"
description: "Choisir une période et interpréter des indicateurs comparables."
fiche: true
categorie: "analyser"
publics: ["equipe"]
intentions: ["statistiques", "bilan", "nuitées", "repas", "CSV", "compteur"]
prerequis: "Droits de consultation des statistiques et des données du rapport choisi ; aucun droit de saisie n’est nécessaire pour lire un rapport."
depart: "Navigation → Statistiques"
statut: "disponible"
---

1. Choisir une période rapide ou un début inclus et une fin exclue.
2. Sélectionner **Synthèse**, **Hébergement**, **Repas**, **Évolution mensuelle** ou l'exploration spécialisée proposée.
3. Lire la définition de la mesure avant de comparer les valeurs. Exporter le CSV du rapport choisi, ou utiliser son impression lorsqu'elle est proposée.

Le bloc **Composer un rapport** permet de reprendre le rapport affiché avec
**Personnaliser ce rapport**, lorsque sa définition est compatible, ou de
**Créer un nouveau rapport** indépendant. Une limite de personnalisation est
expliquée avant le clic ; elle ne change pas les indicateurs du rapport courant.
Les liens vers les rapports spécialisés sont regroupés sous **Autres rapports disponibles**.

## Ce que les chiffres comptent

| Indicateur | Lecture |
| --- | --- |
| Admissions et sorties | Débuts et fins d'épisodes de séjour dans la période, pas personnes distinctes. |
| Nuitées théoriques | Nuits de séjour par bénéficiaire ; une même personne peut apparaître dans plusieurs séjours. |
| Nuits distinctes | Élimination du double compte d'une même nuit pour une personne. |
| Nuits hors absences déclarées | Retrait des absences enregistrées, sans preuve de présence constatée. |
| Repas distribués | Quantités effectivement enregistrées et non annulées, pas accords. |
| Nuitées par lieu | Périodes d'affectation ; un changement de lieu ne crée pas une admission. |

Les personnes distinctes ne s'additionnent pas d'un mois à l'autre. Les nuitées par âge de l'explorateur utilisent l'âge exact à chaque nuit ; majeurs, mineurs et inconnus réconcilient le total. Les enfants déclarés par plusieurs adultes ne sont pas nécessairement des enfants distincts.

## Vérifier avec un jeu neuf

Dans l'**Établissement Les Passerelles** non modifié, choisir **J−60 à J+1**, J étant la date de génération : 18 ménages accompagnés, 18 prises en charge dans cette fenêtre, 6 personnes avec séjour, 3 séjours, 3 admissions et 2 sorties. Le bilan compte **215 nuitées théoriques**, **215 nuits distinctes**, **209 nuits hors absences déclarées** et **8 repas distribués**. Ces valeurs sont contrôlées dans les tests du scénario enrichi ; elles remplacent les anciens repères 159/153/5.

La fenêtre ne contient pas les 51 prises en charge de toute l'histoire du jeu. Une démonstration partagée ou déjà modifiée peut produire d'autres valeurs.

## Rapports structurés et croisements

Les rapports des rubriques personnelles, du parcours, des prestations et des financements ont leurs filtres propres. Les identifiants administratifs sont exclus du rapport personnel par défaut. Les montants restent séparés par devise, périodicité ou phase ; une imputation ne prouve pas un paiement.

Pour construire d'autres croisements et ouvrir un relevé détaillé, suivre [Explorer les populations]({{< relref "/guide/analyser/explorer/" >}}), puis [Conserver un modèle]({{< relref "/guide/analyser/modeles/" >}}).

Ces rapports ne constituent pas une validation réglementaire pour des dossiers réels, et un historique incomplet ne prouve pas une première admission absolue.

## Repérer l’écran dans le jeu fictif

{{< captures-passerelles ids="statistiques.png" >}}

Capture issue de la démonstration automatisée ; vérifier les libellés de la version utilisée.

## Comparer des mesures de même portée

Les **nuitées par lieu** comptent les affectations : une nuit sans lieu peut manquer de ce rapport, et deux affectations de séjours différents pour une même personne peuvent y compter deux fois. Leur total n’est donc pas automatiquement égal aux nuits distinctes par personne. Les admissions et sorties d’épisodes ne sont pas les débuts et fins de tous les fragments de continuité.

Pour les âges, distinguer le rapport spécialisé **Âges**, qui utilise une référence commune affichée, des mesures **Nuitées majeurs / mineurs / âge inconnu** de l’explorateur, qui utilisent l’âge exact à chaque nuit. Une naissance imprécise ne devient pas un âge exact. Comparer uniquement des rapports utilisant la même unité, la même référence et les mêmes critères.
