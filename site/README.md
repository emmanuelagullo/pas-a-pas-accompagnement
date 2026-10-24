# Site public Hugo

Même organisation que Petits Pas : le contenu du site est dans le dépôt
applicatif. Le job site-public construit Hugo ; pages vérifie et publie les
mêmes fichiers. Aucun modèle, secret, base ou export privé n'est incorporé.
Le thème commun est épinglé par sous-module Git ; il ne charge aucune police distante ni script tiers.

```sh
hugo --source site --baseURL https://pas-a-pas-accompagnement.gitlabpages.inria.fr/pas-a-pas-accompagnement/ --cleanDestinationDir --minify --panicOnWarning
python3 scripts/verifier-site-public.py --sortie site/public --base-url https://pas-a-pas-accompagnement.gitlabpages.inria.fr/pas-a-pas-accompagnement/
```

La CI reprend l'image Hugo Extended 0.140.2 épinglée de Petits Pas.
Les liens de démonstration, PWA et releases sont des adresses publiques ; ne
pas leur substituer les artefacts temporaires de CI. Les fonctions seulement
prévues sont explicitement distinguées des boutons accessibles.

Trois projets :

- dépôt applicatif : site publié sous /pas-a-pas-accompagnement/ ;
- pas-a-pas-accompagnement.gitlabpages.inria.fr : redirection de la racine ;
- pas-a-pas-accompagnement-pwa : inclusion du pipeline PWA, publication manuelle.

Pour cette arborescence, désactiver Use unique domain dans les réglages Pages
des trois projets et autoriser l'accès public. Configurer cela avant les essais
PWA durables, car un changement d'origine ou chemin ne transfère pas les données.
Ne pas confondre le projet racine de redirection et le dépôt contenant le site.

Les contenus du site ajoutés ici sont sous AGPL-3.0-or-later comme le dépôt.
Les pages utilisent exclusivement des exemples fictifs. Toute évolution de
fonction met à jour d'abord les faits et les libellés dans les pages liées.

## Thème commun et vérification (#SOC)

Avant toute construction (clone neuf compris) :

```sh
git submodule update --init site/theme-communs
```

Le gitlink épingle un commit public de Pas communs, utilisé uniquement pour
le thème Hugo. Lire `site/theme-communs/HUGO.md`. Ne pas utiliser `--remote`
en CI. Aucun changement de wheel Python ou de déploiement applicatif.
La CI initialise le sous-module dans les jobs Hugo ; les contenus et artefacts
métier continuent d’être préparés par les jobs habituels.

Menus : `site/hugo.toml`. Identité : `site/static/css/identite.css` et paramètre
`themeColor`. Accueil, contenus, comptes fictifs et shortcodes métier restent
locaux. Les layouts génériques, guide, navigation, encadrés et CSS viennent du
thème : ne pas en réintroduire une copie locale.

Après la préparation et la construction Hugo :

```sh
python3 site/theme-communs/hugo/verifier-site.py --sortie site/public --base-url https://example.invalid/produit/
```

Utiliser la même URL de base pour Hugo et le contrôle. Tester aussi la racine
et le préfixe public. Le contrôle attend les captures et fichiers d’essai du
produit lorsqu’ils sont référencés. Il ne remplace pas la revue clavier et
mobile/ordinateur. Pour une évolution commune : publier d’abord le commit du
socle sur GitLab Inria, puis avancer les sous-modules applicatifs, construire
et publier les sites. Le miroir GitHub conserve son rôle de miroir ; il n’est
pas utilisé pour récupérer le thème. Leurs URL restent inchangées.


## Rubriques et disponibilité

Les anciennes URL `/essayer/`, `/premiers-pas/` et `/le-projet/` sont conservées.
Les nouvelles rubriques complètent les intentions de Petits Pas : Démarrer,
Guide, équipes d’accompagnement, accès, institutions, données et technique.
Aucune équivalence école/CHRS ou classe/service. Les comptes publics et la visite
viennent de `personnes/demonstration.py`, `templates/decouverte.html` et
`DEMONSTRATION.md`, pas d’une sauvegarde distribuée.

Le 20 octobre 2026, le HTML public de la PWA a été consulté : il ne proposait
pas encore le sélecteur Établissement Les Passerelles. Le serveur Render n’a pas répondu
pendant la vérification. Les pages gardent donc les instructions conditionnelles
et renvoient aux versions effectivement publiées, sans déclarer les déploiements
à jour. Recontrôler les publications avant d’enlever cette réserve.

Le sous-module utilise l’URL HTTPS absolue de GitLab Inria déclarée dans
`.gitmodules`. Cette déclaration fait foi pour la récupération du thème ;
l’ancienne mention du miroir GitHub dans le contrat du commit importé est
historique. Le commit adopté est celui effectivement publié sur Inria :
`5d64e2487939093bd6378a8a1611da95d93830ca`. Aucune reproduction de SHA avec
une commande spéciale `git am` n’est nécessaire.

## Guide métier CHRS5–7

Les fiches accompagnement, travail-du-jour et corriger-saisie décrivent les
parcours du code courant. Conserver les réserves sur la version effectivement
installée/publiée. Ne pas annoncer l’attribution de droits aux comptes existants :
autoriser_chrs7 est une action explicite. Aucun changement du thème ou gitlink.

## CHRS10 — Synchronisation documentaire

Les fiches de `site/content/guide/` utilisent `fiche: true`, comme les fiches
du guide Petits Pas. Le rendu dépend du thème partagé épinglé ; ne pas dupliquer
les layouts. Les nouvelles pages décrivent CHRS8–10 et les exemples fictifs.
Aucune capture d'écran n'est ajoutée sans capture réellement produite par la CI :
le pipeline actuel ne contient pas de job de captures du scénario CHRS.
Une future capture automatisée doit utiliser uniquement un jeu fictif neuf,
avec masquage des secrets et vérification des pages générées avant publication.

## CHRS10-11 — Captures publiques

Le job `captures-demonstration` reprend le principe de Petits Pas : navigateur
Playwright épinglé, démarrage d’une base jetable neuve avec `start-render.sh`,
contrôle des pages et captures PNG comme artefacts CI. Le job `site-public`
consomme ces artefacts avant Hugo ; les pages du guide et des équipes affichent
la galerie `captures-passerelles`. Aucun PNG n’est conservé dans Git.

Pour tester localement, utiliser **uniquement** une instance fictive jetable :

```sh
python3 scripts/capturer-site-chrs.py --base-url http://127.0.0.1:8000 --output site/static/captures
```

Ne pas exécuter ce script sur une instance contenant des dossiers réels.
La vérification visuelle du rendu du thème partagé reste nécessaire.
