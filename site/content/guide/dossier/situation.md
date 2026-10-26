---
title: "Renseigner une situation sociale à la bonne date"
description: "Distinguer évolution réelle, information tardive et correction."
fiche: true
categorie: "dossier"
publics: ["equipe"]
intentions: ["situation", "rétroactivité", "logement", "emploi", "formation", "source"]
prerequis: "Un compte disposant des droits de lecture et de saisie de la rubrique concernée."
depart: "Dossier ou prise en charge → Situation sociale et projet"
statut: "disponible"
---

1. Choisir la vue : **Aujourd’hui** dans le dossier, **À l’entrée** par défaut dans la prise en charge, ou une date précise. Le sommaire **Dans cette page** garde les accès principaux visibles. **Afficher les rubriques** déplie les personnes et les rubriques sans masquer les informations de la page.
2. En présentation **Intégrale**, les informations consultables sont affichées directement, y compris les champs non renseignés. Choisir **Renseigner** ou **Modifier** ouvre le formulaire dans le même bloc lorsque JavaScript est disponible. Vérifier la date d’effet. La source particulière peut être indiquée si elle est connue, dans **Précisions facultatives**.
3. Une information ancienne peut être insérée rétroactivement dans sa chronologie. Vérifier les valeurs voisines avant confirmation.
4. **Modifier** une valeur héritée propose un changement à la date choisie. Pour une déclaration commencée à cette date, **Modifier** corrige ce renseignement. Si une information héritée était déjà fausse auparavant, choisir **Autres actions → Corriger l’information héritée**, au lieu de créer un changement fictif. La correction porte sur la période de cette déclaration et peut modifier sa restitution dans d’autres prises en charge.

Les valeurs héritées sont affichées en gris lisible. **Afficher les origines** révèle les déclarations dont elles proviennent. Dans une nouvelle déclaration de coordonnées, un téléphone modifié apparaît en texte principal et une adresse reprise de la déclaration précédente reste grise. Cela ne crée pas de lien permanent entre les champs de déclarations distinctes.

Une correction ouverte depuis ce bloc affiche sa période et les entrées de prises en charge de cette période. La confirmation explicite est réservée aux corrections antérieures, aux périodes déplacées et aux effets sur d’autres prises en charge. Si une modification de date change cette portée, le formulaire demande une nouvelle confirmation, sans enregistrer la première tentative.

## Retirer un changement erroné

Sur une déclaration commençant à la date consultée, **Autres actions → Retirer ce changement** propose de rétablir l’état antérieur continu, jusqu’au prochain changement connu. Sans état antérieur continu, la période devient **Non renseigné**. Le changement retiré et son journal sont conservés.

L’aperçu précise les valeurs et la période rétablies. Pour les coordonnées, la famille, l’identité déclarée et la situation administrative, le retrait porte sur la déclaration complète de cette rubrique. Une cessation réelle se renseigne comme un nouveau changement ; elle ne se traite pas par un retrait.

Les ressources détaillées, dettes, protections multiples et autres collections gardent leurs actions spécialisées. Leur annulation ne doit pas être confondue avec le retrait d’un changement dans une série à valeur unique.

Dans l’encadré **Vue et saisie**, le **Contexte de saisie (facultatif)** propose les contextes récents consultables du dossier. Il accompagne les opérations effectivement enregistrées, sans remplacer leurs sources ni leurs dates. Vide signifie non précisé. Il reste proposé pendant la séance, pour ce dossier et ce compte, le même jour. Une correction ordinaire ne nécessite pas de motif rédigé. Chaque rubrique s’enregistre séparément et conserve les autres valeurs proposées. Un conflit de version laisse la saisie visible : ne pas répéter aveuglément l’enregistrement.

**Aujourd’hui**, **À l’entrée** et **Au dernier jour** calculent la date affichée : elle est grisée et non modifiable. **À une date…** active le calendrier. Avec JavaScript, les réglages de vue s’appliquent au changement ; sans JavaScript, utiliser **Appliquer la vue**.

**Intégrale** affiche tous les champs, y compris non renseignés. **Synthèse** retient jusqu’à trois valeurs renseignées par déclaration et indique les informations supplémentaires. **Afficher les origines** révèle les dates et sources sous les valeurs, dans les deux présentations.

**Renseigner / Modifier** remplace les valeurs de la rubrique par ses champs. **Enregistrer** valide cette rubrique ; **Annuler** rétablit son affichage sans écrire. Les sources et précisions particulières sont facultatives et dépliables. Une erreur conserve la saisie et ouvre les précisions si elles sont concernées. Aucun enregistrement n’est déclenché en quittant un champ.

**Évolution** affiche la trajectoire dans le même cadre, à la demande. Sans JavaScript, les liens conduisent aux mêmes formulaires et à la trajectoire en pleine page.

**À vérifier :** la situation à l'entrée d'une prise en charge et celle d'aujourd'hui utilisent la même histoire personnelle. Une correction peut donc modifier la restitution d'une ancienne date ; celle-ci n'est pas un instantané figé.

Les informations sociales des anciens suivis restent conservées avec leur provenance. Une divergence appelle une vérification, pas une fusion automatique.

Pour comparer plusieurs dates, consulter la [trajectoire sociale]({{< relref "/guide/trajectoire-sociale/" >}}).

## Qualifier une évolution déclarée

**Itinéraire et antécédents → Évolutions personnelles déclarées** conserve un
domaine et un libellé structurés, avec date, source et corrections. Plusieurs
qualifications sont possibles. Elles se recherchent dans les rapports et ne
changent automatiquement ni logement, ni emploi, ni ressources, ni objectif.
Une qualification déclarée n'est pas un score social.

## Avant une saisie rétroactive

Choisir une date non future ; préciser la source si elle est connue. Un ajout antérieur à une déclaration déjà enregistrée exige les droits de modification ; une valeur à la même date se corrige explicitement. Une correction de date ne traverse pas une autre déclaration. Vérifier les deux périodes voisines après enregistrement.

Pour les ressources et dettes détaillées, partir de [leur rubrique propre]({{< relref "/guide/dossier/ressources/" >}}). Leur synthèse peut remplacer l’affichage de l’ancienne valeur globale, sans effacer cette dernière. La [trajectoire d’accompagnement]({{< relref "/guide/trajectoire-sociale/" >}}), accessible depuis le dossier, réutilise cette même lecture datée et conserve les anciennes informations séparément. En l’absence de déclaration personnelle couvrant la date, elle affiche « Non renseigné » sans promouvoir un ancien suivi en déclaration consolidée.
