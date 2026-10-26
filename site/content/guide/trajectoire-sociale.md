---
title: "Lire une trajectoire d’accompagnement"
description: "Lire l’histoire personnelle et les faits de plusieurs prises en charge, sans score social."
fiche: true
categorie: "dossier"
publics: ["equipe"]
intentions: ["trajectoire", "évolution", "comparaison", "bilan", "histoire", "ancien suivi", "prise en charge"]
prerequis: "Droits de consultation du dossier ; déclarations personnelles, ressources, dettes, anciens suivis et prestations restent filtrés par leurs droits propres."
depart: "Dossier → Trajectoire d’accompagnement"
statut: "disponible"
---

1. Depuis un dossier personne ou ménage, ouvrir **Trajectoire d’accompagnement**. Depuis une prise en charge, le même lien présélectionne cette prise ; l’ancienne entrée depuis **Situation et parcours sociaux** reste disponible.
2. Choisir la personne, la période et, si utile, une prise en charge. Le filtre de prise sélectionne ses bénéficiaires et ses faits liés ; il ne limite pas l’histoire personnelle aux dates de cette prise.
3. Lire les situations aux deux bornes : logement, emploi/formation, ressources et dettes détaillées selon les droits. Cette lecture réutilise celle du dossier et de la situation à l’entrée.
4. Examiner les éléments datés et ouvrir **Source et historique** pour consulter leur provenance, leurs corrections et les actions disponibles.

**Quelle information fait référence ?** Une déclaration personnelle couvrant la date est affichée, même si un ancien suivi dit autre chose. Par exemple, Léa peut être déclarée **en formation** alors qu’un ancien suivi indique encore **sans emploi**. Cet ancien renseignement reste dans un dépliable avec sa source et sa prise en charge ; une divergence ne prouve pas une erreur.

Sans déclaration personnelle couvrant la date, **Non renseigné** est affiché. Les anciennes situations applicables restent accessibles séparément, sans devenir une déclaration personnelle consolidée. Les périodes des anciens suivis ne sont pas prolongées au-delà de leurs bornes ou de la clôture de leur prise en charge. Aucune donnée n’est convertie, rapprochée ou effacée.

Les ressources détaillées font référence pour leur synthèse à la date consultée. Une ancienne synthèse personnelle ou de suivi reste conservée séparément. Les dettes totales déclarées et les détails par créancier ne s’additionnent pas ; les montants inconnus, devises et périodicités restent distincts.

**Dates :** les bornes du filtre des éléments datés sont incluses ; les fins de périodes et de séjours sont exclues. Un fait commencé avant le filtre peut couvrir une borne sans être ajouté artificiellement à la chronologie. Sans début choisi, la comparaison part de la première date disponible dans cette sélection ; sans fin, elle va jusqu’à aujourd’hui. Une correction rectifie la lecture à la date d’effet d’origine : elle ne devient pas une évolution réelle à sa date d’enregistrement. Les journaux restent consultables dans les sources.

**Personne ou ménage :** un dossier personne suit ses prises en charge, même dans différents ménages. Un dossier ménage lit les faits liés à ce ménage ; les déclarations personnelles sont présentées pendant une appartenance datée ou une prise en charge dont la personne est explicitement bénéficiaire. Les autres dates sont signalées hors contexte. La sélection d’une personne exclut les bilans collectifs. Une appartenance ne rend jamais bénéficiaire d’une prestation.

**À vérifier :** un événement ou une sortie d’hébergement ne modifie pas automatiquement une situation déclarée. Une continuation individuelle d’un séjour ne devient pas une nouvelle admission. Les repas annulés restent signalés comme tels dans la chronologie et ne redeviennent pas des distributions dans les statistiques.

**Essai aux Passerelles :** chez Thomas, comparer deux dates dans la trajectoire puis ouvrir l’[histoire personnelle datée]({{< relref "/guide/dossier/situation/" >}}) et la rubrique [ressources et dettes]({{< relref "/guide/dossier/ressources/" >}}) à la même date. Vérifier la source et le filtre de prise avant de comparer. Le séjour peut être fini tandis que l’accompagnement continue ; aucun de ces écrans ne produit un score social.

Les [objectifs et orientations]({{< relref "/guide/dossier/objectifs/" >}}) conservent leur parcours propre. Les [rapports d’activité]({{< relref "/guide/statistiques/" >}}) gardent leurs populations, unités et dates de référence : cette trajectoire ne les remplace pas. Les documents financiers déjà émis restent inchangés.

## Choisir les deux situations comparées

Chaque borne propose **À l’entrée**, **Au dernier jour** (ou **Au dernier jour prévu**), **Aujourd’hui** et **À une date…**, selon la prise en charge sélectionnée. Les dates implicites sont calculées et grisées ; la date libre active le calendrier.

Par défaut, une prise en charge se compare de son entrée à son dernier jour connu, ou à aujourd’hui si sa fin n’est pas connue ou reste future. La fin est exclue dans le modèle : le dernier jour est la veille. Une fin prévue est nommée comme telle, sans devenir une sortie effective. Les dates futures restent exclues des faits consultables. Les dates libres conservent la possibilité d’examiner l’histoire personnelle au-delà de cette prise en charge. Sans JavaScript, choisir puis utiliser **Afficher l’évolution** ; pour une date libre, appliquer ce choix avant de remplir le calendrier.
