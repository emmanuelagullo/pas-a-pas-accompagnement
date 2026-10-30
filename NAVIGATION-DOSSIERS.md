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
