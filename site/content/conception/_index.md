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
| Modèle et périmètre métier | [V0-METIER.md](https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement/-/blob/main/V0-METIER.md) |
| Authentification et permissions | [AUTHENTIFICATION.md](https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement/-/blob/main/AUTHENTIFICATION.md) |
| Déploiements et publications | [DEPLOIEMENTS.md](https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement/-/blob/main/DEPLOIEMENTS.md) |
| Notes du code actuel | [CHANGELOG.md](https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement/-/blob/main/CHANGELOG.md) |

## Vérifier une version disponible

Dans l’application, relever sa version. Pour les programmes, vérifier les
[fichiers des releases publiques](https://github.com/emmanuelagullo/pas-a-pas-accompagnement/releases),
leur notice et leurs empreintes. Le site ne propose pas d’artefacts temporaires CI.
La PWA et le serveur ont leurs propres déploiements : publier Hugo ne les met pas à jour.

Les parcours des Passerelles et de changement d’espace sont présents dans le code
examiné (`32d71f1`). Le 20 octobre 2026, la page publique de la PWA ne proposait pas encore le
sélecteur Les Passerelles. Le serveur Render n’a pas répondu pendant le contrôle.
La présence du parcours dans les programmes publiés reste à vérifier. Le [guide d’essai](../essayer/)
indique les boutons à rechercher et les limites des anciennes versions.

Les sauvegardes restent privées ; aucune base, clé ou session n’est incorporée
aux pages de ce site.
