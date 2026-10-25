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
