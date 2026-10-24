# PWA fictive — fonctionnement actuel et historique SOC5

Premier parcours : préparer son compte, créer une personne, fermer puis rouvrir
hors connexion et se reconnecter pour retrouver la fiche. Le mot de passe est
choisi à l'installation, aucun compte ni fichier de données n'est embarqué.
Aucun dossier réel : ce prototype n'est pas un dossier social exploitable.
#SOC5b ajoute les copies ZIP et leur restauration explicite. Le stockage et les
ZIP ne sont pas chiffrés ; le navigateur peut effacer ses données locales.

## Construire et essayer

Installer les dépendances de requirements.lock avec **Python constructeur
3.12+** ; le wheel adopté vient de requirements-communs.txt (0.8.0 publié à
l'issue d'AUD). Sous Guix, les dépendances peuvent venir du profil ; pip reste
utilisé explicitement par le constructeur pour remplir les caches de wheels.

Le constructeur affiche la version exacte de son Python et son exécutable.
Le **Python embarqué dans Pyodide** est différent : Python 3.14.2, Pyodide
314.0.7, ABI 2026_0. Les dépendances pures verrouillées et les wheels WASM
sont qualifiés dans ce runtime, pas déduits de la version du constructeur.
GitLab utilise python:3.12-slim-trixie (Node fourni par Trixie) ; GitHub choisit
Python 3.12 et Node 24. Les versions effectives sont affichées dans les logs.

Construire, puis servir le résultat :

```sh
python scripts/construire-pwa.py
python -m http.server 8001 --directory dist/pwa --bind 127.0.0.1
```

Ouvrir http://127.0.0.1:8001/ et attendre l'apparition de l'installation.
Le téléchargement initial nécessite Internet lors de la construction. Une fois
les ressources mises en cache, le navigateur fonctionne sans serveur Django.
Le profil Python serveur/bureau n'est pas modifié. Le bundle est autonome.

La sortie doit être vide pour chaque nouvelle construction. On peut choisir
`--sortie /chemin/neuf`, `--runtime /chemin/cache-runtime` et
`--wheels /chemin/cache-wheels`. Les caches doivent être hors sortie ; le wheel
commun y est contrôlé avec l'empreinte de requirements-communs.txt.
Ces options permettent de tester le candidat avant publication sans changer
les dépendances du dépôt. Le fichier de verrou Pyodide reste contrôlé et les
wheels Python sont épinglés dans requirements.lock.

Hors localhost, il faut HTTPS et les bons types MIME (.mjs JavaScript,
.wasm application/wasm). Un hébergement statique suffit, à la racine ou dans
un sous-répertoire. La publication suit les contrôles et déclencheurs décrits dans
[../DEPLOIEMENTS.md](../DEPLOIEMENTS.md) ; les tags qualifiés sont automatiques,
main reste manuel. Le caractère fictif reste obligatoire.
Conserver une adresse et un chemin stables pendant les essais ; leur changement
ouvre un autre espace et ne déplace aucune donnée.

## Fonctionnement et limites

Le Service Worker conserve les ressources statiques après contrôle SHA-256.
Les requêtes `/app/` vont au Worker Python, qui exécute les vraies vues Django.
Les cookies sont virtuels en mémoire, sans session exposée au navigateur ;
rouvrir impose une reconnexion. CSRF et permissions restent actifs. Le premier
compte dispose seulement des droits de consultation/création des personnes.
Le TOTP n'est pas activable en PWA, comme sur bureau ; un compte déjà protégé
n'est pas déprotégé par ce profil.

SQLite et la clé sont copiés en OPFS via le moteur commun ; une saisie n'est
annoncée terminée qu'après activation du manifeste IndexedDB. Un Web Lock
interdit deux onglets propriétaires du même espace. Une erreur persistante
arrête le moteur : fermer puis rouvrir, sans rejouer aveuglément une saisie.
Une corruption ou migration inconnue refuse l'ouverture, sans base vide.

