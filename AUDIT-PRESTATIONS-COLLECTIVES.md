# Prestations collectives : compacité et suivi individuel

Audit du 4 novembre 2026, sur le main public
`9dee5bd8e28ca6e9a7ca8c7b5ecb5f6a925c77b3` (#NAV7).

## Constat dans Pas à Pas

| Domaine | Création pour plusieurs bénéficiaires | Présentation actuelle dans Form3 |
| --- | --- | --- |
| Hébergement | Un accord partagé ; une arrivée confirmée crée un séjour par personne sélectionnée | Une carte par séjour, même lorsque dates et lieu sont identiques |
| Repas | Un accord par service choisi, partagé par les bénéficiaires | Une carte par accord ; les distributions effectives sont personnelles |
| Transport, bons alimentaires, produits, accueil de jour | Un accord partagé ; une remise peut concerner plusieurs bénéficiaires | Une carte par accord ; les réalisations sont détaillées à l’ouverture |

Sources : `admission.accueillir`, `admission.enregistrer_arrivee`,
`hebergement.admettre_individuellement`, `repas.accorder`,
`repas.accorder_services`, `aides.accorder` et `aides.remettre`.
L’hébergement prévu ne crée pas encore de séjours effectifs. Les anciens séjours
collectifs restent possibles dans le modèle ; cette diversité ne doit pas être
réécrite par un changement de présentation. NAV7 n’a pas introduit la création
individuelle, mais son ouverture sous chaque carte ne corrige pas la répétition.

Une personne n’est pas une chambre. Une quantité remise collectivement n’est
pas multipliée par ses bénéficiaires. Les distributions de repas, usages et
paiements ne se déduisent pas des autorisations. Ces distinctions doivent rester
vraies quel que soit le regroupement à l’écran.

## Référence Solenne examinée

Archives fournies dans Library : `avit001-java-files.tgz` et
`avit001-listes.tgz`. Lecture statique des sources, sans exécution de J#.

Dans `sejour.java`, une fiche rassemble une période, un lieu, les effectifs
`nbre_adulte` / `nbre_enf`, les collections `adultes` / `enfants`, ainsi que des
quantités de repas et de transports. `estSejour` distingue hébergement et repas.
`Form3.java`, notamment `RetoucheRepas`, réemploie la fiche en adaptant les
libellés et contrôles ; les quantités de transport sont chargées ensemble.
Les fichiers `.agu` examinés sont des listes de propositions (hôtels,
restaurants, catégories d’âge, budgets…), pas une raison de dupliquer une
fiche par bénéficiaire. Leur contenu n’est pas importé dans l’application.

Solenne appuie donc la recommandation d’une unité de lecture collective,
avec les détails dans cette unité. Son objet `sejour` réunit toutefois des
notions aujourd’hui séparées : il ne démontre pas que les règles temporelles,
les réalisations ou le modèle financier actuels doivent être fusionnés.
La comparaison ne constitue pas un audit exhaustif de toutes ses fonctions.

## Recommandation pour un prochain lot

Présenter une carte d’hébergement par accord visible dans la prise, puis une
liste dépliable des séjours autorisés à la lecture dans ce contexte. Le titre
et Ouvrir doivent développer le même ensemble sur place. Afficher les personnes
concernées, puis une période et un lieu communs seulement s’ils sont réellement
communs ; sinon annoncer des situations différentes et donner leurs détails.
Sur un dossier individuel, ne montrer que les faits de la personne.

Les actions ordinaires doivent permettre une sélection explicite des personnes
ou séjours concernés en réutilisant les actions collectives déjà présentes.
Une sortie différente ou un changement de lieu reste une action individuelle,
accessible dans la même carte. Prolonger concerne l’accord partagé et doit le
dire. Annuler une arrivée ne doit pas annuler implicitement toutes les autres.
Les archives et droits restent contrôlés séparément.

Garder la même grammaire pour les repas et aides : carte commune, bénéficiaires
visibles, réalisations dépliables, actions de portée explicite. Ne pas fusionner
deux accords sur la seule égalité des dates, du lieu ou du libellé. Ne pas cacher
une divergence derrière un faux résumé homogène. Préserver les liens directs,
le retour au séjour exact, les saisies actives, les frises et les PDF.

Cette recommandation porte sur la présentation. Aucun regroupement de données,
aucune migration et aucun changement de calcul ne sont implémentés dans le lot
correctif NAV8. La réalisation de cette présentation collective reste à décider.
