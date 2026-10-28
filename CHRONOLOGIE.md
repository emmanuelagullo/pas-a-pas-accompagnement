# Chronologie — audit et premier lot de consultation (#SOC)

## Bases examinées le 28 octobre 2026

Patch réactualisé sur `main` Inria `1a09370e93f1b705d639f80c7e000744805baa8d`.
Les ajouts ACT08/ST12 du README sont conservés ; la correction du libellé
« Équipe de suivi » est déjà intégrée en amont. La projection chronologique
est inchangée par cette réactualisation. Les validations générales ci-dessous
décrivent le premier lot sur sa base initiale ; les contrôles de compatibilité
sur la nouvelle base sont précisés dans le bilan de livraison.


- Pas à Pas, Inria `main` : `c70f77d05cf69252ff91303eee90e1072ffba446`.
  Le miroir GitHub annonce le même SHA.
- pas-communs, Inria `main` : `896a6e819c5fdfa3ac92541c91332351281581e8`.
  La dépendance applicative reste le wheel 0.9.0 épinglé, pas ce checkout.
- Petits Pas, Inria `main` : `f3969a75df6306a22c96cadc42291f0d4326f748`.

Lecture des AGENTS.md, de README/ARCHITECTURE et des contrats pertinents.
L'application utilise désormais `acteurs.middleware`, `acteurs.managers` et
`acteurs.politique` pour borner les lectures ordinaires ; une responsabilité
métier et une habilitation actuelle sont distinctes. L'activation reste explicite.
`ACTEURS-ACCES.md` décrit les limites de ce contrôle, notamment les copies locales.

Sources confrontées : modèles de périodes et bénéficiaires, `vues_dossiers`,
`lecture_dossier`, `bd6`, `hebergement`, `continuite_hebergement`, `repas`, `aides`,
`condition_sociale`, `saisie_sociale`, `trajectoire`/`vues_trajectoire`,
`dossier`, `exploration_releve` et les tests des retours de rapports.
Les formulaires de condition sociale et leurs retraits/corrections sont plus
récents que les anciens jalons BD6 : ils ne doivent pas être remplacés par une
nouvelle source sociale. Les rapports disposent de retours vérifiés et de liens
vers le séjour, l'affectation ou la remise exacts ; la frise conserve cette
convention de fragments et le contexte de rapport déjà présent.

Dans Petits Pas, les parcours et aides HTML natives, la séparation des droits
et les mécanismes de sélection ont été recherchés ; aucun composant de frise
commun immédiatement réutilisable n'a été identifié. Le socle fournit des
ressources et mécanismes techniques, pas une définition des périodes CHRS.
Ce lot reste donc applicatif, sans nouveau moteur graphique ni modification du
socle, des sources sociales, des politiques d'accès ou des dépendances.

## Audit d'usage et proposition

La liste compacte existante reste préférable pour choisir une prise en charge
par date connue et pour les écrans étroits. Elle juxtapose toutefois difficilement
plusieurs séjours, autorisations et absences : une fin prévue ressemble facilement
à une sortie si l'on ne lit pas les détails. Une frise proportionnelle rend les
chevauchements visibles mais devient illisible si des décennies sont comprimées.

Choix retenu : une page facultative **Chronologie**, depuis le dossier ou la
prise en charge. Fenêtre explicite de 1 jour à 3 ans, 60 lignes par page, filtres
par nature, dates et libellés toujours visibles, puis barres à échelle commune.
Le dossier commence par les prises et leurs prévisions distinctes, avec une
synthèse des prestations consultables dans la fenêtre. Le filtre Tout permet
de les déplier temporellement ; depuis une prise, toutes ses périodes sont
proposées. Le premier lien ouvre la prise BD ; les prestations ouvrent leur
fiche exacte. Le retour conserve fenêtre, filtre, page et ancre de la ligne.
Les listes et le parcours Recherche → Dossier → Prise restent disponibles.

Une fenêtre d'un jour permet de retrouver les autorisations et périodes qui
recouvrent cette date. Cela ne prouve ni présence physique, ni distribution,
ni usage d'un titre de transport. Le filtre n'est pas un calcul statistique.