| Ressource | Identité CHRS |
| --- | --- |
| Manifeste | Pas à Pas — Accompagnement, identifiant relatif `./` |
| IndexedDB | `pas-accompagnement-pwa-v1` + suffixe du chemin |
| OPFS | `pas-accompagnement-pwa` + suffixe du chemin |
| Verrou | `pas-accompagnement-pwa-owner-` + chemin |
| Cache | `pas-accompagnement-pwa-` + chemin + version |
| Base | `accompagnement.sqlite3` |

Aucun compte, secret, cache ni stockage Petits Pas n'est repris. Un même
navigateur peut conserver les deux espaces. Une origine partagée ne les isole
pas contre du code malveillant : choisir des origines distinctes pour une future
exploitation. Pas de synchronisation avec le serveur ou le programme local.
Les uploads sont plafonnés à 1 Mio dans ce prototype sans documents métier.

## Copies et restauration (#SOC5b)

Ouvrir **Copies et restauration sur cet appareil**. Ces outils techniques
concernent tout l'espace de ce profil navigateur, comptes et clé compris ; ils
ne sont pas un nouveau rôle web. Ils sont réservés au propriétaire de cet
appareil fictif, comme les commandes locales de maintenance.

- **Télécharger une sauvegarde** lit l'état confirmé OPFS, dans un Worker
  séparé, et produit le même ZIP CHRS que la commande `sauvegarder_paquet`.
  Vérifier le téléchargement et conserver une copie privée hors appareil.
- Choisir un ZIP dans **Vérifier une copie à restaurer**. Une copie séparée
  vérifie identité du produit, chemins, empreintes, intégrité SQLite, relations
  et migrations. Aucun fichier courant ni pointeur OPFS n'est modifié. Le
  résumé affiche les nombres de personnes et comptes, et la date de la copie.
- **Annuler** détruit cette préparation. **Remplacer cet espace par la copie
  vérifiée** ferme le moteur courant, active la copie durablement, puis recharge
  l'application. Les sessions et compteurs sont retirés de la copie ; une
  nouvelle connexion avec ses propres comptes est exigée. Les facteurs TOTP
  existants ne sont pas supprimés et restent bloquants dans le profil local.
- **Télécharger l'état avant remplacement** exporte le checkpoint retenu avant
  migration de version ou restauration. Il ne remplace rien automatiquement.
  S'il n'existe pas ou est endommagé, l'export est refusé explicitement.

La copie native et la copie navigateur sont interchangeables pour ce prototype, médias compris. Limites : ZIP de 64 Mio, base de 64 Mio et clé de 64 Kio maximum,
5 000 entrées au plus, manifeste compris, et contenu décompressé de 64 Mio maximum.
Les médias sont conservés comme fichiers opaques, sans nouveau parcours métier.
Les ZIP scolaires, altérés, incomplets ou avec migrations inconnues sont refusés. La vérification
et les copies sont bornées mais utilisent de la mémoire WASM ; cela ne reprend
pas les transferts de médias volumineux de Petits Pas.

Une corruption ou une migration future n'ouvre jamais une base vide : la coque
garde les outils de copie et restauration disponibles. L'export courant lit
l'état enregistré sans appliquer de migration ; un état corrompu est refusé.
Restaurer un ZIP valide reste une action explicite. Après confirmation, les
blobs de la copie sont réécrits pour éviter de réutiliser des octets altérés
malgré l'empreinte annoncée par l'ancien pointeur. Un état de secours stocké
sur le même appareil ne remplace jamais le ZIP externe.

## Mises à jour

Une nouvelle version ne s'installe qu'après contrôle de toutes ses ressources.
Une ressource absente ou altérée laisse l'ancienne version intacte. Le bouton
**Installer la mise à jour** exige une confirmation explicite et reste bloqué
pendant une requête, une vérification ou une restauration. L'ancien Worker est
arrêté avant activation du Service Worker ; la réouverture impose une connexion.
L'initialisation migre la copie en mémoire, puis confirme l'état en OPFS avec
checkpoint pré-version. En cas d'échec avant activation, l'ancien état reste
confirmé ; après activation, le nouvel état reste confirmé. Pas de retour
silencieux au code ancien ni de remise à zéro. Des caches d'anciennes versions
peuvent rester sur le profil ; le nettoyage et le quota relèvent du navigateur.

