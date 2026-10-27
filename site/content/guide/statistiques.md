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

Les **accès habituels** ouvrent directement les réglages enregistrés. Le bouton
**Gérer les modèles et leurs personnalisations** centralise les actions de gestion
et de création. Le modèle définit le calcul ; sa personnalisation conserve les
choix d’application ; le rapport est le résultat recalculé.

Après les résultats, **Conserver ces réglages…** permet de retrouver une
personnalisation, un modèle ou les deux. Remplacer un enregistrement reste un
choix explicite. Les définitions antérieures restent utilisables.

**Exporter ce rapport** réunit CSV et PDF. Le résumé optionnel décrit ce résultat ;
une case permet d’inclure aussi la description du modèle. Dans le CSV, ces textes
ajoutent des lignes de notes avant l’en-tête ; sans texte ajouté, le format
tabulaire reste inchangé. Le PDF reprend critères, groupes et sous-totaux
calculés. Serveur et bureau utilisent le rendu HTML/CSS du socle ; le navigateur
produit les mêmes informations sous forme textuelle paginée.

Les périodes relatives distinguent notamment **mois en cours jusqu’à aujourd’hui**
et **mois civil entier**, jours précédents/suivants, semaines, trimestres, années
et bornes libres en jours relatifs. Une suggestion ne remplace jamais
silencieusement des dates historiques. Les rapports à une date unique proposent
des dates relatives, et restent des situations à date plutôt que des événements
dans une période.

Depuis un rapport compatible, le dépliant **Adapter ce rapport** permet de
composer à partir de sa définition : repas, financements et appels compatibles.
Les autres rapports spécialisés conservent leurs indicateurs ; une absence de
traduction complète n’est pas remplacée par une approximation.

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
