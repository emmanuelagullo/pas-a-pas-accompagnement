---
title: "Le projet"
description: "Un parcours compact pour des usages d’accueil et d’accompagnement social étendus."
---

Pas à Pas — Accompagnement est une application libre Django/HTMX destinée
notamment aux équipes de CHRS. Le parcours **Recherche → Dossier → Prise en charge**
regroupe l'information utile sans imposer de remplir tout un dossier avant d'accueillir.

## Les usages présents dans le code

- **Accueillir** : rechercher ou créer explicitement une personne ou un ménage,
  enregistrer une demande, suivre sa décision et ouvrir une prise en charge.
- **Accompagner** : identité et relations, coordonnées, situations sociales datées,
  ressources, dettes, administration, protections, besoins d'accueil et antécédents ;
  objectifs et orientations suivis entre plusieurs prises en charge.
- **Réaliser des prestations** : hébergement, lieux, absences et sorties ; repas,
  transports, aides alimentaires et accueil de jour. Les accords sont distincts des faits.
- **Financer et documenter** : tarifs datés, coûts par phase, financeurs,
  documents émis numérotés et fichiers privés joints avec versions.
- **Assurer la continuité** : appels 115 éventuellement anonymes, notes,
  cahier de liaison et actions de relève explicitement créées.
- **Relire l'activité** : recherches structurées, rapports, croisements,
  impressions et exports, avec critères et unités explicites.

Le [guide pratique]({{< relref "/guide/" >}}) décrit les tâches et leurs prérequis.
L'[Établissement Les Passerelles]({{< relref "/guide/decouvrir-passerelles/" >}})
permet une visite courte puis des exercices complets. La publication du site
ne met pas automatiquement à jour les programmes, la PWA ou le service de démonstration.

## Ce qui reste à qualifier

Le prototype reste réservé aux données fictives. Les permissions sont explicites ;
il n'existe pas de cloisonnement qualifié entre établissements ou métiers.
Un calcul de financement n'est pas un encaissement ; une déclaration de besoin
n'est pas un dossier médical. Les parcours décrits ne promettent pas de synchronisation
avec un autre système d'information.

La reprise des usages historiques de Solenne progresse par lots. Elle ne constitue
pas encore une certification exhaustive de tous ses calculs ou documents anciens.
Les sources et arbitrages sont suivis séparément de ce guide d'utilisation.

## Des outils partagés avec Petits Pas

[Petits Pas](https://petits-pas.gitlabpages.inria.fr/petits-pas/) s'adresse aux
équipes de maternelle. Les métiers restent distincts ; Pas à Pas reprend des
mécanismes éprouvés et une organisation du guide par tâches, sans transposer
les rôles ou modèles scolaires dans l'accompagnement social.

[Pas communs](https://gitlab.inria.fr/pas-communs/pas-communs) fournit des
mécanismes techniques et le thème des sites publics. Chaque application garde
ses modèles, autorisations, contenus, couleurs et données.

[Contribuer]({{< relref "/contribuer/" >}}) · [Démarrer]({{< relref "/demarrer/" >}}).
