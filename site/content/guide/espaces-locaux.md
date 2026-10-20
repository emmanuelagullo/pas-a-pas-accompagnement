---
fiche = true
title: "Essayer et retrouver son espace habituel"
description: "Deux espaces distincts dans la PWA et les programmes récents."
liste_auto: false
---

Cette fiche concerne les versions proposant **Essayer avec Les Passerelles**.
[Choisir une version](../../essayer/). La démonstration partagée en ligne n’utilise
pas ce sélecteur d’espaces locaux.

## Ouvrir l’essai

Le bouton est accessible avant ou après la création de l’espace habituel.
La première ouverture génère Les Passerelles dans un espace distinct, avec les
comptes publics affichés. Les réouvertures retrouvent vos changements, sans reset.
Votre compte personnel de l’espace habituel n’est pas le compte public du jeu.

Dans la PWA, terminez les saisies et fermez les autres onglets avant de changer
d’espace. Dans le programme, confirmez la fermeture et la réouverture de la
fenêtre. En mode sans fenêtre depuis les sources, fermer puis relancer avec
ou sans `--essai` ; les [commandes techniques](../../conception/) donnent les détails.

## Revenir

Choisissez **Revenir à mon espace habituel**. Vous retrouvez son contenu et ses
comptes ; vos essais restent dans l’autre espace. Il n’y a ni fusion ni
synchronisation. Les premiers espaces qui avaient chargé le jeu dans l’espace
habituel restent conservés : ils ne sont ni déplacés ni effacés.

## Conserver les essais

Dans l’espace à conserver, ouvrir **Copies et restauration sur cet appareil**,
puis **Télécharger une sauvegarde**. Vérifiez que le ZIP est réellement conservé
hors de l’appareil. Il contient base, comptes et secrets sans chiffrement :
il doit rester privé, même s’il ne contient que des données fictives.

Restaurer une copie remplace seulement l’espace sélectionné après vérification
et confirmation. Les comptes du ZIP deviennent ceux de cet espace ; il faut se
reconnecter avec eux. L’état précédent ne remplace pas une copie hors appareil.
La PWA accepte au maximum 64 Mio, contenu décompressé compris. Les sauvegardes
Petits Pas sont refusées. Le PDF de consultation n’est pas une sauvegarde.

Les données de la PWA dépendent du navigateur, de son profil et de l’adresse du
site. Leur effacement peut supprimer les espaces. Le programme conserve ses
données hors de l’installation ; conservez aussi vos sauvegardes lors d’une mise à jour.
[Parcours détaillé de copie](../../premiers-pas/#conserver-un-essai-local).