### Maquette concrète : Les Passerelles

La maquette est la page HTML de l'application, sur le jeu neuf Les Passerelles :
ouvrir Samira, puis Chronologie, et choisir Tout ou la chronologie d'une prise.
Les lignes textuelles servent aussi de restitution sur écran étroit.

| Ligne | Sens de la barre et ouverture |
| --- | --- |
| Prise du début de l'accompagnement | Période enregistrée ; clôture effective ou absence de clôture |
| Prévision de cette prise | Ligne hachurée séparée, fin prévue et dépassement éventuel |
| Hébergement autorisé | Accord seulement ; une arrivée n'est pas déduite |
| Séjour enregistré | Arrivée/sortie enregistrées, distinctes de l'accord |
| Unité A puis Appartement relais | Affectations successives ; lien à l'affectation exacte |
| Absence au sein du séjour | Ligne superposée ; le séjour reste ouvert |
| Dîner ou Déjeuner | Période d'autorisation, distributions dans la fiche |
| Transport, bons, autres aides | Autorisation photographiée, sans usage ou remise implicite |

Le jeu existant comprend plusieurs prises, prestations simultanées, changements
de lieu, absences et corrections. Ce lot ne le réécrit pas et n'enrichit aucun
ancien espace. Les cas discriminants supplémentaires sont créés uniquement dans
les bases de tests. Les corrections restent dans les formulaires existants.

## Sens temporel et accès

- Intervalles civils début inclus / fin exclue. Pas d'arrondi au mois.
- Une période ouverte enregistrée est dessinée au plus jusqu'à aujourd'hui ;
  aucune continuité future n'est inventée. Le texte conserve l'absence de fin.
- Une autorisation ouverte reste explicitement une autorisation sans fin
  enregistrée. La fenêtre graphique n'en devient pas la date de fin.
- Les prévisions et réalisations ont des lignes distinctes. Les annulations
  restent nommées et en motif discontinu ; elles ne sont pas des sorties.
- L'épisode initial et la continuation individuelle gardent leur qualification.
- Aucune date précise n'est tirée d'un récit ou d'un horodatage de correction.
  Les événements personnels ponctuels, dates inconnues/estimées et distributions
  ne sont pas transformés en périodes dans ce lot.
- Le journal de saisie reste sur la fiche. La frise représente les valeurs métier
  courantes corrigées, pas une photographie de ce qui était connu à une ancienne
  date de saisie. Situation/Évolution restent les vues de l'histoire personnelle.
- Lecture via les gestionnaires contrôlés, dans le périmètre de la requête ou du
  service. Les parents accessibles sont sélectionnés avant les prestations et
  les périodes filles. Aucun gestionnaire de base intégral ni SQL brut.
- Dans un dossier personnel, bénéfice explicite exigé sur chaque accord et
  séjour ; aucune prestation des autres membres n'est projetée. Une absence ou
  affectation concerne tous les bénéficiaires de son segment de séjour.
- Dans un dossier ménage, les prises sont celles de ce ménage et les prestations
  gardent leurs bénéficiaires propres. La composition actuelle n'est pas
  rétroprojetée. Les fiches consultables détaillent la portée collective.
- Chaque fiche revalide ses droits. Le contexte signé n'est pas une habilitation.
  Aucun endpoint JSON ou compteur d'objets privés n'est ajouté.

## Performance et limites

La projection effectue des lectures groupées par modèle, jamais une requête
par barre ; les liens sont signés uniquement pour la page affichée. Les périodes
filles sont filtrées en SQL par fenêtre. Les parents prises/accords d'hébergement
restent sélectionnés pour pouvoir montrer un séjour dont la durée excède son
accord, sans déduire la durée de l'un de celle de l'autre. Sur le dossier Samira du jeu neuf avec contrôle actif, la mesure HTTP locale
a donné 64 requêtes pour 38 lignes (environ 0,9 s), contre 89 pour la page dossier
dans le banc acteurs ; ces temps ne sont pas une garantie de latence. Le test
de 125 accords supplémentaires vérifie un nombre de requêtes stable et la
conservation de la deuxième page au retour. La pagination borne
le HTML mais pas toute la mémoire de projection : coût linéaire dans les parents
accessibles et les périodes de la fenêtre. Pas de prétention à un chargement SQL
intégralement paginé pour des dizaines de milliers de parents.

