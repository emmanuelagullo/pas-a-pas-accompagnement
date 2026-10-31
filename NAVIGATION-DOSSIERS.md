# NAV1 — Fil d’Ariane et retours

Le parcours Recherche → Dossier → Prise en charge affiche un fil d’Ariane
accessible : Dossiers, identité du dossier, puis date de début de la prise.
Le dernier élément porte aria-current="page" et ne constitue pas un lien.
Les séparateurs sont décoratifs ; les identités longues se replient sans troncature.

« Dossiers », y compris dans le menu principal des deux pages de détail,
conserve la saisie, le mode, les filtres et la page de recherche.
Depuis une prise, le dossier rejoint #prises avec sa sélection et son contexte.
Une personne ouverte depuis un ménage garde son retour explicite vers ce ménage ;
ce lien contextuel ne devient pas un niveau du fil d’Ariane.
Les retours rapport, chronologie et frise restent séparés.

Les liens sont des navigations GET ordinaires : repli sans JavaScript et historique
du navigateur. Les écritures continuent de suivre le contexte signé existant
(personnes/dossier.py), sans nouvelle destination arbitraire ni nouveau droit.
Une correction sur place actualise aussi l’identité du chemin et le titre de l’onglet.
Aucune migration ni modification du modèle métier.

## Réutilisation et qualification

Examen de pas-communs et Petits Pas : conservation des mécanismes existants
de destinations serveur et retours contextuels. Aucun composant de fil d’Ariane
commun à réutiliser trouvé ; le fragment métier reste dans cette application.
Aucune nouvelle version du socle n’est requise.

Tests HTTP/HTML : personnes.tests_entree_bd, personnes.tests_bd6,
personnes.tests_chronologie, personnes.tests_frises ; les suites existantes
couvrent aussi les retours d’écriture, jetons falsifiés et droits.
Le banc JavaScript de recherche reste scripts/verifier-recherche-dossiers.cjs.

Recettes Chromium : personnes.qualification_navigateur.EntreeBDNavigateur
(parcours existant adapté et recette dédiée au clavier, sans JavaScript,
écran de 320 px, noms longs, taille de texte doublée et Précédent).
La taille de texte doublée ne qualifie pas à elle seule le zoom natif du navigateur.
Les recettes PWA communes ciblent explicitement le menu principal pour éviter
l’ambiguïté avec le nouveau lien « Dossiers » du chemin.

Une recette disponible n’est pas une observation réussie. La livraison précise
les commandes effectivement exécutées et leurs résultats ; ni le HTML Django
ni Chromium ne qualifient les vrais programmes Windows ou le runtime Pyodide/OPFS.


# NAV2 — Navigation à l’intérieur des pages

Sur les pages Dossier et Prise en charge, trois accès à icône et libellé restent
disponibles en bas sur écran étroit : Situation, Prises en charge / Prestations,
Sommaire. Le contenu conserve son ordre et sa présentation complète.
Situation rejoint le volet social dans sa lecture courante : ce déplacement
ne change jamais Situation en Évolution ou inversement et n’efface aucun formulaire.

Le sommaire détaillé n’existe qu’une fois. À partir de 80 rem (1 280 px avec
la taille de texte habituelle), il reste visible à gauche. Sous ce seuil,
le bouton Sommaire ouvre un panneau non modal, défilant au-dessus de la barre :
Fermer, Échap ou un lien le ferment. Fermer et Échap rendent le focus au bouton.
Le passage du clavier à la page ferme aussi ce panneau sans modifier la saisie.
Aucun second bandeau fixe n’est ajouté en haut.

Le seuil de 80 rem a été retenu après examen du rendu à 1 366 px : la marge
latérale de 15 rem laisse environ 1 090 px au contenu dans cette disposition.
Le zoom du navigateur réduit la largeur CSS utile et ramène les commandes en bas.
La barre dispose d’une réserve de hauteur mesurée, d’une réserve sans JavaScript
et des marges de sécurité de l’appareil. Les champs focalisés sont remis dans
la zone visible ; la barre s’efface lorsqu’un clavier virtuel est détecté par
la réduction du viewport pendant une saisie. Cette détection reste une aide :
elle ne constitue pas une qualification de tous les claviers mobiles.

## Ancres, droits et actualisations

Les liens du sommaire sont adaptés à la lecture visible. Évolution présente
les situations aux bornes et les éléments datés ; aucune ancienne ancre cachée
ne provoque un changement implicite de lecture. Un lien direct vers une ancre
evolution-* demande explicitement Évolution au chargement, avant toute saisie.
Les ouvertures nécessaires aux ancres ne replient jamais une autre rubrique.

