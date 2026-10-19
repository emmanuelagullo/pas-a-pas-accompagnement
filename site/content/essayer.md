---
title: Essayer le prototype
---

Utilisez uniquement des personnes et informations inventées.

## Découvrir sans installation

[Ouvrir la démonstration partagée](https://pas-a-pas-accompagnement.onrender.com/).
La page de connexion indique les identifiants publics. Les essais sont visibles
par les autres visiteurs et disparaissent au redémarrage du service. Cette
version n’est pas un espace de travail privé.

## Créer un espace dans le navigateur

[Ouvrir l’application navigateur](https://pas-a-pas-accompagnement.gitlabpages.inria.fr/pas-a-pas-accompagnement-pwa/).
Le premier chargement installe les ressources nécessaires. Créez votre propre
compte : les identifiants publics de la démonstration ne s’y appliquent pas.

Le parcours hors ligne est vérifié par des essais automatisés sous
Chromium/Linux. Les autres navigateurs restent à qualifier. Les données sont
liées au navigateur, à son profil et à l’adresse de l’application : effacer les
données du site peut supprimer l’espace. Ce n’est pas une synchronisation entre
appareils. Téléchargez une sauvegarde et conservez-la hors de l’appareil.

## Télécharger un programme

[Consulter les versions publiées](https://github.com/emmanuelagullo/pas-a-pas-accompagnement/releases).
Téléchargez les fichiers joints à la version choisie, avec sa notice et ses
empreintes ; ne prenez pas le ZIP des sources pour un programme installé.

- **Windows x64** : utiliser le setup `PasAPasAccompagnement-Setup-<version>-x64.exe`
  lorsqu’il est joint à la release. Il propose un assistant en français et un
  raccourci ; la désinstallation conserve les données. Le ZIP portable reste
  une alternative : extraire puis lancer `PasAPasAccompagnement.exe`.
  WebView2 doit être disponible.
- **Linux** : l’archive cible Ubuntu 24.04 x86-64 avec GTK/WebKitGTK.
  Extraire puis lancer `PasAPasAccompagnement`. La compatibilité avec toutes
  les distributions n’est pas garantie.

Les fichiers disponibles dépendent des releases effectivement publiées.
Le premier démarrage demande de créer un compte local. Gardez le dossier de
données et vos sauvegardes lors d’une mise à jour du programme.
