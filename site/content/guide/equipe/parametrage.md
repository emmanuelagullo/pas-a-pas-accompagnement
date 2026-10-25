---
title: "Transporter les répertoires et tarifs vers un autre espace"
description: "Examiner un JSON, vérifier les homonymes et conserver le reçu d’import."
fiche: true
categorie: "equipe"
publics: ["gestion"]
intentions: ["paramétrage", "transport", "import", "export", "JSON", "tarifs", "homonymes"]
prerequis: "Droits de consultation des répertoires et reçus ; droit d’export pour télécharger, droits de création requis dès l’examen d’un fichier à importer, puis à sa confirmation."
depart: "Organismes partenaires → Importer ou exporter le paramétrage"
statut: "disponible"
---

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

## Vérifier le résultat

Retrouver le reçu et les entrées créées dans les répertoires de destination. Vérifier les liens organisme/professionnel, la hiérarchie des lieux et les versions des tarifs. Les entrées préexistantes restent inchangées. Si l’aperçu est périmé, le refaire avant de confirmer ; en cas d’écriture non confirmée, consulter d’abord les reçus.

**Essai fictif :** exporter depuis Les Passerelles et préparer un aperçu dans un autre espace fictif. Annuler avant confirmation pour simplement examiner les homonymes. Le fichier reste privé : les coordonnées professionnelles exportées ne sont pas nécessairement publiques.

[Préparer les propositions de saisie]({{< relref "/guide/equipe/propositions/" >}}) et [sauvegarder un espace complet]({{< relref "/guide/local/sauvegarder/" >}}) répondent à d’autres besoins.
