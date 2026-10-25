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

Depuis **Organismes partenaires → Importer ou exporter le paramétrage**, exporter
le JSON privé. Il contient les organismes et professionnels avec leurs fiches
datées, les liens entre répertoires, la hiérarchie des lieux, les types d'aide et
les versions de tarifs. Les comptes, droits, personnes accompagnées et dossiers
en sont exclus. Les anciens journaux restent dans la sauvegarde de l'espace
source ; l'import est attribué à son auteur actuel.

Dans l'autre espace, examiner le fichier, vérifier les entrées et les homonymes,
puis confirmer avec un motif. L'import crée de nouvelles entrées et ne fusionne
aucun homonyme. Une confirmation supplémentaire est nécessaire pour créer ces
doublons visibles. Un fichier déjà importé est refusé ; le reçu conserve les
correspondances. Une erreur annule l'ensemble de l'import. Limites : 1 Mo,
500 entrées et 2 000 définitions datées par fichier.

Les propositions de saisie et modèles d'exploration conservent leurs propres
échanges JSON, accessibles depuis cette page selon les droits. Ce paramétrage
ne constitue ni une sauvegarde complète ni une synchronisation entre espaces.
