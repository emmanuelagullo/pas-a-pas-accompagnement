---
title: "Documentation technique"
description: "Sources, contrats et état de publication."
---

Les sources publiques de `main` décrivent le code ; elles ne prouvent pas
qu’une instance ou une version téléchargeable l’utilise déjà.

| Sujet | Source du dépôt de référence |
| --- | --- |
| Installation et vérifications | [README](https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement/-/blob/main/README.md) |
| Jeu, comptes, espaces et limites des Passerelles | [DEMONSTRATION.md](https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement/-/blob/main/DEMONSTRATION.md) |
| Architecture et frontières du socle | [ARCHITECTURE.md](https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement/-/blob/main/ARCHITECTURE.md) |
| Définitions des rapports | [STATISTIQUES-METIER.md](https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement/-/blob/main/STATISTIQUES-METIER.md) |
| Authentification et permissions | [AUTHENTIFICATION.md](https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement/-/blob/main/AUTHENTIFICATION.md) |
| Déploiements et publications | [DEPLOIEMENTS.md](https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement/-/blob/main/DEPLOIEMENTS.md) |
| Notes du code actuel | [CHANGELOG.md](https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement/-/blob/main/CHANGELOG.md) |

## Vérifier une version disponible

Dans l’application, relever sa version. Pour les programmes, vérifier les
[fichiers des releases publiques](https://github.com/emmanuelagullo/pas-a-pas-accompagnement/releases),
leur notice et leurs empreintes. Le site ne propose pas d’artefacts temporaires CI.
La PWA et le serveur ont leurs propres déploiements : publier Hugo ne les met pas à jour.

Le [guide pratique]({{< relref "/guide/" >}}) décrit les usages présents dans le code,
y compris les lots de reprise Solenne et leur consolidation. Les documents V0
restent des jalons historiques, sans limiter le périmètre actuel.
Les contrôles locaux du site vérifient construction, liens, ancres et structure HTML ;
ils ne certifient ni la publication de la dernière application ni son affichage
dans chaque navigateur. Pour vérifier un essai, relever sa version, sa date de
génération et s'il a été modifié depuis sa création.

Les sauvegardes restent privées ; aucune base, clé ou session n’est incorporée
aux pages de ce site.
