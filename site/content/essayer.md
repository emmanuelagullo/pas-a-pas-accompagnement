---
title: "Essayer avec Les Passerelles"
description: "Le même scénario fictif, partagé en ligne ou conservé sur cet appareil."
---

Utilisez exclusivement des personnes et informations inventées.
[Découvrir le parcours en cinq minutes](../guide/decouvrir-passerelles/)
et [rencontrer l’équipe fictive](../roles/equipe/).

{{< parcours mode="service" titre="Dans la démonstration partagée" >}}
[Ouvrir la démonstration en ligne](https://pas-a-pas-accompagnement.onrender.com/).
Utilisez les accès affichés sur la page de connexion : tous les visiteurs voient
et peuvent modifier les mêmes essais. Les changements disparaissent à la
recréation du service. Le démarrage peut demander de patienter.

Le code de démarrage prépare **Les Passerelles**. Vérifiez que la version en ligne
propose **Découvrir le scénario fictif Les Passerelles** à l’accueil ; sa présence
effective sur cette publication reste à confirmer.
{{< /parcours >}}

{{< parcours mode="appareil" titre="Sur cet appareil" >}}
Dans les versions qui proposent **Essayer avec Les Passerelles**, ce bouton ouvre
un autre espace persistant. Votre espace habituel reste intact. Les essais
restent conservés lorsque vous revenez à cet espace.

### Dans votre navigateur

[Ouvrir l’application navigateur](https://pas-a-pas-accompagnement.gitlabpages.inria.fr/pas-a-pas-accompagnement-pwa/),
puis choisir **Essayer avec Les Passerelles**. Le chargement initial télécharge
les ressources. Si ce bouton est absent, cette publication n’intègre pas encore
ce parcours ; ne chargez pas de sauvegarde privée pour le remplacer.

### Avec le programme

[Consulter les versions publiées](https://github.com/emmanuelagullo/pas-a-pas-accompagnement/releases).
Choisissez les fichiers joints à la release et lisez sa notice : le ZIP des sources
n’est pas le programme. La présence du nouveau parcours dépend de la version.

- **Windows x64** : le setup `PasAPasAccompagnement-Setup-<version>-x64.exe`,
  s’il est joint, fournit un assistant et un raccourci. Sinon, extraire le ZIP
  portable puis lancer `PasAPasAccompagnement.exe`. WebView2 est nécessaire.
- **Linux x86-64** : extraire l’archive puis lancer `PasAPasAccompagnement`.
  La cible de construction est Ubuntu 24.04 avec GTK/WebKitGTK ; la compatibilité
  avec les autres distributions reste à vérifier.

Ouvrez **Essayer avec Les Passerelles**, puis confirmez le changement d’espace.
La fenêtre se ferme et se rouvre. [Comprendre le retour et la conservation des essais](../guide/espaces-locaux/).
{{< /parcours >}}

## Les accès du jeu neuf

{{< acces-demonstration >}}

## Ce que la publication permet réellement

Les parcours ci-dessus sont implémentés dans le code actuel. Une nouvelle page
web ne met pas à jour la démonstration, les programmes ou la PWA. Vérifiez la
version proposée dans l’application et les notes de la release. Les identifiants
ci-dessus s’appliquent au jeu neuf ; les comptes d’une copie restaurée peuvent
différer. [Détails et vérifications techniques](../conception/).

Pour préparer votre utilisation, revenez à [Démarrer](../demarrer/).
