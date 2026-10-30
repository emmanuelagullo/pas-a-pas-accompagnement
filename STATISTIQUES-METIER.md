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

## Demandes, orientations, objectifs et suivi

Le rapport Parcours compte les éléments dont une version est applicable à la
date choisie, une ligne par demande/orientation/objectif/repère. Une demande
collective reste une demande, pas autant de demandes que de bénéficiaires. Les
annulations sont exclues du courant et conservées dans les fiches et journaux.
Les états se ventilent dans la sélection ; motifs, provenance, type du dernier
hébergement, destination, thème, horizon, activité, organisme et professionnel
se filtrent selon la rubrique. Les filtres nommés « exact » comparent le libellé
complet sans distinction de casse. Le filtre textuel transversal reste distinct.

La cohorte est bornée par la date de première déclaration de chaque élément ;
le statut retenu est celui applicable à la date de référence. Une admission
comptée est une prise liée ayant débuté à cette date. Le délai est le nombre de
jours civils entre première déclaration et début de prise, y compris zéro ;
la moyenne exclut les demandes sans début de prise. Cela ne mesure ni une arrivée
d'hébergement ni une présence effective. Aucun rapprochement automatique des
anciennes prises et demandes n'est effectué. Les droits des prises sont requis
pour filtrer ou exporter leur association et calculer ces délais.

Entrées/sorties des prises : une ligne par prise ayant des informations
versionnées, avec la dernière version saisie, motifs/provenance/destination et
activité explicite. Les prises sans fiche d'information ne sont pas assimilées
à des réponses vides et n'entrent pas dans ce rapport. Les anciens récits n'ont
pas de date d'effet : ce rapport ne prétend pas reconstruire leur contenu ancien
à la date de référence. Le filtre ouverte/close s'applique à la période réelle
de la prise ; son activité n'est pas déduite d'un lieu ou d'une demande.

HTML paginé, CSV de toute la même sélection, impression de la page courante.
Les filtres ne transforment pas ces unités en file active de personnes. Les
combinaisons historiques Solenne restent suivies dans la matrice externe ; ce
rapport ne déclare pas achevé leur audit sémantique.

## Prestations C : unités et continuités