## Bancs fictifs

Node 24, puis `npm ci --prefix pwa` et
`npx --prefix pwa playwright install --with-deps chromium` :

```sh
node scripts/verifier-pwa-pyodide.mjs
# Après la construction normale ci-dessus, sortie neuve de tests :
python scripts/construire-pwa.py --test --sortie dist/pwa-tests --runtime dist/pwa/runtime --wheels dist/pwa/wheels
PWA_BUNDLE=dist/pwa-tests PWA_TEST_HTTPS=oui node scripts/verifier-pwa.cjs
PWA_BUNDLE=dist/pwa-tests PWA_BASE_PATH=/ node scripts/verifier-pwa.cjs
# Contrôle de la construction normale, protocole de test désactivé :
PWA_PRODUCTION=oui node scripts/verifier-pwa.cjs
```

Le premier banc initialise deux runtimes Pyodide et vérifie copie SQLite,
reconnexion et refus d'une migration inconnue. Le second exerce un Chromium
éphémère : installation, création, refus du second onglet et relance hors
connexion. Il exerce aussi OPFS/IndexedDB réels : profils séparés, arrêt du
Worker avant activation, conservation de l’état confirmé et du secours.
`PWA_CHROMIUM` permet de choisir un Chromium installé.
Les tests utilisent uniquement des identités fictives et des profils temporaires.
La CI GitHub exécute ces bancs sans publication. La recette GitLab serveur et
les programmes locaux restent indépendants ; mutualiser les CI relève de #SOC6.
Firefox, Safari/iOS, installation Windows et appareils réels restent à qualifier.

Le banc #SOC5b exerce aussi l'aller-retour des commandes natives, les refus
croisés/empreintes/migrations futures, l'annulation, la restauration et le
secours, la terminaison du vrai Worker avant/après commit, le quota simulé,
l'échec d'installation d'une version altérée, l'activation hors restauration,
la reconnexion hors ligne et la réparation explicite depuis un ZIP après
corruption. `PWA_OLD_BUNDLE` sélectionne une distribution #SOC5a pour tester
son adoption effective de #SOC5b. Les injections sont gardées par une constante
compilée fausse hors `--test`, sans paramètre URL pour les activer.

#SOC5 est clos pour le moteur et ces bancs Chromium/Linux. Les Workers et
coques restent propres aux produits ; les documents et médias n'ont pas de
correspondance métier à imposer. La qualification d'appareils, des autres
navigateurs et l'exploitation de données réelles ne sont pas validées ici.


## Publication explicite (#SOC6c)

Voir ../DEPLOIEMENTS.md pour la construction/qualification GitLab, la promotion
du bundle normal vers le projet Pages dédié. La configuration est incluse depuis
main et le préparateur provient du commit source exact, comme pour Petits Pas. Les identités commit/tag/version sont dans config.json ; les bundles
test restent impropres à la publication. La nouvelle page telecharger.html
renvoie aux releases publiques des programmes et rappelle les limites fictives.

## Harmonisation des copies (candidat socle 0.9.0)

Le banc Pyodide exerce PWA → commande native → PWA avec un compte, une personne,
un ménage, un accompagnement, des relations CHRS1–4 et un média fictif. Le banc
Chromium vérifie aussi ces médias et relations dans les copies exportées après
restauration et secours. `scripts/jeu-technique-copies.py` est une sonde des bancs,
jamais embarquée ni distribuée comme démonstration. Aucun rôle supplémentaire.

## Essayer Établissement Les Passerelles dans un espace distinct

**Essayer avec Établissement Les Passerelles** ouvre un stockage d’essai distinct, avec les
comptes publics du jeu fictif. **Revenir à mon espace habituel** retrouve les
données habituelles sans restauration. Vos essais restent conservés pour la
prochaine ouverture. Le lien est accessible avant la création d’un compte.
Voir [le parcours et la compatibilité du premier patch](../DEMONSTRATION.md).
Les Workers de copie et de restauration sélectionnent le même espace que la
coque ; le verrou d’ouverture reste commun aux deux espaces. Aucun effacement
ni nouveau format de copie. Effacer les données du site peut supprimer les deux.
