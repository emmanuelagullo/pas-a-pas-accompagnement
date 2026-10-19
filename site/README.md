# Site public Hugo

Même organisation que Petits Pas : le contenu du site est dans le dépôt
applicatif. Le job site-public construit Hugo ; pages vérifie et publie les
mêmes fichiers. Aucun modèle, secret, base ou export privé n'est incorporé.
Le thème est local et ne charge ni police distante, script tiers ou thème Git.

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
