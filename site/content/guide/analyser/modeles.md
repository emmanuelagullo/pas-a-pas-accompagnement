---
title: "Conserver et échanger un modèle de rapport"
description: "Réutiliser des critères sans enregistrer ni partager les résultats."
fiche: true
categorie: "analyser"
publics: ["equipe"]
intentions: ["modèle", "JSON", "rapport", "paramètres", "période relative"]
prerequis: "Droits de consultation et d’ajout des modèles, ainsi que les droits nécessaires au rapport qui sera recalculé."
depart: "Exploration statistique → modèles personnels"
statut: "disponible"
---

1. Construire un rapport et vérifier ses critères et sa période.
2. Enregistrer un modèle personnel avec un nom reconnaissable. Vérifier si sa période est fixe ou relative avant réutilisation.
3. Recalculer le rapport : les droits actuels sont contrôlés, et les résultats peuvent évoluer avec les données ou corrections.
4. Pour réutiliser les paramètres dans un autre espace, exporter le modèle JSON puis utiliser l'import. Les paramètres et droits sont revérifiés ; aucun accès supplémentaire n'est accordé.

**Résultat attendu :** le modèle reste personnel. Le fichier d’échange contient le nom du modèle et ses critères, sans lignes de résultats ni copie de dossiers. Des noms ou d’autres renseignements personnels saisis dans le nom du modèle, les valeurs des filtres ou les libellés de classes peuvent toutefois y figurer : relire le JSON avant de le transmettre et le conserver privé si nécessaire. Ce n'est ni une copie de base ni un PDF archivé du résultat.

**Essai :** Nadia dispose de modèles sur les appels et d'un modèle comparant nuitées totales, majeurs, mineurs et âges inconnus. Rémi et Camille ne voient pas automatiquement ses modèles.

Le fichier JSON échange les **modèles d’exploration** ; il ne convertit pas automatiquement les anciens modèles des rapports spécialisés. L’export et l’import requièrent les droits de consultation et d’ajout des modèles ; le fichier est limité à 64 Kio et chaque compte à 30 modèles, tous types confondus. Un modèle importé appartient au compte qui l’importe.
