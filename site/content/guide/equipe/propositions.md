---
title: "Préparer des valeurs proposées à la saisie"
description: "Partager des libellés utiles sans remplir les dossiers automatiquement."
fiche: true
categorie: "equipe"
publics: ["gestion"]
intentions: ["préremplir", "proposition", "liste", "suggestion", "import"]
prerequis: "Les droits explicites de consultation et de modification des propositions partagées."
depart: "Partenaires → Propositions de saisie"
statut: "disponible"
---

1. Choisir le champ parmi ceux proposés par l'application.
2. Ajouter une valeur réutilisable et un motif. Garder les noms de personnes et données de dossiers hors des listes partagées.
3. Vérifier la suggestion dans le formulaire métier : la valeur reste librement modifiable et doit être confirmée par l'utilisateur.
4. Désactiver une proposition devenue inutile plutôt que réécrire les dossiers existants ; consulter son historique.
5. Pour un autre espace, exporter puis importer les propositions JSON. L'import ajoute les nouvelles valeurs et conserve les valeurs déjà présentes, y compris leur activation.

**À vérifier :** aucune suggestion n'est collectée automatiquement depuis les dossiers. Une proposition ne remplace ni source, ni date, ni confirmation. Le fichier JSON ne transporte ni personnes ni permissions.

Les organismes, professionnels, lieux et tarifs restent dans leurs répertoires propres. Il n'existe pas de bouton pour préremplir indistinctement tout un dossier.

## Transporter les répertoires et tarifs

Cet échange transporte les répertoires et tarifs, sans dossiers ni comptes. Les propositions de saisie gardent leur propre échange JSON.

[Ouvrir la fiche détaillée]({{< relref "/guide/equipe/parametrage/" >}}).

**Avant de partager le JSON :** il contient les valeurs proposées, actives ou inactives, telles qu’elles ont été saisies volontairement. Il n’extrait pas les dossiers, mais ne rend pas anonyme une valeur contenant un nom ou une information personnelle. Relire les valeurs avant l’envoi. L’import est limité à 1 Mio et 1 000 propositions ; un refus annule les ajouts de cet import.
