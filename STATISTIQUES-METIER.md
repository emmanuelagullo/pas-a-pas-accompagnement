# CHRS10 — Dictionnaire initial des indicateurs

Période de consultation : `[début, fin[`, en dates civiles. Un séjour ou
accompagnement chevauche la période si `debut < fin_consultation` et si sa
fin est absente ou postérieure au début de consultation.

| Indicateur | Définition |
| --- | --- |
| Ménages accompagnés | Nombre de ménages distincts ayant au moins un accompagnement chevauchant la période |
| Accompagnements | Nombre d'épisodes d'accompagnement chevauchant la période |
| Personnes avec séjour | Nombre de personnes distinctes bénéficiaires d'au moins un séjour chevauchant la période |
| Séjours | Nombre d'épisodes de séjour chevauchant la période |
| Admissions | Nombre de débuts de séjour dans la période |
| Sorties | Nombre de fins de séjour dans la période (fin exclue) |
| Nuitées théoriques | Pour chaque séjour, jours d'intersection × nombre de bénéficiaires explicitement rattachés ; puis somme |
| Nuits distinctes | Union des nuits civiles couvertes par au moins un séjour, par identifiant de personne ; une nuit simultanée ne compte qu’une fois |
| Nuits hors absences déclarées | Union des nuits de séjour non couvertes par une absence déclarée pour le séjour concerné ; ne prouve pas une présence effective |
| Repas distribués | Somme des quantités enregistrées dans la période, hors distributions annulées |

**Limites importantes** : les nuitées sont des nuitées théoriques d'hébergement,
non des présences constatées. Les absences ne sont pas déduites et deux séjours
simultanés peuvent contribuer deux fois pour une personne. Les bénéficiaires
sont ceux actuellement rattachés à chaque séjour : ce premier indicateur ne
reconstitue pas une composition historique. Les repas sont des réalisations
saisies, et non des droits accordés. Les sorties sont des fins de séjours,
non des sorties définitives de l'établissement.

Ces indicateurs ne mesurent ni l'occupation des places ni les capacités,
ni les trajectoires sociales. Les agrégats ne sont pas ventilés par professionnel
et ne doivent pas servir à classer les équipes.

L'accès à la page nécessite les permissions de lecture sur les accompagnements,
les séjours et les distributions. Aucun droit nouveau n'est accordé par défaut.

Export CSV : mêmes indicateurs et même période que la page, avec noms de clés
stables. Aucune donnée individuelle n'est exportée. L'accès exige les mêmes
permissions que la consultation. Les absences sont ici celles saisies dans
l'application ; leur absence ne démontre pas une présence. Lorsque deux séjours
se chevauchent et qu'un seul porte une absence, une nuit peut encore être
comptée via l'autre séjour : il ne s'agit pas d'un relevé de présence.

## Ventilations CHRS10

La ventilation mensuelle découpe la période demandée en intersections avec
les mois civils (24 mois maximum pour éviter un calcul coûteux). Admissions,
sorties, nuitées et repas sont calculés sur chaque sous-période. Les populations
distinctes ne doivent **jamais** être additionnées d'un mois à l'autre.

Les repas par service totalisent uniquement les distributions non annulées
(petit-déjeuner, déjeuner, dîner). Aucun accord non réalisé n'est compté.

## Périodes rapides et comparaison (CHRS10-06)

Les raccourcis « mois en cours » et « année en cours » s'arrêtent au lendemain
civil de la date du jour : aucune donnée future n'est supposée. Les périodes
précédentes correspondent aux mois et années civils complets. Les bornes restent
semi-ouvertes. Les dates manuelles restent disponibles.

La comparaison facultative porte sur l'intervalle immédiatement antérieur de
**même nombre de jours**, pas nécessairement sur le même mois de l'année
précédente. Elle juxtapose les chiffres bruts, sans présenter de variation en
pourcentage lorsque la base est nulle. Les personnes distinctes ne sont jamais
additionnées entre périodes. L'export CSV reste celui de la période choisie ;
la comparaison est une aide de lecture à l'écran.

## Qualification croisée CHRS10-07

Les tests vérifient que les **flux additifs** (admissions, sorties, nuitées
théoriques par séjour et repas distribués) se réconcilient entre le bilan
global et les sous-périodes mensuelles. À l'inverse, les **effectifs
distincts** ne sont pas additifs : une personne peut apparaître plusieurs mois.

La limite de 24 mois porte sur les mois **effectivement intersectés** par
`[début, fin[` : une fin au premier jour du 25e mois reste autorisée, car
ce dernier mois n'appartient pas à la période.

Cette qualification ne constitue pas une validation institutionnelle des
définitions, notamment des sorties définitives, des absences non saisies et
de la présence effective.


## Qualification par le scénario fictif Les Passerelles (CHRS10-08)

Sur la fenêtre civile `[date de référence - 60 jours, date de référence + 1 jour[`,
le jeu fictif initial (avant toute saisie manuelle) doit donner : 3 ménages,
3 accompagnements, 4 personnes ayant un séjour, 2 séjours, 2 admissions,
1 sortie, 159 nuitées de séjour, 159 nuits distinctes, 153 nuits hors
absences déclarées et 5 repas distribués (2 déjeuners, 3 dîners).
Les 159 nuitées correspondent à 40 nuits pour trois bénéficiaires du premier séjour (120) et 39 nuits pour le bénéficiaire du second séjour (39). Les 6 nuits exclues correspondent à deux nuits d’absence pour trois personnes.
Ces chiffres sont un **contrat de démonstration**, pas des données de référence
pour les bilans réels. Ils sont vérifiés par `personnes.tests_demonstration.DemonstrationStatistiquesTests`.
La navigation propose « Statistiques » uniquement aux comptes disposant des
trois permissions de consultation nécessaires ; les exports sont également protégés.

## Exploration des affectations (CHRS15)

Le rapport « Explorer les nuitées par mois et lieu » compte, pour chaque
bénéficiaire d'un séjour, les dates civiles couvertes simultanément par le
séjour et une affectation dans un lieu. La période est [début, fin[ et les
mois partiels sont conservés. Un filtre facultatif permet de choisir un lieu ;
le CSV reprend exactement les lignes visibles.

**Attention :** ces nuitées d'affectation sont *théoriques*. Une affectation
ne prouve pas la présence physique. Des affectations concomitantes peuvent
compter plusieurs fois la même nuit pour une personne ; des nuits de séjour
sans affectation ne sont pas attribuées à un lieu. Le total ne doit donc pas
être présenté comme égal aux nuitées de séjour, ni comme un taux d'occupation.
Les absences déclarées ne sont pas soustraites de cet indicateur.

L'exploration est bornée à 24 mois et ne produit aucune liste nominative.
Pour une véritable mesure d'occupation, il faudrait une définition métier
explicite des capacités, des chevauchements et des présences constatées.
