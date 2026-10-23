# Textes narratifs enrichis — contrat v1

Les commentaires de dossier (personne, ménage, prise), notes partagées,
transmissions du cahier de liaison, objectifs courts/longs du projet et bilans
sociaux proposent une édition visuelle légère : paragraphes, gras, italique,
listes à puces ou numérotées, liens web et annuler/rétablir. Enregistrer reste
l'acte de confirmation ; les motifs restent des champs simples. Aucun changement
implicite de droits, de rattachement ou de disposition des pages métier.

Les événements courts, animaux, sources, motifs, identités et libellés restent
en texte simple. Petits Pas et pas-communs sont inchangés : une extraction
technique ultérieure exige un usage établi et la qualification des consommateurs.

## Données et reprise

La migration 0014 ajoute des colonnes JSON nullables, sans convertir les textes
historiques. Le contenu narratif enrichi est explicite : `{version: 1, doc: ...}`.
`personnes.textes_riches` reconstruit et valide ce petit schéma ; aucun HTML
libre, Markdown, style ou attribut d'événement n'est accepté. Le document fait
foi et la colonne texte est sa projection en texte simple. La projection n'est
jamais une seconde source éditable lorsque le document est présent.

Une simple consultation ou ouverture d'éditeur ne convertit pas un ancien texte.
`**ancien**`, les chevrons et les URL anciennes restent littéraux. Une saisie
visuelle modifiée produit le format v1. Sans JavaScript, les anciens textes
restent éditables ; les textes enrichis sont consultables en texte simple et
protégés en lecture seule. Aucun basculement avec perte silencieuse de format.

Les limites de 1 000 / 2 000 / 4 000 caractères comptent le texte lisible côté
Python. Le document est borné à 65 536 octets, 2 048 nœuds et 12 niveaux.
Le compteur JavaScript compte les points de code Unicode comme Python ; la
validation Python reste autoritaire. Ces bornes techniques ne modifient pas
les limites métier des champs courts.

## Sécurité et restitutions

Le rendu Python échappe chaque texte et chaque attribut et ne produit que des
balises fixes. Les URL doivent être HTTP(S), absolues, sans identifiants ni
espaces ; aucune ressource n'est téléchargée par le rendu. Les liens de lecture
ouvrent un nouvel onglet avec `noopener noreferrer`. Un document d'archive
invalide retombe sur sa projection échappée, jamais sur du HTML brut.

Le collage est limité au schéma de l'éditeur ; images, scripts et contenus
embarqués sont exclus, les mises en forme non prises en charge disparaissent
dans la zone avant enregistrement. La saisie n'active pas automatiquement une
syntaxe Markdown. Pas de téléchargement d'image, de police ou de conversion
distante. Les ressources et licences sont distribuées localement.

Lecture, versions précédentes, corrections avant/après, travail du jour,
trajectoire et résumé imprimable utilisent le même rendu et la même feuille
narrative. La pagination varie selon le navigateur ; le résumé conserve la
structure, pas une promesse d'identité pixel à pixel. Les événements simples
conservent leur échappement, même dans les vues communes aux bilans.
La fiche PDF native de personne ne contient toujours pas de note ou de projet.
Le backend PDF texte PWA n'a pas été transformé en moteur enrichi. Les CSV
statistiques ne deviennent pas un export de textes narratifs.

## Versions, droits et conflits

Les commentaires et projets conservent leurs versions immuables et jetons
existants. Les corrections de bilan conservent les documents avant/après et
incluent le document dans leur état signé. Notes et transmissions ont un état
signé incluant leur identité, projection et document ; une correction de mise
en forme seule est une modification. Le comparer-et-échanger SQL protège
l'écriture de ces contributions sur SQLite comme PostgreSQL, dans la même
transaction que la révision. Un ancien POST simple reste accepté pour une
contribution simple ; une contribution enrichie exige son état signé.
Les contrôles de droits restent dans les vues et les services. Une erreur ou
un conflit conserve le document soumis et le motif dans le formulaire.
Les écritures directes internes sans jeton restent des appels de service,
pas un nouveau point d'entrée web.

Les copies privées ZIP conservent les colonnes et historiques sans interprétation.
Les anciennes copies sont migrées après restauration ; une ancienne application
ne sait pas lire les nouvelles migrations et ne doit pas être réinstallée sur
la base enrichie. Pour revenir au code antérieur, utiliser la sauvegarde d'avant
migration dans un espace distinct, pas une migration inverse qui supprimerait
les documents. Le format ZIP commun et les politiques serveur ne changent pas.

## Ressources, fabrication et profils

Tiptap 3.32.0 / ProseMirror, dépendances exactes dans
`outils/editeur/package-lock.json`. Le cœur et les extensions retenues sont
libres ; les licences transitives figurent dans `static/editeur/LICENCES.txt`.
Aucun service Tiptap, CDN, React ou fonctionnalité commerciale n'est employé.

Le petit chargeur initialise à la demande, y compris après `fetch` de Form2
ou remplacement HTMX, et détruit les instances retirées. Il ne dépend pas
de scripts présents dans les fragments reçus. La synchronisation précède la
collecte du formulaire ; l'éditeur transmet aussi les événements de modification
au parcours métier. Les erreurs sont associées à la zone visible, les boutons
ont des libellés français et des états annoncés, les liens disposent d'un
formulaire clavier/tactile. Ctrl/Cmd+B, I, K et annuler/rétablir sont disponibles.

Node/npm ne servent qu'à reconstruire les fichiers embarqués, pas à installer
ou utiliser le produit. Depuis le dépôt :

```sh
npm ci --prefix outils/editeur
node outils/editeur/construire.mjs
```

Le script imprime taille brute, gzip et SHA-256 et régénère les licences.
Le bundle initial mesure environ 380 Ko / 122 Ko gzip. Il est chargé seulement
lorsqu'un champ enrichissable apparaît. Le serveur/bureau le distribue par les
statiques habituels ; le constructeur PWA copie le dossier static complet,
l'empreinte et le précache, sans modification de son protocole de stockage.

## Vérifications

```sh
python3 manage.py check
python3 manage.py test
python3 manage.py makemigrations --check --dry-run
node scripts/verifier-editeur-textes.cjs
# Après construction PWA :
node scripts/verifier-pwa-pyodide.mjs
node scripts/verifier-pwa.cjs
git diff --check
```

Le banc de composant exige Playwright/Chromium ; il ne les installe pas.
`PWA_PLAYWRIGHT` et `PWA_CHROMIUM` permettent d'utiliser un environnement existant.
Les CI PWA l'exécutent avec leurs dépendances habituelles, puis le parcours
métier écrit un vrai commentaire gras via Django/Pyodide. Les tests Django du
format et des services ne nécessitent pas Playwright.

Les tests automatisés couvrent l'échappement, les formats/URL refusés, les bornes,
les textes historiques, les corrections de format seul, conflits et rollback,
les restitutions et droits, la migration et une reprise ZIP. Le banc navigateur
couvre le collage, les liens au clavier, le remplacement de formulaire, la
validation, le repli simple sans JS et 360 px.
Restent à qualifier sur appareils : WebKitGTK/Linux, WebView2/Windows, Safari,
lecteurs d'écran et gestes tactiles réels. Un passage Chromium n'est pas une
qualification de ces environnements. Aucune installation ou nouvelle commande
de déploiement n'est imposée ; appliquer les migrations et collecter les
statiques selon le profil habituel.
