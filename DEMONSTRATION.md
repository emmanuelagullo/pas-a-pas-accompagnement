# Les Passerelles — démonstration métier fictive

Jeu mono-espace, sans table d’établissement : « Les Passerelles » est un cadre
narratif, pas un cloisonnement entre CHRS. Données fictives exclusivement.
Le générateur métier est dans `personnes/demonstration.py` ; aucune base,
clé, session ou sauvegarde privée n’est distribuée avec le programme ou la PWA.

| Personnage | Parcours |
| --- | --- |
| Alex | Accompagnement ouvert sans hébergement ; déjeuner accordé, deux distributions passées. |
| Samira, Lina, Adam | Trois fiches, trois bénéficiaires explicites du suivi, des repas et du séjour ; unité interne puis lieu partenaire ; absence close de deux jours, séjour ouvert. |
| Thomas | Séjour terminé, accompagnement ouvert ; logement devenu autonome, formation, ressources déclarées, événement et bilan. |

Nadia illustre l’accompagnement social, Rémi l’accueil/hébergement, Camille la
restauration. Sur le serveur public, les trois comptes `nadia`, `remi`, `camille`
et l’accès historique `essai` ont les mêmes droits explicites CHRS1–4 et la
création de personnes, sans suppression ni administration. Ce ne sont pas des
rôles ni des habilitations par service. Les écritures initiales sont attribuées
à leur acteur narratif via les services métier et leurs journaux.
En local, tout est attribué au compte choisi par l’utilisateur ; aucun compte
à mot de passe public n’y est ajouté. Les enfants sont présentés dans le scénario,
sans âge enregistré, filiation ni représentation légale déduite du ménage.

## Essayer

- Serveur jetable : le démarrage existant `bash start-render.sh` prépare le jeu.
  Connexion avec `nadia`, `remi`, `camille` ou `essai`, mot de passe public
  `Demonstration-fictive-2026!`. Depuis l’accueil, ouvrir **Découvrir le scénario
  fictif Les Passerelles**. Les essais des visiteurs sont partagés. Ne pas
  utiliser ce profil pour un espace persistant.
- PWA ou programme Linux/Windows : au tout premier démarrage d’un espace vide,
  choisir ses identifiants privés et cocher **Charger Les Passerelles,
  démonstration métier fictive**. La case n’est pas cochée par défaut ; elle
  annonce l’attribution des droits CHRS1–4. La page de découverte s’ouvre ensuite.
  Sans cette case, le parcours antérieur de fiches de personnes est conservé.
- Depuis les sources, pour essayer le même premier démarrage local sans fenêtre :
  `python scripts/lancer-local.py --paquet /chemin/absolu/neuf --sans-fenetre`.
  Les dépendances du programme restent celles de `requirements-bureau.txt`.

Le parcours `/decouverte/` suit : ménage → accord et réalisation → distribution
d’un déjeuner pour Alex aujourd’hui → affectations et absence de Samira →
situation datée et historique de Thomas. Un bilan ou un événement fictif peut
ensuite être ajouté. Les vues continuent à contrôler leurs permissions ; le guide
n’accorde aucun droit et ne charge aucune donnée.

## Dates, conservation et copies

J est la date civile locale de génération. Le suivi commence à J−60 ; la famille
est admise à J−39, change de lieu à J−15, est absente de J−7 inclus à J−5 exclu ;
Thomas sort à J−10. Les accords d’Alex et de la famille restent ouverts. Le repas
d’Alex à J est volontairement absent ; sur le serveur partagé il peut avoir été
saisi par un autre visiteur. Les distributions sont datées et effectives, sans
prétendre mesurer une consommation physique.

Le contenu et les décalages sont reproductibles. UUID, horodatages techniques,
clés et mots de passe hachés restent propres à chaque espace. Les dates sont
fixées à la génération : aucune redatation à l’ouverture ou à la restauration,
aucune date simulée dans les règles métier. Un espace conservé reste utilisable,
avec son historique réel d’essai et ses périodes ouvertes.

La préparation serveur refuse comptes ou objets métier existants. L’installation
locale n’est disponible que sans compte ni objet métier ; la création du compte,
les droits et le jeu sont dans la même transaction. Pas de commande de reset,
pas de nouvelle restauration. Le redémarrage du serveur jetable utilise toujours
un dossier neuf, selon le contrat existant. Pour reprendre un essai local, garder
son espace, ou restaurer explicitement une copie avec les outils déjà présents.
Sauvegarder avant tout remplacement ; le ZIP complet contient comptes et secrets
et reste privé. Ne pas le publier comme jeu distribuable.

## Qualification

```sh
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
python scripts/verifier-demonstration.py
python scripts/exercer-deploiement.py --help
git diff --check
```

Le banc `verifier-demonstration.py` génère le jeu en espace temporaire, sauvegarde,
vérifie, restaure par les commandes existantes, compare les objets, identités,
permissions et relations, et vérifie la reconnexion. Les bancs PWA existants
restent requis pour qualifier Pyodide/OPFS (racine et préfixe), ainsi que les
constructions et essais des programmes Linux/Windows. CPython ne qualifie pas
WebView2, WebKit ni le navigateur. Aucun changement de pas-communs, de dépendance,
de format ZIP ou de commande d’exploitation persistante n’est nécessaire.

### Vérifications de cette livraison — 20 octobre 2026

- Python 3.12, Django 5.2.18 et 6.1.2, wheel épinglé pas-communs 0.9.0 :
  103 tests exécutés par version, dont 3 ignorés (qualification PostgreSQL distincte).
- Contrôles Django, absence de migration nouvelle et diff sans erreur ;
  sauvegarde/restauration native complète du jeu, permissions et reconnexion.
- Serveur jetable : banc HTTP réel, statiques, refus de reset et deux démarrages.
- Construction PWA et vrais runtimes Pyodide/Python 3.14.2 : premier compte avec
  jeu facultatif, découverte, droits et transfert du jeu vers le natif ; banc
  existant d’échanges PWA ↔ natif, relations CHRS1–4 et ancienne copie migrée.
- À confirmer en CI : parcours Chromium racine/préfixe (banc étendu au chargement
  du jeu et à sa reprise hors ligne), constructions Linux/Windows et Hugo.
  Chromium n’a pas pu être installé ici : archive téléchargée incomplète.
  Hugo et les moteurs graphiques des programmes ne sont pas présents ici.
  L’essai interactif sur les postes cibles reste nécessaire.