Avec JavaScript, un déplacement remplace l’ancre courante, sans ajouter une
entrée d’historique à chaque rubrique et sans requête serveur. Un
IntersectionObserver indique la rubrique courante avec aria-current="location" :
aucun gestionnaire de défilement ne parcourt la page. Les actualisations
sociales et de prestations réinstallent cette observation et la mesure de la
barre. Le fil d’Ariane et les retours signés de NAV1 sont conservés.

Sans JavaScript, le sommaire reste dans le flux et les trois commandes sont
des liens d’ancre ordinaires. Le lien historique vers la page Évolution reste
disponible. Les destinations métier restent produites sous les droits existants ;
la navigation ne charge aucun objet supplémentaire.

## Mécanismes et qualification NAV2

Le sommaire et l’observation de position existants ont été remplacés par un
mécanisme unique propre au dossier. L’examen de Petits Pas et pas-communs n’a pas
révélé de composant de navigation interne partagé adapté à ces deux lectures :
aucune extraction ni publication du socle n’est nécessaire.

- HTML et droits : personnes.tests_navigation_interne et
  personnes.tests_condition_sociale, dont destinations présentes et sommaire unique.
- Chromium/Linux : personnes.qualification_navigation_interne.NavigationInterneNavigateur,
  avec dossier personne/ménage, ménage de plusieurs personnes, prise, deux lectures,
  formulaires, erreurs serveur, Enregistrer/Annuler, ancres, Précédent,
  absence de requêtes pour les déplacements et commandes tactiles émulées.
- Tailles exercées : 320, 390, 640, 1 280, 1 366 et 1 920 px, texte doublé et
  largeur CSS réduite correspondant au réagencement à fort zoom.
- Les recettes sociales existantes et scripts/verifier-parcours-metier.cjs sont
  adaptés au sommaire unique et aux déplacements sans navigation de l’iframe.
  La qualification navigateur GitLab inclut la nouvelle recette.

Les captures livrées sont des vues réellement rendues et inspectées.
Les vérifications HTTP ne sont pas des observations visuelles. L’émulation
tactile et le texte doublé ne qualifient pas le clavier virtuel d’un appareil,
le zoom natif de tous les navigateurs, WebView2/WebKitGTK ni le vrai runtime
Pyodide/OPFS ; ces limites doivent rester explicites dans la livraison.

Qualification de livraison du 30 octobre 2026, sur la base publique
e80ff28d76cb63a0128b3a027cdf13f8f64ee28b avec NAV2 :
Python 3.12.14, Django 5.2.18, SQLite 3.53.1 et Chromium 134.0.6998.35/Linux
(Playwright Python 1.51.0). Suite générale : 1 026 tests, OK, 35 ignorés.
Après les derniers ajustements de présentation : 43 contrôles ciblés, OK,
dont les 8 parcours Chromium (4 nouveaux, 3 recettes sociales existantes et
le repli clavier sans JavaScript de NAV1). Le banc JavaScript de recherche,
les contrôles Django, l’absence de migration et git diff --check passent.


# NAV3 — Rubriques repliables

Les rubriques personnelles de Situation, la composition du ménage et les
sous-rubriques du projet sont des details/summary natifs, ouverts à la première
consultation. Projet et parcours reste un titre de regroupement : pas de
dépliant englobant supplémentaire. Les informations propres à une prise en charge
et ses missions suivent la même convention. Évolution conserve sa présentation.

Le déclencheur contient le titre et un aperçu court, sans lien ni action d’édition.
L’aperçu disparaît quand le contenu complet est ouvert. Il réutilise les champs
renseignés déjà présentés, au maximum deux repères courts. Les collections
emploient des compteurs ; une absence déclarée, une déclaration non connue et
une rubrique non renseignée restent distinctes. Les listes internes à un champ
sont également comptées. Les numéros administratifs ne sont pas répétés dans
l’aperçu. Aucun diagnostic, total financier ou continuité n’est déduit.

## Portée et mémoire des choix

« Tout déplier / Tout replier » concerne la composition, les rubriques
personnelles et le projet de la lecture Situation. Les options, actions secondaires
et historiques annexes gardent leurs dépliants indépendants. Les actions d’édition
restent à l’intérieur de la rubrique ouverte.

La session navigateur mémorise uniquement des identifiants de rubrique et des
booléens, sous une clé propre à l’utilisateur et au dossier. Aucun aperçu,
renseignement, source ou contenu de formulaire n’entre dans cette mémorisation.
Les identifiants personnels stables permettent de retrouver les mêmes choix entre
Dossier et Prise en charge. Les informations et missions propres à une prise
ont une clé incluant cette prise ; aucune correspondance entre deux prises
différentes n’est inventée. Un dossier personne et un dossier ménage restent
deux contextes distincts.

