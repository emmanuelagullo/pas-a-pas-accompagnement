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

1. Choisir un des **Modèles prêts à utiliser**, présentés en premier à l’entrée Statistiques.
2. Renseigner sa période et ses critères, puis lire les définitions avant de comparer les valeurs.
3. Exporter le CSV ou utiliser l’impression proposée.

**Créer un modèle**, à côté de **Gérer mes modèles**, propose de partir de zéro
ou d’une définition composable. Le **modèle** conserve la sélection, les colonnes,
les mesures et le classement ; le **rapport** est le résultat recalculé.

Depuis un rapport compatible, **Composer à partir de ce rapport** reprend
fidèlement sa définition dans Retenir / Afficher / Compter / Classer. Cette action
est disponible pour les repas, les financements et les appels 115 lorsque leurs
critères sont représentables. Elle crée un modèle composable distinct.

Pour un rapport spécialisé, **Enregistrer ces paramètres** mémorise ses critères
sans changer ses indicateurs ou sa présentation. Si la traduction complète vers
la composition libre manque, aucune dérivation composable n’est proposée.

**Mes modèles** affiche les définitions personnelles enregistrées ; une liste
vide propose **Créer un modèle**. **Gérer mes modèles** permet de modifier,
renommer, dupliquer ou supprimer une définition. Après édition, choisir
explicitement **Remplacer** ou **Enregistrer un second modèle**. Supprimer un
modèle ne supprime aucun dossier. Les définitions existantes restent lisibles.

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