Pas de drag-and-drop, de nouveau PDF, d'export graphique ni de graphique dans les
rapports. Les distributions/remises/usages restent sur leurs fiches. L'histoire
personnelle sélectionnée est reportée : son utilité ne justifie pas encore de
fusionner ces périodes avec les dates imprécises et faits collectifs. Ce report
ne change pas Situation/Évolution et n'appelle aucune nouvelle règle métier.

## Qualification et recette

Tests automatisés : `personnes.tests_chronologie`, avec bornes exclues,
clippage, prévision dépassée, bénéficiaires partiels, refus d'une prise étrangère,
retours signés depuis les vraies fiches et la prise BD, accès limité à une seule
prestation, séparation de services, révocation, pagination et requêtes groupées
sur un dossier long. Les assertions HTTP/HTML sont distinctes de la recette
visuelle. La suite générale et les tests de rapports/trajectoire sont exécutés
séparément ; voir le bilan de livraison pour leurs résultats exacts.

Recette navigateur, données fictives uniquement :

1. Sur un espace neuf Les Passerelles avec acteurs, ouvrir Samira ou Alex,
   puis Chronologie. Essayer la fenêtre annuelle, Tout et chaque nature.
2. Ouvrir une prise, un séjour, un lieu et une absence. Revenir avec le lien
   proposé ; contrôler dates, filtre et position sur la même ligne.
3. Depuis une prise BD, ouvrir Chronologie des prestations. Vérifier qu'aucune
   prestation d'une autre prise n'y figure ; comparer avec les fiches.
4. Sur une fenêtre d'un jour, vérifier les bornes de sortie et de retour.
   Comparer une prévision dépassée avec un séjour encore ouvert.
5. Refaire au clavier, zoom 200 %, largeur 390 px, puis JavaScript désactivé.
   Tous les libellés et dates restent visibles ; aucune action n'exige un survol.
6. Sur une base de tests, essayer une annulation, une continuation individuelle,
   des bénéficiaires partiels et une révocation entre la frise et sa fiche.
7. Refaire dans un vrai programme local et dans une PWA sous Pyodide/OPFS, à la
   racine et sous préfixe. Les tests Django de ces profils ne remplacent pas
   ces observations. PostgreSQL reste à qualifier dans la matrice existante.


### Observations réellement réalisées

Chromium headless 153.0.8010.12, serveur Django de développement en bouclage,
base Les Passerelles neuve avec contrôle acteurs actif : connexion, dossier
Samira, chronologie, filtre Tout, séjour exact puis retour signé à son ancre.
Captures bureau 1280 px et mobile 390 px inspectées visuellement : bénéficiaires
identifiables, dates visibles, barres distinctes, aucun débordement horizontal.
Parcours des dates au clavier, zoom CSS 200 %, filtrage Absences sans JavaScript
et absence d'erreurs JavaScript observés. Ce n'est ni un audit complet WCAG,
ni une observation WebView2/WebKitGTK, ni une qualification de la PWA/OPFS.

Le banc acteurs des trois profils conservait un ancien libellé de l'équipe :
son assertion est actualisée vers « Équipe de suivi », déjà utilisé sur la base
examinée. Il vérifie désormais aussi la réponse de chronologie et l'absence du
dossier réservé à l'autre service. Cela ne change aucun droit.

Bilan automatisé : suite générale de 878 tests réussie (3 ignorés), puis
9 tests de chronologie sur le dernier code de projection réussis. Le groupe
chronologie/rapports/retours/trajectoire a aussi réussi (28 tests avant l'ajout
du cas annulation/continuation). `check`, absence de migration et `diff --check`
contrôlés. Le banc des trois profils Django a réussi, y compris les PDF réels.
Les dernières retouches purement HTML/CSS (ligne/barre cliquable) sont reprises
dans la recette Chromium ; le bilan général ne qualifie pas les vrais appareils.