Le mécanisme reprend la convention sessionStorage déjà utilisée pour les options
sociales, avec une mémoire de page en secours. Si le stockage est refusé ou
malformé, les commandes et actualisations restent utilisables ; les choix
survivent dans la page courante. Une nouvelle page peut alors repartir ouverte.

## Navigation, saisie et impression

NAV2 ouvre aussi un dépliant qui constitue lui-même la cible d’une ancre.
Les liens du sommaire, liens directs et liens du résumé d’erreurs ouvrent
les parents nécessaires sans changer de lecture. L’observation de rubrique
courante est réinstallée après un changement de dépliage. Les choix et la
position restent conservés après les actualisations sociales et de prestations.

Une rubrique contenant un formulaire actif reste ouverte. Cela vaut pour
« Tout replier » et pour son propre déclencheur : un message invite à terminer
ou annuler la saisie. Le refus ne supprime aucune valeur et ne modifie pas les
contrôles serveur, preuves d’état ou confirmations. Les erreurs restent dans
une rubrique ouverte et leurs liens rejoignent les champs concernés.

Sans JavaScript, tous les contenus sont ouverts initialement ; les commandes
globales sont masquées et les dépliants natifs restent consultables et éditables.
L’impression expose le contenu des rubriques concernées, même fermées à l’écran,
sans changer les choix mémorisés. Les historiques annexes et les deux lectures
gardent leur périmètre antérieur. La qualification d’impression porte sur
Situation hors saisie active.

## Qualification et limites NAV3

- personnes.tests_rubriques_sociales : absence/non connu/non renseigné,
  collections longues, listes internes, aperçu borné et échappé, zéro requête
  pour la fabrication d’un aperçu à partir des données déjà lues, titres et
  actions hors des déclencheurs.
- personnes.qualification_rubriques_sociales : dossier individuel, ménage
  de plusieurs personnes et prise en charge ; commandes et clavier, 320/390/
  640/1 366 px, texte doublé, ancres NAV2, deux lectures, erreurs serveur,
  Enregistrer/Annuler, séparation par utilisateur, stockage refusé et
  actualisations sociales/prestations.
- Les recettes NAV2 et sociales existantes sont rejouées. Les recettes communes
  PWA ouvrent explicitement les rubriques nécessaires et la CI navigateur
  GitLab inclut la nouvelle qualification.

Les captures livrées ont été inspectées. L’impression Chromium est exercée sans
JavaScript et le PDF produit est contrôlé, dont le texte d’une rubrique fermée.
Cela ne qualifie pas une imprimante physique, tous les navigateurs, le zoom
natif, le clavier virtuel réel, les programmes Windows/Linux ou Pyodide/OPFS.
Ce lot réduit la longueur visible ; aucun gain de performance serveur n’est
annoncé. Aucun nouveau modèle, droit ou format de copie.

Qualification du 30 octobre 2026 sur la base publique NAV2
46d5b3118f9b326241be9b3be052550c78a0e616 : Python 3.12.14, Django 5.2.18,
SQLite 3.53.1, Chromium 134.0.6998.35/Linux et Playwright Python 1.51.0.
Suite générale : 1 031 tests, OK, 35 ignorés. Un test supplémentaire sur les
listes internes a ensuite été ajouté. La validation ciblée finale comprend
28 contrôles réussis, dont 12 parcours Chromium (5 nouveaux, 4 NAV2 et
3 recettes sociales). Le texte du PDF sans JavaScript contient bien les
coordonnées de la rubrique fermée à l’écran. Contrôles Django, absence de
migration, banc JavaScript de recherche, syntaxes JS et git diff --check : OK.


## NAV4 — Volet social repliable

« Situation sociale et projet » devient un dépliant natif unique englobant
Situation, Évolution et leurs commandes. À la première visite avec JavaScript,
le volet et les rubriques sans choix préalable sont repliés. Les choix NAV3
existants sont conservés ; fermer le volet ne réinitialise pas ses rubriques.
Le titre et un repère de portée restent visibles, sans synthèse sociale ajoutée.

Tout déplier/Tout replier conserve sa portée intérieure et ne ferme pas le volet.
Les ancres ouvrent tous les parents nécessaires. Aucun changement implicite de
Situation/Évolution ; un formulaire actif bloque aussi le repli du parent.
La mémoire par utilisateur/dossier reste limitée aux identifiants et booléens.
Sans stockage, la page et ses actualisations gardent une mémoire temporaire ;
une nouvelle page retrouve les défauts. Sans JavaScript, les dépliants sont
ouverts initialement. À l’impression le parent et les rubriques sont visibles.
Aucun changement du modèle, des droits ou des règles temporelles ; aucun gain
serveur annoncé.

