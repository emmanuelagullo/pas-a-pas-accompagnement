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

### Coûts et financements

Le rapport dédié permet de consulter et exporter les dernières versions des
calculs, une phase à la fois et des totaux séparés par devise. Les composantes suivent leur date de
prix ; les imputations sont retenues lorsque leur période chevauche la période
recherchée, sans proratisation. Financeur et budget filtrent les imputations ;
unité et catégorie filtrent les composantes. Les montants ne prouvent pas un
paiement et les anciennes versions restent accessibles dans chaque prestation.

### Explorer les populations et croiser les critères

**Explorer et croiser les populations** complète les rapports spécialisés :
choisir d'abord ce qui est compté (personnes, ménages, prises en charge, demandes,
séjours, repas, remises, appels, ressources, dettes, coûts ou imputations).
Choisir ensuite la mesure et les deux axes. Les critères s'ajoutent dans la même
page ; les critères personnels sont vérifiés par la même personne, même si le
ménage comporte plusieurs membres. Pour classer des nombres, saisir des classes
avec minimum inclus et maximum exclu. Les valeurs inconnues restent visibles.

Les montants restent séparés par devise et périodicité ou phase. Les cellules
avec plusieurs valeurs ne s'additionnent pas forcément ; le total est recalculé.
Un effectif déclaré par appel n'est pas un nombre de personnes distinctes.
Les modèles personnels conservent les paramètres et se recalculent sous les
droits actuels, avec dates fixes ou période relative. CSV et PDF reprennent
les mêmes critères. Les limites de calcul produisent un refus explicite,
sans tronquer silencieusement un tableau.

Le scénario neuf de l'**Établissement Les Passerelles** propose quinze appels
et, pour Nadia, deux modèles personnels sur les demandes/réponses et horaires.
Les autres comptes ne voient pas ses modèles privés. Aucun compteur ne permet
de déduire une première admission absolue ou une sortie définitive à partir
d'un historique incomplet.


### Affiner et réutiliser un rapport

Commencez par la population, la période, la référence et une mesure. La rubrique
**Affiner** permet d'ajouter jusqu'à sept niveaux de classement et neuf mesures,
ou des filtres et classes numériques. Les totaux sont recalculés ; n'additionnez
pas les lignes lorsque les catégories peuvent se recouvrir. Les inconnus restent
visibles, notamment pour les âges et déclarations familiales.

Pour l'hébergement, distinguez épisodes de séjour et périodes de lieu. Les
nuitées par âge sont évaluées à chaque nuit : un anniversaire peut changer la
ventilation pendant le séjour. Autorisations, distributions et remises restent
des populations distinctes. Une mission professionnelle se rapporte à la prise
en charge concernée. La référence peut être commune ou suivre la date de chaque
objet ; la référence choisie est conservée dans les paramètres du rapport.

Les modèles personnels peuvent être exportés puis importés en JSON. Ils
contiennent les paramètres, sans les résultats ni les dossiers. Les critères
et droits sont revérifiés à l'import et lors de chaque calcul.

Le relevé détaillé permet de choisir jusqu'à onze colonnes. Depuis une ligne,
ouvrez le dossier puis revenez aux mêmes critères du rapport. Ce retour privé
est valable une journée et reste propre au compte connecté.
