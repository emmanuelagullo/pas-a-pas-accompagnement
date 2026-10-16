# PWA fictive — #SOC5a

Premier parcours : préparer son compte, créer une personne, fermer puis rouvrir
hors connexion et se reconnecter pour retrouver la fiche. Le mot de passe est
choisi à l'installation, aucun compte ni fichier de données n'est embarqué.
Aucun dossier réel : cette tranche ne propose **pas encore de sauvegarde ZIP
ni de restauration dans l'interface navigateur**. Ne rien y saisir à conserver.
Le stockage n'est pas chiffré et le navigateur peut l'effacer.

## Construire et essayer

Installer Python 3.12+, les dépendances de requirements.lock et le wheel
pas-communs 0.4.0 épinglé (à publier au préalable), puis :

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
un sous-répertoire. **Ne pas publier automatiquement ce prototype.**
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

Une mise à jour téléchargée attend l'action explicite du bouton de la coque,
hors requête en cours. L'installation complète de ses ressources précède son
activation. La qualification détaillée des versions anciennes, interruptions
et récupérations du CHRS reste #SOC5b ; ne pas considérer ce mécanisme minimal
comme une procédure d'exploitation ou de retour arrière validée.

## Bancs fictifs

Node 24, puis `npm ci --prefix pwa` et
`npx --prefix pwa playwright install --with-deps chromium` :

```sh
node scripts/verifier-pwa-pyodide.mjs
node scripts/verifier-pwa.cjs
PWA_BASE_PATH=/ node scripts/verifier-pwa.cjs
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
