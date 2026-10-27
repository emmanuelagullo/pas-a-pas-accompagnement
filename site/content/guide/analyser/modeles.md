---
title: "Conserver et échanger un modèle de rapport"
description: "Réutiliser des critères sans enregistrer ni partager les résultats."
fiche: true
categorie: "analyser"
publics: ["equipe"]
intentions: ["modèle", "JSON", "rapport", "paramètres", "période relative"]
prerequis: "Droits de consultation et d’ajout des modèles, ainsi que les droits nécessaires au rapport qui sera recalculé."
depart: "Statistiques → Gérer mes modèles"
statut: "disponible"
---

1. Depuis **Créer un modèle**, partir de zéro ou reprendre une définition composable. Un modèle conserve la définition ; le rapport est le résultat recalculé.
2. Vérifier sa période et ses critères, puis choisir un nom et enregistrer.
3. Pour un modèle personnel déjà ouvert, choisir **Remplacer explicitement** ou **Enregistrer un second modèle**. Un formulaire devenu périmé ne remplace pas les paramètres actuels ; la saisie reste disponible.
4. **Gérer mes modèles** réunit ouverture, édition, renommage, duplication et suppression confirmée. Deux modèles peuvent porter le même nom ; leur numéro et date de création les distinguent. Supprimer un modèle retire ses paramètres, sans supprimer de dossier.
5. Pour échanger un modèle d’exploration entre espaces, exporter le JSON puis utiliser l’import. Les paramètres enregistrés des rapports spécialisés restent réutilisables dans cet espace, sans conversion automatique du format d’échange.

**Résultat attendu :** le modèle reste personnel. Le fichier d’échange contient le nom du modèle et ses critères, sans lignes de résultats ni copie de dossiers. Des noms ou d’autres renseignements personnels saisis dans le nom du modèle, les valeurs des filtres ou les libellés de classes peuvent toutefois y figurer : relire le JSON avant de le transmettre et le conserver privé si nécessaire. Ce n'est ni une copie de base ni un PDF archivé du résultat.

**Essai :** Nadia dispose de modèles sur les appels et d'un modèle comparant nuitées totales, majeurs, mineurs et âges inconnus. Rémi et Camille ne voient pas automatiquement ses modèles.

Le fichier JSON échange les **modèles d’exploration** ; il ne convertit pas automatiquement les anciens modèles des rapports spécialisés. L’export et l’import requièrent les droits de consultation et d’ajout des modèles ; le fichier est limité à 64 Kio et chaque compte à 30 modèles, tous types confondus. Un modèle importé appartient au compte qui l’importe.
