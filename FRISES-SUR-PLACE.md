# Frises compactes sur place

Base examinée : `main` Inria `481f045fbba52eeb4f31bac2ed8de62c285253fc`
(ACT11, premier lot chronologique déjà intégré). Le socle 0.9.0 épinglé reste
inchangé. Les évolutions ACT09–11 sont conservées, en particulier la différence
entre identité repérable et faits accessibles. Données fictives uniquement.

## Utilisation

Cocher **Frise** sur l'écran de recherche, dans Prises en charge du dossier ou
dans Prestations de la prise. La préférence est commune à la session Django,
désactivée initialement, sans changer de destination. Les listes, sélections,
filtres, formulaires et actions restent ceux du parcours BD.

- Form1 : une bande de 18 px sous le nom, avec les prises et les prestations
  consultables en miniature. Les dossiers de la page partagent la même échelle.
- Form2 : une bande sous la période de chaque prise, dans sa ligne actuelle.
- Form3 : des bandes dans les blocs actuels Hébergement, Repas et autres aides,
  avec une échelle relative commune à la prise. L'organisation des blocs reste
  identique ; sur écran étroit, ils se succèdent comme auparavant.
- Le petit **+ / Élargir** ouvre localement les périodes et leurs liens exacts.
  Les repères se consultent au survol, au focus et au toucher. Échap masque
  leur détail sans déplacer le focus. Les dates restent lisibles en texte.
- Le retour signé réouvre le dépliage d'origine et vise son ancre, y compris
  depuis une prestation ouverte dans la recherche. La recherche conserve ses
  critères et sa page. La préférence est stockée côté serveur ; le changement remplace seulement les fragments graphiques, sans recharger
  la page ni remplacer la lecture Situation/Évolution. Une saisie en cours
  doit être terminée ou annulée, selon les contrats existants des formulaires.
- Sans JavaScript, **Appliquer** enregistre cette même préférence par POST/CSRF.
  Les dépliages natifs, les liens et la restitution textuelle fonctionnent aussi.

L'ancienne page Chronologie reste accessible par ses URL et retours signés,
pour compatibilité. Elle n'est plus l'entrée proposée sur les écrans BD.

## Représentation commune

Contour : prise en charge. À l'intérieur, quatre pistes fixes : séjour enregistré,
autorisation d'hébergement, repas accordés, autres autorisations d'aides.
Les périodes autorisées sont hachurées et distinctes du séjour enregistré.
Lieux et absences se détaillent à l'élargissement du séjour concerné.
Une absence ne clôt pas le séjour. Repas accordé ne signifie pas distribué ;
transport autorisé ne signifie pas remis ou utilisé.

Les superpositions sont calculées sur les intervalles accessibles. **≋** indique
plusieurs éléments sur une piste, sans augmenter la hauteur. Si la projection
dépasse 128 segments, une synthèse de densité sur 64 cellules par piste remplace
ces marques, explicitement signalée comme synthétique. En dehors de ce cas,
les bornes graphiques sont exactes à la précision du rendu. Les dates exactes
restent dans les détails. Le contour orange indique des prises qui se recouvrent,
à examiner, sans les qualifier d'anomalies. Les autres superpositions ne créent
aucune nouvelle règle d'alerte métier.

Le futur n'est pas dessiné. Un signe **›** indique des bornes ou informations
futures consultables dans les détails et les fiches. Les fins prévues restent
nommées séparément dans les descriptions des prises. Un début aujourd'hui peut
être représenté par une marque au bord droit, sans durée future supposée.
Les accords annulés restent nommés dans les détails mais ne remplissent pas les
pistes d'activité. Une continuation garde son libellé et son propre segment.

## Échelles automatiques

Form1 et Form2 : borne droite aujourd'hui, au moins la dernière année civile,
origine gauche au plus ancien début consultable des objets comparés. La même
transformation est appliquée à toutes les lignes de la page.

Pour l'ancienneté `a` en jours et la longueur `A` de la dernière année civile :

