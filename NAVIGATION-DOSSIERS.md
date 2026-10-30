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
