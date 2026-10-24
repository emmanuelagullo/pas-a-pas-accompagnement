---
categories_guide: [analyser, quotidien]
mots_cles_guide: ["csv", "rapport", "nuitées"]
title: "Lire les statistiques d’activité"
description: "Choisir une période, comprendre les indicateurs et exporter un bilan."
fiche: true
---

Depuis la navigation, ouvrir **Statistiques** avec un compte autorisé. Choisir
une période rapide ou renseigner un début **inclus** et une fin **exclue**.
Sélectionner ensuite le rapport : **Synthèse**, **Hébergement**, **Repas** ou
**Évolution mensuelle**, **Explorer les repas par mois et service** ou **Explorer les nuitées par mois et lieu**. Les explorations proposent trois regroupements (mois et catégorie, catégorie seule, mois seul) et un filtre de service ou de lieu. Le bouton **Exporter ce rapport (CSV)** télécharge les
valeurs du rapport affiché, sans identité nominative.

## Lire les chiffres sans les confondre

- **Admissions et sorties** comptent les débuts et fins de séjours dans la
  période, pas les personnes distinctes.
- **Nuitées théoriques** additionnent les nuits de séjour par bénéficiaire ;
  des séjours simultanés peuvent compter plusieurs fois la même nuit.
- **Nuits distinctes** évitent ce doublon pour une même personne.
- **Nuits hors absences déclarées** retirent les absences enregistrées ; elles
  ne constituent **pas** une mesure de présence physique constatée.
- **Repas distribués** reposent sur les distributions enregistrées non
  annulées, et non sur les seuls accords.

Les effectifs de personnes distinctes ne s'additionnent pas d'un mois à
l'autre. Une comparaison entre périodes juxtapose des activités de même durée,
mais ne mesure pas à elle seule une évolution des parcours sociaux.

## Essayer avec Établissement Les Passerelles

Dans un **jeu fictif fraîchement généré**, sélectionner la période allant de
**J−60 à J+1** (J est la date de création du jeu, et non nécessairement la date
du jour de consultation). Le bilan de référence comprend **3 ménages**, **4
personnes avec séjour**, **2 séjours**, **2 admissions**, **1 sortie**, **159
nuitées théoriques**, **159 nuits distinctes**, **153 nuits hors absences
déclarées** et **5 repas distribués**. Les mois partiels et les exports doivent
restituer des totaux cohérents. Dans une démonstration partagée ou déjà modifiée,
les valeurs peuvent différer.

Consulter le [parcours Établissement Les Passerelles](../decouvrir-passerelles/) puis le
[travail du jour](../travail-du-jour/) pour comprendre l'origine des chiffres.
Ces indicateurs ne constituent pas un bilan réglementaire validé pour des
dossiers réels.

## Explorer le scénario Établissement Les Passerelles

Sur la période J−60 à J+1, sélectionner « Explorer les repas par mois et service » et « Total par catégorie » : le jeu initial comprend 2 déjeuners et 3 dîners effectivement distribués. Le rapport des nuitées par lieu présente les affectations théoriques, sans déduction des absences et sans preuve de présence physique. Les résultats sont agrégés, non nominatifs. Les captures publiques illustrent ces deux regroupements ; elles sont régénérées en CI sur une base jetable.
