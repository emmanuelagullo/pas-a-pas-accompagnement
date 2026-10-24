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

## Regroupements exploratoires (CHRS15-04)

Les rapports de repas et d'affectations proposent trois vues : détail mois ×
service/lieu (par défaut), total par service/lieu, ou total par mois. Les
regroupements additionnent **les lignes agrégées du rapport de base** : ils
ne modifient ni les filtres, ni les périodes, ni les règles de calcul. Les
lieux sont regroupés par identifiant et non par libellé (deux lieux peuvent
porter le même nom). Le CSV possède exactement les colonnes et les lignes
de la vue choisie. Aucun résultat nominatif n'est ajouté.

Les nuitées d'affectation peuvent rester doublonnées en cas d'affectations
concomitantes : un total par lieu ou par mois ne doit pas être interprété
comme un nombre de nuits distinctes ni comme un taux d'occupation.


## Modèles personnels de rapports (CHRS16)

Les professionnels disposant des droits de consultation statistique peuvent
enregistrer jusqu’à 30 configurations personnelles : rapport, bornes civiles,
service ou lieu et regroupement. Aucun résultat ni donnée nominative n'est
stocké dans le modèle ; la consultation recalcule les indicateurs avec les
données et permissions actuelles. Les modèles ne sont pas partagés entre comptes.
Les bornes sont fixes : un modèle enregistré pour janvier 2026 ne devient pas
automatiquement « janvier prochain ». La suppression est explicite.

### Modèles de rapports et périodes relatives (CHRS16)

Un modèle personnel peut enregistrer une période fixe (bornes civiles) ou un code de période relative : mois courant, mois précédent, année courante, année précédente ou douze derniers mois glissants. Les bornes relatives sont résolues à chaque consultation, y compris pour le CSV ; elles ne sont pas des résultats mis en cache. La fin est toujours exclue. Les filtres et regroupements restent ceux de CHRS15. Les modèles ne sont pas partagés entre utilisateurs.

## Déclarations familiales à une date (Solenne L2a)

Ce rapport distinct consulte toutes les fiches Personne enregistrées aujourd'hui,
avec leur déclaration applicable à la date choisie. Il ne reconstitue ni un registre
de personnes présentes à cette date, ni une file active. Les filtres nom/prénom,
situation familiale déclarée exacte (insensible à la casse) et déclaration
applicable/non applicable sont communs au HTML et au CSV. Chaque fiche compte une
fois. Les regroupements affichent le libellé déclaré tel quel ; ils ne constituent
pas une nomenclature normalisée et des variantes de libellés peuvent rester séparées.
Les enfants déclarés par plusieurs adultes ne sont pas dédoublonnables sans leurs
identités et relations ; aucun total d'enfants n'est donc calculé. Les identités
restent actuelles, les situations sont datées selon les connaissances corrigées
aujourd'hui. Une déclaration effacée par correction reste dans son journal.

## Coordonnées personnelles à une date (Solenne L3a)

Population : fiches personnes enregistrées aujourd'hui, avec les coordonnées
applicables à la date. Les filtres nom/prénom, ville, pays et code postal sont
communs à l'écran et au CSV ; les trois champs géographiques sont comparés sur
leur valeur complète, sans distinction de casse. Regroupement par libellés de
ville et pays déclarés, avec une personne par fiche ; aucune géolocalisation,
déduction de nationalité ni présomption de présence physique. Les variantes de
libellés restent distinctes dans les regroupements. Les valeurs vides et les
personnes sans coordonnées applicables sont visibles hors filtre géographique.


## Missions professionnelles par prise (Solenne L4a)

La consultation et le CSV portent sur les missions non annulées d'une seule
prise à la date choisie, éventuellement filtrées par rôle. La borne de fin est
exclue ; une mission sans fin propre n'est applicable que pendant la prise.
Le CSV distingue fin propre et fin effective tenant compte de la prise.
Une ligne représente une mission, pas une personne accompagnée ni un ménage ;
les co-intervenants ne constituent donc pas une file active additionnable.
Nom, fonction et coordonnées du professionnel proviennent de sa fiche à date.
Les organismes sont identifiés par UUID et libellé actuel ; le CSV n'est pas
une photographie documentaire figée. Les missions annulées restent dans le
journal, hors de cette sélection. Aucun rapprochement des anciens noms libres.


## Recherche des prises en charge par intervenant

Population : missions non annulées dans leurs périodes et celles de leur prise à
la date choisie. Le filtre organisme sélectionne une cible directe d'organisme
ou un professionnel dont la fiche appartient à cet organisme à cette date.
Le filtre de dossier recherche libellé du ménage et noms des bénéficiaires
explicites ; aucune appartenance actuelle n'est substituée à ces bénéficiaires.
Une ligne du CSV représente une mission ; les compteurs distinguent missions et
prises distinctes, sans total implicite de personnes. Fin propre et fin effective
sont exportées séparément. Les colonnes organisme du CSV décrivent la cible
directe de la mission ; le rattachement de la fiche professionnelle sert au filtre.
Les libellés des identités sont actuels. Les champs libres hérités ne sont pas
rapprochés automatiquement et ne participent pas à ce filtre structuré.


## Identité déclarée et liens personnels à une date (méta-lot A02)

Compléments : toutes les fiches personnes enregistrées aujourd'hui avec leur
déclaration applicable à date. Filtres exacts insensibles à la casse sur sexe,
lieu, ville et pays de naissance, nationalité parmi la collection, apatridie
oui/non/inconnue et présence d'une déclaration. Une personne compte une fois ;
les libellés de sexe restent tels qu'enregistrés dans les regroupements. Une
collection vide est une nationalité non renseignée, pas une apatridie déduite.
Le CSV représente la collection de nationalités par un tableau JSON dans sa
cellule, et conserve les dates/sources. Les identités des personnes sont actuelles.

Liens : relations non annulées applicables à date, filtrées par type et par noms
d'une ou des deux extrémités. Une relation est comptée une fois, pas une fois par
personne. Le CSV expose les deux UUID et le rôle depuis la première extrémité ;
il n'impose aucun sens juridique. Les noms sont actuels, les périodes sont celles
connues après corrections. Aucune dépendance aux appartenances ou à la file
active d'accompagnement. HTML, pagination et CSV partagent la sélection.

## Déclarations du dossier personnel

Le rapport « Dossier personnel » porte sur les déclarations applicables à la
date choisie, et non sur une file active de prises en charge. Une ligne représente
un poste : une personne peut en avoir plusieurs. Le nombre de lignes n'est donc
pas un effectif de personnes. Les annulations sont exclues du rapport courant
et conservées dans les historiques. Le HTML pagine ; le CSV exporte toute la
sélection. L'impression porte sur la page affichée.

Les sommes de ressources portent uniquement sur les montants mensuels connus,
séparés par devise. Les autres périodicités restent consultables et filtrables,
sans conversion implicite. Les sommes partielles de dettes détaillées et les
totaux déclarés sont présentés séparément : ils ne s'additionnent pas. Un montant
inconnu n'est pas zéro ; une absence déclarée n'est pas une rubrique non saisie.
Les filtres structurés comprennent état, devise, montant, organisme, périodicité,
nature de dette, échéance et portée/représentant d'une protection selon la rubrique.
Les identifiants administratifs ne participent à la recherche et au CSV que si
leur inclusion a été explicitement demandée. Les échéances dépassées restent
des prévisions à vérifier, sans effet automatique sur les droits déclarés.
