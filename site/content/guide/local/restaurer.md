---
title: "Vérifier puis restaurer une copie"
description: "Remplacer l’espace choisi sans fusionner les données de deux espaces."
fiche: true
categorie: "local"
publics: ["appareil"]
intentions: ["restaurer", "vérifier", "ZIP", "remplacement", "reconnexion"]
prerequis: "Une copie Pas à Pas compatible et une sauvegarde extérieure de l’espace à remplacer."
depart: "Copies et restauration sur cet appareil → choisir un ZIP"
statut: "disponible"
---

1. Sauvegarder d'abord l'espace actuel et vérifier le bandeau de l'espace qui sera remplacé.
2. Choisir une copie Pas à Pas puis lire le résultat de sa vérification. Une archive incompatible ou altérée doit être refusée ; ne pas forcer son ouverture.
3. Annuler si ce n'est pas la bonne copie. Sinon, confirmer explicitement le remplacement.
4. Dans le programme, appliquer le redémarrage demandé ; dans la PWA, laisser l'application se recharger. Se reconnecter avec un compte de la copie restaurée.
5. Vérifier un dossier, une ancienne version et un document joint avant de poursuivre la saisie.

**À vérifier :** il s'agit d'un remplacement, pas d'une fusion. Les comptes restaurés peuvent différer des comptes précédents. La PWA accepte au maximum 64 Mio, contenu décompressé compris ; les archives Petits Pas sont refusées.

L'état précédent conservé par le parcours ne remplace pas une sauvegarde hors appareil. Ne pas restaurer pour simplement [changer d'espace d'essai]({{< relref "/guide/espaces-locaux/" >}}).