Les rapports d'aides séparent quatre natures, types, libellés photographiés et
unités. Mode autorisations : plafonds globaux des accords chevauchant [début,fin[,
sans proratisation et sans assimiler une quantité non chiffrée à zéro. Mode
réalisations : remises actives dont la date appartient à la sélection. Une
remise collective contribue sa quantité une seule fois, même avec plusieurs
bénéficiaires. Financeur et prestataire sont des organismes annoncés, pas des
imputations ou dépenses déduites. La valeur faciale par bon est exportée avec
sa devise, sans être additionnée aux nombres de bons ni aux coûts.

Les repas restent des quantités réellement distribuées, avec catégorie déclarée
facultative. Les jours d'autorisation servent au contrôle de distribution et
au travail du jour, pas à inventer des distributions. Les tableaux historiques
de repas demeurent alimentés par les réalisations actives.

Une continuité individuelle d'ancien séjour crée des fragments non chevauchants
avec une filiation explicite. Les admissions/sorties et durées historiques de
séjours portent sur l'épisode initial : début original, fin du dernier fragment
si tous sont clos. Le passage technique à l'individuel n'est donc pas une sortie
ou une admission. Les nuitées utilisent les périodes de chaque fragment et
ses bénéficiaires, sans redoubler l'histoire commune antérieure.

Le détail individuel d'hébergement fournit une ligne par personne/fragment,
référence de l'épisode initial, dates du fragment, nuitées théoriques dans la
sélection, nuits hors absences déclarées et lieux. Il expose les départs partiels,
qui ne sont pas le compteur historique de sorties de l'épisode collectif. Les
fragments concomitants restent distincts ; les nuits distinctes par personne
sont toujours disponibles dans les indicateurs existants. Aucune de ces mesures
ne prouve une présence physique attestée.

HTML et CSV utilisent la même sélection ; CSV complet, impression de la page
consultée pour les rapports paginés. Le détail d'hébergement borne sa période
à deux ans pour contenir le calcul par nuit. La qualification sémantique de
toutes les branches et combinaisons statistiques Java reste ouverte dans la
matrice extérieure au dépôt.

## Coûts et financements — D

Le rapport dédié retient uniquement la dernière version du calcul de chaque
prestation non annulée. Il distingue composantes et imputations, et impose une
phase. Les composantes sont sélectionnées à leur date de prix (quantité totale
rattachée à cette date) ; les imputations sont sélectionnées par chevauchement
de la période du calcul et ne sont pas proratisées. Ce ne sont ni des charges
comptables à rattacher à l'exercice ni des règlements. Les totaux sont séparés
par devise. Les quantités d'unités hétérogènes ne sont pas additionnées. Un coût
n'est pas répété pour chacun de ses financeurs. Versions historiques et documents
figés restent consultables dans la prestation. Les CSV protègent les cellules
textuelles des formules. Les montants sont calculés en décimal, sans conversion FRF/EUR
à partir de la seule date. La lecture F distingue les anomalies anciennes de
classement numérique et de cumul des nombres entiers/décimaux, sans attribuer
une troncature uniforme à tous les montants historiques.

## Exploration transversale et appels 115 — E

Les appels sont des événements distincts : dernière version de chaque appel non
annulé, sélection sur sa date déclarée ; heure inconnue distincte de minuit.
Appelant, origine, demandes principales/secondaires, réponses et complément
115 restent des dimensions structurées. Une liste vide de réponses ne signifie
pas automatiquement « sans réponse » : cet état est déclaré séparément. Les
sommes d'adultes/enfants/grossesses déclarés par appel ne sont pas des personnes
uniques. Les personnes identifiées se dédoublonnent par UUID, indépendamment du
nombre de rappels ou des versions d'un appel. Aucun appel n'est une nuitée.

L'explorateur porte sur douze populations et permet deux axes, filtres combinés,
classes sur deux axes et somme/min/max/moyenne des quantités connues compatibles.
Les situations personnelles se lisent à la référence indiquée ; les filtres de
saisie et ceux du fait sont différents. Les modèles relatifs recalculent leurs
dates et référence à chaque ouverture. L'ensemble des champs administratifs
identifiants reste dans les éditions dédiées, sous droits, pas dans les axes.
Un axe ou filtre incompatible avec une population est refusé. Un modèle n'est
jamais un résultat figé ou une autorisation d'accès durable.

Une cellule personnelle ne reçoit que les bénéficiaires qui vérifient ses
critères, et deux critères personnels portent sur la même personne. Une quantité
collective demeure celle de l'objet sélectionné, sans répartition fictive ; une
ventilation multi-valeurs peut la répéter dans plusieurs cellules. Le total global
repart des objets distincts. Les ressources restent par devise/périodicité ; les
dettes détaillées ne s'additionnent pas au total déclaré. Coûts et imputations
restent séparés par devise/phase, sans somme prévu + autorisé + réalisé.
L'imputation est retenue par chevauchement de sa période, sans proratisation.

Convention moderne des classes : minimum inclus, maximum exclu. Les anciennes
listes d'âge contiennent des bornes inclusives, chevauchements et même des
étiquettes dont les chiffres ne concordent pas ; elles ne sont pas importées
aveuglément. Inconnus et hors classes sont visibles. Une naissance estimée ne
produit pas un âge exact. Une première entrée connue/retour connu ne garantit
pas la complétude historique du dossier ; une clôture de prise n'est jamais
une sortie définitive de l'établissement inférée.

L'explorateur complète les rapports spécialisés des lots A–D et les rapports
CHRS. La qualification de toutes les combinaisons du moteur Java reste à
terminer ; l'existence de cet explorateur ne constitue pas une preuve de
reproduction exhaustive de chacune d'elles. Les listes 115 absentes et leurs
libellés d'usage réels restent explicitement non vérifiés.


## Consolidation F — contrat des calculs

Les quinze populations distinguent personnes, ménages, prises, demandes,
épisodes de séjour, autorisations d'hébergement/repas, périodes de lieu,
distributions de repas, remises d'aides, appels, ressources, dettes, coûts et
imputations. Une autorisation ne crée aucune réalisation. Une période de lieu
ne crée aucune admission ; sa quantité est bornée à la sélection et au séjour.

Les sept niveaux et neuf mesures sont facultatifs, bornés à 2 000 cellules
au total, avec refus explicite plutôt que troncature. Les axes personnels
portent sur la même personne. Les situations/objectifs/orientations sont ceux
des bénéficiaires à la référence (toutes leurs prises, sans inférer une mission).
Les axes mission portent exclusivement sur la prise ou prestation comptée.
Les libellés de répertoire peuvent refléter une correction : ce ne sont pas
des documents figés. Les champs de texte narratif ne deviennent pas des axes.

Référence commune, date de fait/début ou date de saisie initiale sont proposées
explicitement. Au plus 366 dates personnelles distinctes dans un calcul ;
si un même déclarant possède des valeurs différentes selon ces dates, une
somme familiale distincte est refusée plutôt que remplacée par un maximum.
Les déclinaisons d'âge peuvent se chevaucher entre dates : totaux non additifs.

Nuitées par âge : âge exact à chaque nuit civile, majeur à partir de 18 ans,
naissance du 29 février évaluée au 1er mars dans une année non bissextile.
Une date inconnue, estimée ou postérieure à la nuit contribue à la catégorie
inconnue. Majeurs + mineurs + inconnus réconcilient le total de nuitées du
périmètre choisi ; les absences ne sont pas déduites. Les quantités par âge
respectent les bénéficiaires filtrés ; les quantités collectives d'autres
prestations ne sont jamais réparties artificiellement.

Les personnes distinctes majeures/mineures/inconnues à la référence ne sont
pas les catégories déclarées des repas. Celles-ci restent libres et explicites :
le classement « adulte/jeune/bas âge » ne signifie pas majorité légale. Une
proposition de saisie facultative montre ses seuils inclusifs (12 et 2 par défaut),
n'infère rien d'une naissance imprécise et doit être confirmée avant écriture.
Les repas bas âge sont inclus dans le total moderne, contrairement au calcul
ancien FormStats.calculeNbreRepas qui ne les ajoutait pas.

Déclarations familiales : une valeur par déclarant distinct à la référence,
inconnus exclus et dénombrés, zéro conservé. Les nombres d'enfants déclarés par
plusieurs personnes peuvent décrire les mêmes enfants : ils ne sont pas un
effectif de ménage ou un compte de personnes uniques. Une somme totale connue
à charge ou non exige que les deux composantes soient connues. La grossesse
déclarée est un décompte de déclarants, jamais une valeur déplacée vers un
autre compteur comme dans les positions 17–20 historiques.

Débuts et fins sont filtrables séparément du chevauchement ; une fin exactement
au début de sélection est une sortie de cette sélection. La fin exclue du
rapport n'y appartient pas. L'intégralité des épisodes exige qu'ils soient clos ;
les durées civiles complètes, leurs intersections et les personnes-nuitées
restent des mesures différentes. Les copies/requêtes enregistrées ne fabriquent
ni dates, ni personnes, ni faits. La recette F des 21 destinations est une
comparaison des définitions modernes, pas l'exécution de l'ancien logiciel.

Le relevé détaillé offre jusqu'à onze colonnes choisies, avec les mêmes filtres
que la synthèse, le CSV et le PDF. Les liens vers un dossier conservent les
critères du rapport dans un retour signé propre au compte, valable 24 heures ;
aucune URL de retour arbitraire n'est acceptée. Les valeurs personnelles
affichées restent celles des bénéficiaires retenus par les filtres.


Consolidation H : les déclarations d'ancrage territorial et d'évolution
réutilisent les faits personnels datés, leurs journaux, droits propres et CAS.
La fréquentation institutionnelle déclarée (oui/non/inconnue) ne se déduit pas
des séjours connus ; les anciennes déclarations restent non qualifiées.
Les champs d'une même déclaration sont corrélés dans les filtres et classements.
Les populations ressources/dettes utilisent les champs du poste sélectionné.
L'exploration propose premier/dernier objet filtré par personne pour les mesures
de personnes, et des sous-totaux par préfixe recalculés sans additionner les
ventilations recouvrantes. Aucun classement n'est une première admission absolue.

## Corrections statistiques ST1 — portée et corrélation

Les nuitées des populations **séjours** et **affectations** sont décomposables par
bénéficiaire. Après les critères personnels, la quantité de chaque objet est
recalculée sur les personnes retenues, en conservant les bénéficiaires propres
à chaque fragment de continuité. Les filtres de quantité portent ensuite sur
cette quantité retenue ; le relevé détaillé et ses exports l'affichent aussi.
Chaque cellule et sous-total recalcule les nuitées de ses propres bénéficiaires.
Somme, minimum, maximum et moyenne utilisent cette même portée par objet.
Exemple : trois personnes pendant quatre nuits donnent 12 personnes-nuitées ;
si une seule personne est retenue, la quantité vaut 4. Deux nationalités peuvent
faire apparaître les mêmes quatre nuits dans deux lignes, sans doubler le
sous-total. Les absences ne sont pas implicitement déduites.

Cette décomposition ne s'applique ni aux remises collectives ni aux coûts et
imputations : deux cartes collectives restent deux cartes, et un montant n'est
pas divisé ni multiplié par ses bénéficiaires. Les valeurs de ces objets peuvent
figurer dans plusieurs cellules personnelles ; leurs ventilations ne s'ajoutent
pas. La mesure quantitative n'est pas une mesure de personnes distinctes.

Les lieux d'affectation sont regroupés par **identifiant**, même lorsque leur
libellé est identique. Dans la synthèse et ses exports, l'identifiant complète
le libellé si plusieurs lieux de la sélection portent le même nom. Les filtres
historiques par nom continuent à sélectionner tous les lieux de ce nom.
La dimension **Identifiant du lieu d'hébergement** permet d'isoler un lieu ou
de conserver son identité dans les colonnes d'un relevé détaillé.

Une mission à la référence doit être applicable dans sa propre période **et**
dans celle de sa prise en charge exacte : débuts inclus, fins exclues. Le mode
« date du fait » peut donc afficher une mission qui n'est plus applicable à la
référence commune ; ce n'est pas une affectation actuelle déduite de la personne.

Dans la population **demandes**, les champs `demande.*`, l'état, le motif et la
provenance décrivent la dernière version de la **même demande comptée**. Ils ne
peuvent pas être satisfaits par une autre demande du même bénéficiaire. Le choix
d'une référence personnelle antérieure ne transforme pas cette population de
dernières versions en historique d'états. Depuis une autre population, les
dimensions de parcours conservent leur sélection datée à la référence.

### Source sociale conservée, adaptation séparée

Ce lot ne change pas de source sociale. Les dimensions `social.*` lisent les
**déclarations `SituationPersonnelle` applicables à la référence** (commune,
du fait ou de saisie), dans leur état corrigé connu aujourd'hui. Elles ne lisent
ni les anciens témoins `SituationSociale` des prises, ni la projection économique
dérivée des ressources détaillées par `bd6.etat`. Les dimensions `ressources.*`
et la population ressources lisent ces déclarations détaillées séparément.
Un dossier peut donc afficher « Ressources déclarées » tandis que la déclaration
sociale brute reste « sans ressources » ou non renseignée. L'harmonisation de
ces deux notions relève d'un contrat de source sociale distinct, à coordonner
avec la trajectoire ; aucune recopie ni migration n'est réalisée dans ST1.

## ST2 — Justifier une cellule et revenir à l'analyse

Les chiffres de l'explorateur et leurs totaux ouvrent leurs contributions exactes,
avec période, unité et règle de décompte. Les effectifs distincts ne sont pas
additionnés entre faits ; les valeurs inconnues restent exclues, jamais mises à
zéro. Les minimums, maximums et moyennes portent sur les quantités par objet.
La fiche justificative identifie l'objet retenu et permet de rejoindre son dossier.
Les retours signés conservent critères, sélection logique et pagination.

Ces liens sont propres au compte et expirent après un jour. Les droits sont
revalidés, les périodes relatives figées pour expliquer le calcul affiché et
les contributions recalculées. Si les données de calcul ont changé, le détail
est refusé explicitement et invite à recalculer l'analyse. Aucun résultat figé
ni accès de dossier n'est enregistré dans un modèle. Le détail est borné à
10 000 contributions, sans troncature silencieuse.

## ST3 — Personnaliser le rapport courant

Les rapports proposent un transfert explicite vers l'explorateur. Les repas et
leurs regroupements mois/service conservent les cellules à zéro (domaine limité
à 24 mois) ; cette complétion est un choix visible, réservé à cette population.
Les coûts et imputations reprennent les filtres exacts, la phase, les devises et
la période de prix/chevauchement. Montant, quantité facturée et prix unitaire
restent des informations distinctes ; les égalités sensibles à la casse sont
conservées lorsqu'elles définissent le rapport financier source. Les appels
compatibles reprennent leurs critères datés ; les appels annulés et recherches
transversales non traduisibles produisent un refus explicite.

Une comparaison de périodes, les nuits distinctes, les durées civiles et les
rapports composites ne sont pas remplacés par une somme approchée. Un écran
explique la définition non représentable et permet de retrouver le rapport
courant avec ses critères. Les déclarations personnelles et les rapports de
parcours/prestations gardent également leurs rapports spécialisés lorsque leur
définition complète n'est pas traduisible. Les paramètres anciens restent valides.

## ST4 — Composition progressive

Retenir, Afficher, Compter et Classer ont chacun une synthèse et une modification
directe. Tous les champs restent dans le formulaire GET, utilisable sans
JavaScript ; ouvrir une partie ne réinitialise pas les autres. Le déplacement
d'un niveau déplace ses classes avec lui ; le retrait ne change ni filtres,
ni mesures, ni colonnes. Les sous-totaux restent recalculés sur les identités
et contributions du préfixe. Les erreurs ouvrent les parties concernées.
L'accès aux rapports courants reste disponible sous les droits existants.

## ST5 — Modèles personnels et confirmations périmées

Depuis un modèle ouvert, Recalculer modifie seulement la consultation. L'utilisateur
peut remplacer explicitement le modèle ou conserver une variante sous un autre nom.
Renommer et Dupliquer sont accessibles depuis les listes de modèles des rapports
courants et de l'explorateur. Les définitions historiques restent dans leur format ;
une opération de renommage ne réinterprète pas leurs critères. Aucun partage ajouté.

La confirmation est signée pour le propriétaire et l'état lu du modèle, valable un
jour. Un UPDATE conditionnel compare le nom et tous les paramètres. Une révision
interne dans le JSON empêche aussi un écrasement après un renommage aller-retour ;
elle n'est pas exportée dans les modèles échangeables. Aucun changement de table.
Un conflit conserve la saisie et demande une nouvelle lecture, sans actualiser
silencieusement la confirmation. Les critères de dossier ne sont pas enregistrés
dans les modèles au-delà des paramètres déjà permis par le registre fermé.

Vérifications chiffrées : consultation collective de 12 nuitées, variante de trois
personnes distinctes, remplacement explicite, puis refus d'un second remplacement
avec la confirmation initiale. Deux confirmations concurrentes sur SQLite : une
réussite et un conflit. Tests HTTP/HTML, propriété, CSRF, export et anciens modèles.
Ces tests ne constituent pas une observation réelle dans un navigateur.

## ST7 — Catalogue, variantes et gestion personnelle

L'entrée Statistiques présente d'abord les rapports prêts à utiliser. Créer un
rapport propose Partir de zéro ou sélectionner une définition proposée/personnelle.
Gérer mes rapports réunit ouverture, édition, renommage, duplication et suppression
confirmée. Les remplacements et suppressions contrôlent l'état signé du modèle ;
la suppression ne touche aucun fait de dossier. Aucun partage entre comptes.

Les variantes de rapports spécialisés conservent leur calcul natif et leurs
critères validés par le même formulaire et les mêmes droits que leur rapport
source. La dérivation n'est pas une conversion approximative dans une population
de l'explorateur. Les modèles historiques gardent leur format ; les nouvelles
définitions spécialisées portent un discriminateur fermé `_rapport_source`.
La composition libre Retenir/Afficher/Compter/Classer reste accessible séparément.
Modifier les mesures d'une synthèse composite au-delà de ses paramètres natifs
nécessitera des blocs de calcul communs ; ce lot ne prétend pas les avoir unifiés.

## ST8 — Objets précis et continuité de navigation

Le relevé de l’explorateur ouvre les accords et faits concernés, avec ancre sur
le séjour, l’affectation, la distribution, la remise ou la composante/imputation
financière et sa version. Les liens sont chargés en lot ; les projections de
colonnes n’effectuent aucune requête supplémentaire. Les critères personnels
continuent de porter sur les bénéficiaires retenus, sans modifier le fait collectif.

Les rapports spécialisés transmettent un retour signé propre au compte, à leurs
critères et à leur page. Il est conservé dans le contexte du dossier et s’ajoute
à sa navigation habituelle, sans donner d’accès supplémentaire. Les retours de
l’explorateur et leurs justificatifs existants restent compatibles. Les CSV
gardent leurs colonnes et leurs valeurs ; aucun résultat n’est enregistré.

Vérifications : 12 nuitées collectives, composante 6,30 EUR et version exacte,
retour depuis fiche familiale puis dossier, confirmations concurrentes/périmées,
et une seule requête de liens pour plusieurs séjours. Gestion personnelle et
retours testés en Chromium, au clavier et sans JavaScript sur écran étroit.

## ST9 — Modèle enregistré, résultat et traduction fidèle

Les actions visibles distinguent la définition (modèle) du résultat recalculé
(rapport). Les paramètres enregistrés d’un rapport spécialisé gardent ses
indicateurs et sa présentation ; ils ne sont pas présentés comme une composition
libre. La liste personnelle vide propose une action de création.

Les adaptateurs existants de repas, financements et appels compatibles sont
réutilisés depuis le catalogue et le rapport courant. L’action de composition
n’est proposée qu’après validation de la traduction avec les critères courants.
Elle crée une définition composable distincte, sans conversion ou remplacement
implicite d’un ancien modèle. Formats, sources sociales et droits sont conservés.

L’audit chiffré distingue 14 nuitées additives, 12 nuits distinctes et 10 hors
absences sur un même jeu ; une durée de quatre jours ne devient pas douze jours
parce que le séjour concerne trois bénéficiaires. Plusieurs mesures et niveaux
existent déjà ; l’unification restante exige des contrats de contributions,
quelques agrégations supplémentaires et, pour la synthèse, plusieurs analyses.

## ST10 — Définition, personnalisation et restitution

Les définitions existantes restent des modèles autonomes. Une migration additive
distingue les nouvelles personnalisations, ajoute la description et conserve
la filiation lorsqu’elle est connue. La personnalisation mémorise la définition
et les réglages à l’enregistrement : une modification ou suppression ultérieure
du modèle source ne réécrit pas les consultations habituelles. La gestion signale
une origine modifiée. La conservation du modèle et de sa personnalisation est
atomique ; les remplacements restent explicites et protégés par preuve d’état.

L’accueil ouvre directement les accès habituels et centralise la gestion.
Après les résultats : un bloc CSV/PDF, textes facultatifs, puis une action de
conservation. Les routes historiques sont maintenues. Les descriptions peuvent
accompagner les JSON existants sans introduire de version obligatoire nouvelle.

Les règles civiles nommées et les bornes en jours relatifs sont recalculées à
l’ouverture. La période historique fixe reste disponible ; la suggestion est
visible et confirmée. Les rapports à date unique ne deviennent pas des rapports
d’événements dans une période. Les exports figent les dates affichées ; leurs
données sont relues sous les droits courants, sans résultat archivé implicitement.

Les nouveaux PDF utilisent une restitution structurée depuis les données des
exports natifs, avec critères, résumé et description optionnels, hiérarchie et
sous-totaux déjà calculés. Aucun total n’est reconstruit par addition de lignes.
Le navigateur conserve le backend texte paginé du socle ; aucun moteur natif
n’est chargé dans la PWA. Les CSV sans notes gardent leurs en-têtes et données.

L’explorateur propose des durées civiles de séjour clos (moyenne au dixième),
des participations par épisode et des nuits distinctes, éventuellement hors
absences déclarées. Les justificatifs explicitent doublons et absences.
Ces extensions ne rendent pas automatiquement composables les synthèses
réunissant plusieurs populations ; leur assemblage reste un chantier distinct.

## ST13 — Mesures indépendantes et assemblages personnels

Créer un modèle → Partir de zéro ouvre la nouvelle composition. Elle conserve
Retenir, Afficher, Compter et Classer sans population globale. Chaque critère
choisit ses faits, ses conditions et sa relation : même personne bénéficiaire,
même ménage explicite ou même prise en charge. Les conditions d'un bloc portent
sur le même fait ; deux blocs peuvent porter sur des faits différents. ET ou OU
s'applique à ces blocs. Sans identité connue, un critère « sans fait » ne démontre
pas une absence. Les regroupements booléens imbriqués ne sont pas encore proposés.

Chaque mesure garde ses faits, ses filtres, son lien temporel et sa règle de
calcul. Une ligne détaillée représente l'objet choisi dans Afficher ; des mesures
de repas et de nuitées peuvent ainsi figurer sur la même ligne de personne,
y compris sans repas. Les effectifs distincts et les sous-totaux sont recalculés,
sans jointure multiplicative. Les montants déclarés absents restent inconnus.
Les informations narratives supplémentaires sont des colonnes détaillées, pas
des axes ; les numéros administratifs ne sont pas ajoutés à ce registre.

Les modèles historiques restent en schéma 1. Une variante explicite peut les
traduire en schéma 2, sans les remplacer. Les rapports de mouvements, synthèse,
hébergement et âges ont des traductions vérifiées, en plus des adaptateurs
repas/financements/appels compatibles. Les comparaisons de périodes, ventilations
mensuelles et autres critères non représentables restent dans leurs calculs
spécialisés : leur présence dans un assemblage ne signifie pas une conversion libre.
Les sources sociales restent SituationPersonnelle à la référence, distinctes des
déclarations détaillées et de la synthèse du dossier.

Un assemblage réutilise au plus douze définitions, préproposées ou personnelles,
avec leurs paramètres et descriptions photographiés. Le changement ou la suppression
du modèle d'origine ne modifie pas la partie ; reprendre la version actuelle est
une action explicite. Les parties ne sont pas imbriquées. Une période commune et
une sélection de dossiers communes sont facultatives ; les paramètres propres
restent le défaut. Une date de référence seule n'est pas remplacée par une période.
Les droits sont revalidés pour chaque partie. Aucun partage entre comptes n'est ajouté.

Les chiffres de la nouvelle analyse ont des preuves signées, des contributions,
l'objet exact et des retours conservés ; les corrections rendent les preuves
périmées. Un assemblage ouvre ses analyses séparées pour approfondir. PDF utilise
le moteur existant de pas-communs ; CSV contient des tables successives identifiées,
sans inventer d'en-tête commun ni total entre parties. Modèle, personnalisation,
conservation des deux et remplacement conditionnel restent distincts.

Bornes : vingt critères relationnels, vingt conditions par bloc, douze mesures,
sept niveaux et onze informations détaillées ; les limites de faits/contributions
de l'explorateur restent explicites, sans troncature. Qualification complémentaire :
`personnes.tests_analyses`, `personnes.tests_assemblages`,
`personnes.tests_analyses_acteurs`, `personnes.qualification_analyses` et
`scripts/qualifier-analyses-profils.py`. Les profils Django PWA ne qualifient pas
à eux seuls l'exécution réelle Pyodide/OPFS.

### ST14 — Composition contextuelle

Le compositeur conserve Retenir, Afficher, Compter et Classer. Chaque bloc
résume ses faits, son calcul et ses conditions ; l'ajout ou une erreur ouvre
la partie concernée. Après un changement de faits, « Actualiser les choix de
ce bloc » présente les calculs et filtres compatibles, aussi sans JavaScript.
Les classements sont communs aux mesures de l'analyse ; des classements
indépendants relèvent de parties distinctes dans un assemblage. Les dimensions
personnelles sont rangées par domaine. Les règles non pertinentes disparaissent
quand elles sont à leur valeur ordinaire ; tout paramètre différent déjà choisi
reste visible. Les choix devenus incompatibles restent identifiables et sont
signalés, jamais supprimés silencieusement. Les classes numériques sont dans
les options de classement ; le type de ligne n'apparaît qu'en restitution détaillée.
Cette présentation ne traduit pas de nouveau rapport spécialisé et ne change
ni les sources sociales, ni les définitions, ni les formats enregistrés.
