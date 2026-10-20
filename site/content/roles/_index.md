---
title: "Comptes et accès"
description: "Les permissions actuelles du prototype, sans rôles CHRS supposés."
---

Les comptes de connexion sont distincts des personnes accompagnées.
La connexion seule ne donne pas le droit de consulter les fiches.

Dans le jeu neuf **Les Passerelles**, Nadia, Rémi et Camille disposent des mêmes
permissions explicites : consulter et créer des personnes, intervenir sur les
ménages et accompagnements, les repas, les séjours et les situations sociales.
Les vues contrôlent ces permissions ; aucun de ces comptes n’a de droit
implicite d’administration ou de suppression.

Leurs fonctions professionnelles sont narratives, sans restriction par service.
Tous voient le même espace fictif ; aucune isolation entre établissements
n’est implémentée. [Rencontrer l’équipe](equipe/).

Le premier compte créé dans un espace habituel neuf garde les droits de lecture
et création de personnes ; il ne reçoit pas automatiquement les droits métier
complets du jeu d’essai. Les anciens comptes conservent leurs permissions.
Le code technique utilise des permissions distinctes pour les actes métier :
[voir les sources et le cadrage](../conception/).

Les habilitations nécessaires aux dossiers réels restent à définir et qualifier.
