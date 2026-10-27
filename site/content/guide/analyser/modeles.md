---
title: "Conserver et échanger un modèle de rapport"
description: "Réutiliser des critères sans enregistrer ni partager les résultats."
fiche: true
categorie: "analyser"
publics: ["equipe"]
intentions: ["modèle", "JSON", "rapport", "paramètres", "période relative"]
prerequis: "Droits de consultation et d’ajout des modèles, ainsi que les droits nécessaires au rapport qui sera recalculé."
depart: "Statistiques → Gérer les modèles et leurs personnalisations"
statut: "disponible"
---

Un **modèle** définit le calcul et la présentation. Une **personnalisation**
retrouve les choix habituels d’application. Le **rapport** est le résultat recalculé.

1. À l’entrée Statistiques, ouvrir directement un **accès habituel** ou un modèle proposé.
2. Ajuster si besoin la période et les critères, puis consulter les résultats.
3. Après les résultats, **Conserver ces réglages…** enregistre une personnalisation. Pour une nouvelle composition libre, le choix proposé est un modèle.
4. Choisir des dates fixes ou une règle relative affichée. La proposition reste modifiable ; les règles relatives seront recalculées à chaque ouverture.
5. Dans **Conserver aussi une définition de modèle**, choisir un modèle seul ou un modèle avec sa personnalisation. Une modification du calcul ou du classement d’un modèle existant demande de conserver une nouvelle définition, plutôt que changer discrètement son sens.
6. **Gérer les modèles et leurs personnalisations** réunit création, ouverture, renommage, description, duplication et suppression. Remplacer reste explicite ; un formulaire périmé conserve la saisie et refuse l’écrasement.

Une personnalisation liée conserve les paramètres de l’enregistrement. Si le
modèle source évolue, la gestion le signale ; les rapports habituels gardent leur
définition précédente. Supprimer le modèle source ne supprime pas les réglages de
sa personnalisation. Les anciennes définitions restent des modèles autonomes.

Le JSON échange les définitions d’exploration et peut conserver leur description.
La filiation privée vers un autre enregistrement n’est pas transférée.

**Résultat attendu :** le modèle reste personnel. Le fichier d’échange contient le nom du modèle et ses critères, sans lignes de résultats ni copie de dossiers. Des noms ou d’autres renseignements personnels saisis dans le nom du modèle, les valeurs des filtres ou les libellés de classes peuvent toutefois y figurer : relire le JSON avant de le transmettre et le conserver privé si nécessaire. Ce n'est ni une copie de base ni un PDF archivé du résultat.

**Essai :** Nadia dispose de modèles sur les appels et d'un modèle comparant nuitées totales, majeurs, mineurs et âges inconnus. Rémi et Camille ne voient pas automatiquement ses modèles.

Le fichier JSON échange les **modèles d’exploration** ; il ne convertit pas automatiquement les anciens modèles des rapports spécialisés. L’export et l’import requièrent les droits de consultation et d’ajout des modèles ; le fichier est limité à 64 Kio et chaque compte à 30 modèles, tous types confondus. Un modèle importé appartient au compte qui l’importe.
