# Qualification #SOC5b — 18 octobre 2026

Données fictives, profils Chromium éphémères, Linux / Chromium Headless Shell
151. Les essais n'utilisent ni compte ni donnée d'une instance réelle.

## Banc exécuté

`node scripts/verifier-pwa.cjs` sur un bundle `--test` :

- Racine HTTP localhost et préfixe `/chrs/` en HTTPS local avec certificat
  fictif ; ancien bundle #SOC5a pour le passage HTTPS vers #SOC5b.
- Premier compte, création, deuxième onglet refusé, reprise hors connexion
  et reconnexion ; aucune requête métier envoyée au serveur statique.
- ZIP exporté lisible par SQLite/Python et par les commandes natives de copie
  et sauvegarde ; retour du ZIP natif dans la PWA.
- ZIP étranger, altéré ou à migrations futures refusé ; annulation sans
  remplacement, confirmation avec reconnexion, ancien état exportable.
- Terminaison réelle du Worker avant/après activation ; seul l'état confirmé
  est retrouvé. Quota simulé avant activation, sans perte du précédent état.
- Version à ressource altérée refusée, ancienne version conservée ; nouvelle
  version valide en attente, bouton bloqué pendant vérification d'une copie,
  activation explicite, données et reconnexion hors ligne conservées.
- Base future refusée sans espace vide ; export brut sans migration et
  restauration explicite. Blob OPFS altéré refusé à l'ouverture/export courant,
  puis copie native restaurée explicitement.
- OPFS/IndexedDB réels : espaces de produits distincts, interruption,
  activation durable et secours.

Le banc réinitialise les compteurs fictifs via le protocole de test après ses
connexions répétées, pour ne pas dépasser la fenêtre #SOC4b. Les limites du
produit normal ne sont pas modifiées. Les injections restent inaccessibles
hors construction `--test` ; un bundle normal est construit et son parcours
compte/personne/reprise hors ligne est également exercé, sans `window.pwaTest`.
Aucun bundle `--test` ne doit être publié.

## Autres contrôles

60 tests Django CHRS, `check`, absence de nouvelle migration et contrôles
d'espaces Git. Le socle final est construit deux fois à octets identiques,
installé et testé ; les ressources JavaScript des bundles correspondent aux
octets du wheel. Les tests du moteur commun couvrent également la restauration
avec réécriture après corruption du blob ou du manifeste courant.
Les scripts Pyodide du socle et du CHRS complètent les bancs navigateur.

## Portée

#SOC5 est clos pour le moteur et ces scénarios Chromium/Linux. Les adaptateurs
restent propres aux produits. Le CHRS reste exclusivement fictif ; aucun
modèle social complet ni exploitation de dossiers réels validé. Pas de nouvelle
qualification Windows, Safari/iOS, Firefox, mobiles ou appareils terrain.
Les CI distantes devront confirmer les patches après publication du wheel.