Qualification NAV4 : Python 3.12.14, Django 5.2.18, SQLite 3.53.1,
Chromium 134/Linux. Les recettes ciblées couvrent dossier individuel, ménage
à plusieurs personnes, prise en charge, clavier, largeurs 320–1920 CSS px,
texte doublé, liens directs Situation/Évolution, erreurs serveur, Enregistrer,
Annuler, actualisation des prestations, mémoire isolée et stockage refusé.
Le test sans JavaScript ferme aussi le parent avant l’impression ; le PDF
contient bien les coordonnées masquées à l’écran. Les captures ont été
inspectées. Les recettes PWA sont adaptées et vérifiées syntaxiquement ;
le vrai runtime Pyodide/OPFS, le clavier virtuel, le zoom natif et les autres
navigateurs ne sont pas qualifiés par ces tests.

Les 19 tests ciblés sont validés (6 tests unitaires/HTML et 13 parcours Chromium).
La dernière adaptation de recette NAV2 a été rejouée seule avec succès après
les 18 autres tests réussis. Contrôles Django, absence de migration, syntaxe JS,
banc de recherche et `git diff --check` validés.

## NAV5 — Suivre la rubrique dans un sommaire long

Sur écran large, le sommaire conserve son défilement indépendant. Quand la
rubrique courante sort de sa zone visible, seul le panneau défile du minimum
nécessaire, sans animation ni déplacement du focus ou de la page. Une branche
fermée est représentée par son intitulé, sans ouverture automatique. Le suivi
est suspendu lorsque le pointeur ou le focus parcourt le menu, puis reprend à
sa sortie. Il utilise les notifications IntersectionObserver existantes ;
aucun gestionnaire de défilement continu ni requête serveur n'est ajouté.

## NAV6 — Prestations en une colonne et interactions cohérentes

Les blocs Hébergement, Repas et aides restent dans leur ordre métier, sur une
colonne à toutes les largeurs. Le bouton rond sélectionne les actions ; le lien
du titre et du résumé ouvre la fiche complète existante. Les actions restent
séparées des liens et des frises. Les accueils prévus gardent leurs commandes
explicites sans inventer un séjour réalisé.

Avec JavaScript, une sélection actualise la page sans ajouter une entrée
d'historique. Sans JavaScript, un bouton explicite valide le choix par GET.
Les retours signés conservent la recherche, les vues sociales et les sélections,
y compris la prestation consultée directement. Les choix des quatre familles
d'aides sont des identifiants de navigation dans le contexte signé ; ils ne
créent aucune autorisation et ne modifient ni les modèles ni leurs règles.

Les actions courantes restent sur place, dans une seule zone d'édition et avec
une largeur de formulaire bornée. Les protections de saisie, erreurs et preuves
d'état existantes restent actives. Aucune nouvelle Form4 générique n'est créée.
Les fiches spécialisées demeurent accessibles directement par les liens natifs,
y compris sans JavaScript et dans un nouvel onglet.

Qualification NAV5/NAV6 : Python 3.12.14, Django 5.2.18, SQLite 3.53.1 et
Chromium 134/Linux. Les 25 tests ciblés sont validés, dont 14 parcours Chromium
(sommaire, rubriques sociales et prestations). La suite générale a exécuté
1 032 tests avec succès, dont 38 ignorés ; les deux tests HTTP ajoutés ensuite
ont également été exécutés avec succès. La recette de prestation a été rejouée
après correction du contrôleur : refus serveur d'une date hors accord, saisie
conservée, correction et enregistrement réel, Annuler, blocage d'un changement
de sélection pendant la saisie, consultation/retour et repli sans JavaScript.
Les contrôles Django, absence de migration, banc de recherche et syntaxe JS
passent. Le contrôleur lit l'attribut action du formulaire : un bouton nommé
« action » ne peut plus masquer son URL de soumission.

Les captures étroite/portable, éditeur et sommaire suivi ont été inspectées.
Les dispositions 390/640/1366/1920 CSS px et les libellés longs sont couvertes ;
la recette NAV2 couvre aussi 320 px et le texte doublé. Le vrai runtime PWA,
Firefox/Safari, le zoom natif et le clavier virtuel ne sont pas qualifiés ici.
La recette commune PWA ne comporte pas de sélecteur de carte devenu obsolète ;
la qualification navigateur CI inclut désormais le parcours NAV6.