- `d(a) = a` jusqu'à `A` ;
- `d(a) = A + 90 × log(1 + (a − A) / 90)` au-delà ;
- position depuis la gauche : `1 − d(a) / d(ancienneté maximale)`.

Le raccord est continu, avec la même pente à la frontière de l'année. Le passé
plus ancien se comprime progressivement dans le bon sens. Les anniversaires
civils et le 29 février sont traités explicitement. La compression ne permet
pas de comparer des longueurs anciennes comme des durées linéaires.

Form3 : échelle linéaire du début de la prise (ou d'un fait lié plus ancien)
à sa clôture effective, sinon aujourd'hui. Aucune fin prévue ne ferme cette vue.
Les mini-frises ne demandent aucune saisie de dates. Les réglages manuels restent absents des miniatures. Ils sont disponibles
uniquement après élargissement, dans la commande discrète Période (voir ci-dessous).

## Évolution sur place

L'entrée Évolution de Situation sociale et projet reste intégrée. Par défaut,
la comparaison ne montre que les informations qui diffèrent aux deux bornes.
**Toutes les informations** restitue la table complète. Les événements datés
restent distincts de cette comparaison et du journal des corrections.

Pour une prise, les bornes proposées sont Début de la prise, son dernier jour
si elle est close, Aujourd'hui et À une date. Une prise ouverte finit par défaut
à aujourd'hui, même si sa prévision est dépassée. Les colonnes nomment les
choix effectifs et leur date. Pour le dossier, les références sont le début
et, lorsque toutes les prises consultables sont closes, le dernier jour des
prises connues : aucune ouverture/fermeture du ménage ou arrivée dans un service
n'est inventée. Les dates futures restent refusées pour la lecture sociale.

Les témoignages anciens divergents restent consultables et ne deviennent pas
une source personnelle consolidée. Une différence de leurs valeurs aux bornes
peut laisser apparaître la ligne même si la valeur personnelle est inconnue.
L'ancienne URL spécialisée conserve sa présentation exhaustive par défaut.
Deux tests historiques de provenance demandent désormais explicitement cette
présentation exhaustive lorsqu'ils vérifient une valeur restée identique.

Le sélecteur d'Évolution n'est pas fusionné avec Complet / Informations renseignées
de Situation : « différent entre deux dates » et « connu à une date » ne sont
pas des critères équivalents. Les sources, droits et définitions restent inchangés.

## Accès, coût et limites

Les identités sont revalidées en un groupe dans le périmètre actuel de l'acteur.
Chaque modèle passe ensuite par ses gestionnaires contrôlés, sans gestionnaire
intégral ni SQL brut. Les bénéficiaires sont chargés en listes explicites via
Prefetch/to_attr ; cela évite la réexécution de requêtes de relations à chaque
carte sous le contrôle actif. Les tests comparent 1 et 9 ménages accessibles.
Une identité seulement repérable ne produit aucune période. Une vue personnelle
exige le bénéfice explicite sur chaque prestation et segment de séjour.

Les marques de prestations sont bornées par les pistes de densité ; un contour
reste associé à chaque prise consultable ; chaque dépliage propose
au plus 80 premiers repères, puis renvoie aux listes et fiches existantes.
Les lectures en mémoire restent proportionnelles à l'histoire accessible des
25 dossiers de la page. Il ne s'agit pas encore d'une pagination SQL de chaque
histoire longue. Ni les modèles, ni les sources sociales, ni les habilitations,
ni les dépendances applicatives ou le socle ne sont modifiés. Aucun ancien jeu
n'est enrichi ou réinitialisé.

## Recette

Tests dédiés : `personnes.tests_frises`. Vérifier également les tests de
chronologie, recherche BD, dossier, retours de rapports, condition sociale et
trajectoire. Le banc `scripts/qualifier-acteurs-profils.py` exerce maintenant
l'activation et les mini-frises dans les trois configurations Django, sous
préfixe pour la PWA ; il ne remplace pas Pyodide/OPFS ou les programmes natifs.

Observation Chromium réelle sur un nouveau jeu Les Passerelles : activation
en Form1, alignement et hauteur 18 px, navigation Form2/Form3, dépliage du séjour,
repères au clavier, Évolution intégrée, écran 390 px et désactivation sans JS.
Les captures ont été inspectées. Les vrais programmes, Pyodide/OPFS et
PostgreSQL restent à qualifier ; ce n'est pas un audit WCAG complet.

Bilan de qualification du lot : suite générale de 919 tests réussie, 3 ignorés ;
contrôle Django, absence de migration et diff contrôlés. Le banc des trois
profils réussit : 106 requêtes pour son dossier sans frise, 114 avec frises.
Ce sont des mesures locales sur son jeu fictif, pas une garantie de latence.
Les retouches finales de fragments HTML/JS sont vérifiées par les tests ciblés
et par Chromium : la bascule conserve notamment le panneau Évolution déjà
ouvert, sans remplacement de son DOM. Le banc JS de recherche BD4 réussit aussi.


## Affinage : commandes, périodes et première frise personnelle

Base du patch complémentaire : `fdc0b52880728ebdd638748b4c92f06ca71ce761`,
`main` Inria examiné le 29 octobre 2026 ; son arbre contient le lot précédent
et ACT12–13 (messages d’attribution et cahier unifié), conservés intégralement.
Aucun changement de source sociale, modèle, migration, dépendance, droit ou socle.

La commande **Frise** suit le compteur de résultats en Form1 et le titre
Prises en charge / Prestations en Form2 / Form3. Elle n'occupe plus une ligne
propre. Nouvelle garde sa place à droite. Une recherche dynamique réinitialise
les commandes de son fragment, avec les mêmes jetons et la même préférence.
Sur écran très étroit, la ligne peut se replier plutôt que déborder.

**+ Élargir / − Réduire** reste ancré à droite dans les deux états. Le texte
accessible suit l'état et identifie la frise. Les repères temporels ont une
apparence stable au survol et au focus ; seul leur détail apparaît. La légende
réutilise les couleurs et les motifs effectivement dessinés, accompagnés de mots.

Dans le dépliage seulement, **Période** ouvre :

- Cadrage initial ou Dernière année ;
- À des dates : bornes symboliques initiales, Il y a un an, Aujourd'hui lorsque
  c'est effectivement la borne droite, ou À une date qui active son champ ;
- un curseur Zoom et un curseur Position, ce dernier actif après zoom ;
- Réinitialiser pour restaurer exactement le cadrage et l'échelle initiaux.

Le zoom et les fenêtres choisies utilisent une échelle linéaire, explicitement
nommée. Le cadrage initial conserve son échelle comprimée ou linéaire d'origine.
Les limites sont celles de la période initiale, sans futur supplémentaire. Les
lignes textuelles restent complètes, y compris hors fenêtre. Les barres de la
miniature ne changent pas et restent alignées avec les autres objets. Les débuts
aujourd'hui gardent une marque ponctuelle ; le zoom n'en fait pas une durée.
La reprojection se fait uniquement sur les données déjà filtrées et présentes,
sans nouvelle requête ni réponse JSON métier. Les réglages sont mémorisés dans
l'onglet (sessionStorage, repli en mémoire si indisponible), par compte, page, objet et
bornes initiales ; ils se restaurent à la réouverture après un retour. Les
réglages ne modifient ni recherche ni dates sociales. Sans JavaScript, les
réglages graphiques sont cachés ; la vue élargie initiale et ses textes restent
consultables, ainsi que la préférence serveur via Appliquer.

Dans **Évolution**, Éléments datés propose **Liste complète / Frise personnelle**,
sur place par le même formulaire GET et le même contrat de fragment. La table
comparative entre les deux dates reste indépendante. La première frise retient
les déclarations personnelles de situation, les ressources et les dettes déjà
chargées par la trajectoire. Des points sur une échelle commune à la sélection
montrent leurs dates d'effet ; les textes, bénéficiaires, fins explicites,
sources et liens d'historique restent lisibles sans survol. Aucun segment ne
suppose une continuité personnelle ou une appartenance au ménage entre deux
faits. Aucun fait ancien en cours n'est redaté à l'ouverture de la fenêtre.
Les versions corrigées sont celles lues aujourd'hui ; les corrections et retraits
ne deviennent pas des événements métier supplémentaires. Les données de naissance
imprécises, les autres séries sociales non encore projetées, les récits et les
journaux ne sont pas injectés dans cette première vue. Les membres, bénéficiaires
et droits sont ceux du constructeur de trajectoire, avant cette projection, qui
n'ajoute aucune requête.

### Projet : examen et limite volontaire

ObjectifParcours dispose de VersionObjectif, avec début/fin d'effet, état,
thème, titre et échéance visée. Les états sont En cours, Atteint, Suspendu et
Abandonné. L'échéance est une prévision ; elle n'est pas la date d'atteinte.
Les anciennes InformationsAccompagnement n'ont pas de date d'effet et ne doivent
pas être transformées en histoire métier. Une future représentation peut être
utile pour les versions datées, dans le bloc Projet et parcours existant, mais
n'est pas ajoutée par ce patch : il reste à préciser le dessin des états et des
échéances, ainsi que la portée collective. Ce point ne change aucune définition
métier existante et n'empêche pas la livraison des améliorations indépendantes.

### Recette complémentaire

1. Form1 : rechercher, vérifier compteur et Frise sur la même ligne ; changer
   la saisie et vérifier que le repli Appliquer reste caché avec JavaScript.
2. Élargir puis réduire : commande à droite, libellé et nom accessible adaptés.
3. Survoler / atteindre au clavier un repère : trait stable, bulle consultable,
   masquable par Échap. Comparer les cinq échantillons aux marques de la frise.
4. Ouvrir Période, zoomer, se déplacer, choisir des bornes symboliques puis une
   date ; une paire invalide affiche une explication et conserve le dessin.
5. Réinitialiser : dessin et échelle initiaux ; vérifier que la miniature n'a
   jamais changé. Naviguer vers une source et revenir : cadrage restauré.
6. Form2 et Form3 : mêmes contrôles ; Nouvelle reste à droite en Form2.
7. Évolution : choisir Frise personnelle, puis revenir à Liste complète ; ne
   pas remplacer la table comparative. Vérifier des changements corrigés,
   les droits partiels et la composition datée du ménage.
8. Refaire sur 390 px, au clavier et sans JavaScript. Les contrôles de zoom ne
   sont pas disponibles sans JavaScript, les dates et liens le restent.

Les tests automatisés vérifient notamment la projection ponctuelle d'aujourd'hui,
les corrections personnelles, les autres bénéficiaires et les droits partiels.
Les observations Chromium sont distinctes des tests HTTP/HTML. Les programmes
natifs, PostgreSQL et le vrai runtime Pyodide/OPFS restent hors qualification locale.

Qualification complémentaire observée : 24 tests ciblés réussis ; contrôles
Django et absence de migration confirmés ; banc JavaScript de recherche réussi.
Chromium a exercé Form1/2/3, le retour au cadrage mémorisé, la stabilité du repère
au survol, les bornes symboliques et champs grisés, la restitution personnelle
avec deux points fictifs, sa conservation pendant la bascule Frise, 390 px sans
débordement horizontal et le vrai repli sans JavaScript. Aucune erreur JavaScript
observée. Les captures ont été inspectées. Les trois profils Django réussissent,
avec ACT13, le coût du dossier de qualification est de 110 requêtes sans frise,
118 avec (soit toujours huit requêtes supplémentaires pour les frises). Ces observations ne qualifient pas Pyodide/OPFS ni les programmes natifs.

La suite générale sur la base 5c40ae0 a réussi : 920 tests, 3 ignorés. Après
intégration d’ACT12–13 sur fdc0b52, les 43 tests ciblés des frises, de la
trajectoire, des liaisons et des messages d’attribution réussissent. La suite
générale entière n’a pas été relancée sur cette seconde base ; les validations
complémentaires ciblent les zones modifiées et leurs interactions.
