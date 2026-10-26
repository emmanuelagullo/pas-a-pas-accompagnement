# Bande Dessinée — inventaire, conception et livraison

**État courant : lot BD-SOLENNE-02, à appliquer après le lot 01.** La section finale actualise les limites historiques du premier lot. Une migration est nécessaire pour le lot 02.

Référence examinée : `bada708692221bc90e84c870128eaf2ca1650907` (miroir GitHub téléchargé le 25 octobre 2026). Les main Inria et GitHub ont ensuite été revérifiés au même SHA le 26 octobre 2026.

## Portée

Inventaire structurel ciblé des modèles servant la situation sociale, famille, identité, coordonnées, droits, économie et parcours. Champs extraits du code, héritage inclus ; ce document ne certifie pas une revue exhaustive des 30 sources Java ni de toutes les actions applicatives.

## Correspondance des données

### Identité

Modèle : `Personne`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `designation` | Nom d’usage ou identifiant provisoire | 14 |
| `prenom` | Prénom | 18 |
| `date_naissance` | Date de naissance | 19 |
| `annee_naissance` | Année de naissance seule | 20 |
| `precision_naissance` | Précision de la naissance | 21 |

### Identité déclarée

Modèle : `ComplementIdentite`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `sexe_declare` | Sexe déclaré | 975 |
| `naissance_lieu` | Lieu de naissance (complément) | 976 |
| `naissance_ville` | Ville de naissance | 977 |
| `naissance_pays` | Pays de naissance | 978 |
| `nationalites` | Nationalités déclarées | 979 |
| `apatridie_declaree` | Apatridie déclarée | 980 |
| `source` | Source de l’information | 981 |

### Situation familiale

Modèle : `DeclarationFamiliale`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `situation_familiale` | Situation familiale déclarée | 690 |
| `rapports_parentaux` | Rapports avec les parents | 691 |
| `fratrie` | Fratrie déclarée | 692 |
| `enfants_a_charge` | Nombre déclaré d’enfants à charge | 693 |
| `enfants_non_a_charge` | Nombre déclaré d’enfants non à charge | 694 |
| `grossesse` | Grossesse déclarée | 695 |
| `source` | Source de l’information | 696 |

### Liens personnels

Modèle : `RelationPersonnelle`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `nature` | Nature | 1024 |
| `precision` | Précision du lien | 1025 |
| `source` | Source de l’information | 1026 |

### Coordonnées

Modèle : `CoordonneesPersonnelles`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `usage_adresse` | Nature de l’adresse déclarée | 734 |
| `rue` | Adresse déclarée — rue et complément | 735 |
| `code_postal` | Code postal | 736 |
| `ville` | Ville | 737 |
| `pays` | Pays | 738 |
| `telephone` | Téléphone | 739 |
| `courriel` | Courriel | 740 |
| `fax` | Fax (si utile) | 741 |
| `source` | Source de l’information | 742 |

### Logement et emploi

Modèle : `SituationPersonnelle`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `dimension` | Dimension | 629 |
| `valeur` | Valeur | 630 |
| `source` | Source | 631 |

### Administration et droits

Modèle : `SituationAdministrative`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `numero_ss` | Identifiant de sécurité sociale déclaré | 1071 |
| `numero_caf` | Identifiant allocataire déclaré | 1072 |
| `qualification` | Qualification déclarée | 1073 |
| `droit_sejour` | Situation de séjour déclarée | 1074 |
| `echeance_sejour` | Échéance prévue du droit de séjour | 1075 |
| `sans_emploi_duree_declaree` | Durée déclarée sans emploi (si connue) | 1076 |
| `sans_domicile_duree_declaree` | Durée déclarée sans domicile (si connue) | 1077 |
| `sans_emploi_depuis` | Sans emploi depuis | 1078 |
| `precision_sans_emploi` | Précision de cette date | 1079 |
| `sans_domicile_depuis` | Sans domicile depuis | 1080 |
| `precision_sans_domicile` | Précision de cette date | 1081 |
| `source` | Source de l’information | 1082 |

### Ressources

Modèle : `RessourcePersonnelle`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `etat` | État de la déclaration | 1122 |
| `source` | Source de l’information | 1123 |
| `libelle` | Nature du revenu | 1143 |
| `organisme` | Organisme | 1144 |
| `montant` | Montant déclaré | 1145 |
| `devise` | Devise | 1146 |
| `periodicite` | Périodicité | 1147 |

### Dettes

Modèle : `DettePersonnelle`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `etat` | État de la déclaration | 1122 |
| `source` | Source de l’information | 1123 |
| `nature` | Nature du montant | 1160 |
| `creancier` | Créancier ou type de créancier | 1161 |
| `organisme` | Organisme | 1162 |
| `montant` | Solde de dette déclaré | 1163 |
| `devise` | Devise | 1164 |
| `reference` | Référence de dette (facultative) | 1165 |
| `mensualite` | Mensualité déclarée (même devise) | 1166 |

### Pièces présentées

Modèle : `PieceAdministrative`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `etat` | État de la déclaration | 1122 |
| `source` | Source de l’information | 1123 |
| `type_document` | Type de pièce présentée | 1181 |
| `reference` | Référence déclarée (facultative) | 1182 |
| `date_presentation` | Date de présentation connue | 1183 |
| `echeance_prevue` | Échéance prévue annoncée | 1184 |

### Couvertures sociales

Modèle : `CouvertureSociale`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `etat` | État de la déclaration | 1122 |
| `source` | Source de l’information | 1123 |
| `libelle` | Couverture déclarée | 1198 |
| `regime` | Régime déclaré | 1199 |
| `organisme` | Organisme | 1200 |
| `identifiant` | Identifiant d’adhésion déclaré | 1201 |
| `interlocuteur` | Interlocuteur | 1202 |
| `echeance_prevue` | Échéance prévue annoncée | 1203 |

### Protection juridique

Modèle : `ProtectionJuridique`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `etat` | État de la déclaration | 1122 |
| `source` | Source de l’information | 1123 |
| `mesure` | Mesure déclarée | 1215 |
| `domaine` | Portée déclarée | 1216 |
| `precision_portee` | Précisions sur la portée | 1217 |
| `reference_decision` | Référence de décision connue | 1218 |
| `date_decision` | Date de décision connue | 1219 |
| `echeance_prevue` | Échéance prévue annoncée | 1220 |
| `representant_intervenant` | Professionnel représentant déclaré | 1221 |
| `representant_personne` | Representant personne | 1222 |
| `organisme` | Organisme | 1223 |
| `interlocuteur` | Interlocuteur | 1224 |

### Besoins pratiques d’accueil

Modèle : `BesoinAccueil`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `etat` | État de la déclaration | 1122 |
| `source` | Source de l’information | 1123 |
| `categorie` | Nature du besoin déclaré | 1789 |
| `libelle` | Besoin ou situation déclaré | 1790 |
| `adaptation` | Adaptation pratique demandée (si connue) | 1791 |

### Antécédents institutionnels

Modèle : `AntecedentInstitutionnel`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `etat` | État de la déclaration | 1122 |
| `source` | Source de l’information | 1123 |
| `libelle` | Institution ou type de passage déclaré | 1809 |
| `frequentation` | Fréquentation de cette institution déclarée | 1810 |
| `organisme` | Organisme | 1811 |
| `periode_declaree` | Période déclarée (si non datée précisément) | 1812 |
| `date_entree` | Entrée connue dans cette institution | 1813 |
| `date_sortie` | Sortie connue de cette institution | 1814 |
| `precision_dates` | Précision des dates connues | 1815 |

### Ancrage territorial

Modèle : `AncrageTerritorial`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `etat` | État de la déclaration | 1122 |
| `source` | Source de l’information | 1123 |
| `type_territoire` | Type de territoire déclaré | 1837 |
| `territoire` | Territoire déclaré | 1838 |
| `anciennete_declaree` | Ancienneté déclarée | 1839 |
| `depuis` | Présence déclarée depuis | 1840 |
| `precision_depuis` | Précision de cette date | 1841 |

### Évolutions déclarées

Modèle : `EvolutionPersonnelleDeclaree`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `etat` | État de la déclaration | 1122 |
| `source` | Source de l’information | 1123 |
| `domaine` | Domaine de l’évolution déclarée | 1862 |
| `libelle` | Évolution déclarée | 1863 |

### Menage

Modèle : `Menage`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `libelle` | Libellé | 96 |

### Appartenance

Modèle : `Appartenance`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |

### ContactMenage

Modèle : `ContactMenage`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `contact` | Personne de contact | 775 |
| `source` | Source de la désignation | 777 |

### Accompagnement

Modèle : `Accompagnement`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `fin_prevue` | Fin prévue exclue | 131 |
| `beneficiaires` | Beneficiaires | 135 |

### InformationsAccompagnement

Modèle : `InformationsAccompagnement`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `referent` | Référent professionnel | 592 |
| `provenance` | Provenance à l’entrée | 593 |
| `motif_entree` | Motif d’entrée | 594 |
| `orientation_sortie` | Orientation à la sortie | 595 |
| `motif_sortie` | Motif de sortie | 596 |
| `destination_sortie` | Destination à la sortie | 597 |
| `objectifs_courts` | Objectifs à court terme | 598 |
| `objectifs_longs` | Objectifs à plus long terme | 600 |
| `activite` | Activité de la prise en charge | 602 |
| `animaux` | Animaux — information pratique pour l’accueil | 603 |
| `motif` | Motif de mise à jour | 604 |

### VersionDemande

Modèle : `VersionDemande`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `source` | Source de l’information | 1315 |
| `etat` | État de la demande | 1328 |
| `groupe_demande` | Personne seule ou groupe demandeur déclaré | 1329 |
| `motif_demande` | Motif de la demande | 1330 |
| `motif_decision` | Motif de la décision ou du retrait | 1331 |
| `demandeur` | Demande exprimée par | 1332 |
| `demandeur_professionnel` | Demandeur professionnel | 1333 |
| `demandeur_organisme` | Demandeur organisme | 1334 |
| `precision_demandeur` | Précision sur le demandeur | 1335 |
| `prescripteur` | Prescripteur | 1336 |
| `organisme_orienteur` | Organisme orienteur | 1337 |
| `provenance` | Provenance déclarée | 1338 |
| `dernier_hebergement_type` | Type du dernier hébergement déclaré | 1339 |
| `dernier_hebergement_lieu` | Lieu du dernier hébergement déclaré | 1340 |
| `dernier_hebergement_duree` | Durée déclarée dans le dernier hébergement | 1341 |
| `accueil_prevu` | Date d’accueil annoncée | 1342 |
| `activite` | Activité demandée | 1343 |

### VersionOrientation

Modèle : `VersionOrientation`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `source` | Source de l’information | 1315 |
| `etat` | État de l’orientation | 1353 |
| `destination` | Destination | 1354 |
| `type_destination` | Type de solution ou de service | 1355 |
| `organisme` | Organisme | 1356 |
| `interlocuteur` | Interlocuteur | 1357 |
| `motif_orientation` | Motif de l’orientation | 1358 |
| `resultat` | Résultat ou motif de refus/abandon | 1359 |
| `date_prevue` | Date annoncée | 1360 |

### VersionObjectif

Modèle : `VersionObjectif`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `source` | Source de l’information | 1315 |
| `etat` | Avancement | 1368 |
| `theme` | Thème | 1369 |
| `titre` | Objectif | 1370 |
| `horizon` | Horizon | 1371 |
| `echeance` | Échéance visée | 1372 |
| `texte` | Démarche et bilan de progression | 1373 |

### VersionRepereDossier

Modèle : `VersionRepereDossier`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `debut` | Début inclus | 109 |
| `fin` | Fin exclue | 110 |
| `source` | Source de l’information | 1315 |
| `etat` | État du suivi du dossier | 1379 |
| `raison` | Raison du changement de suivi | 1380 |

### EvenementSocial

Modèle : `EvenementSocial`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `beneficiaire` | Beneficiaire | 412 |
| `date_effet` | Date de l’événement | 413 |
| `texte` | Événement significatif | 414 |
| `source` | Source de l’information | 415 |

### BilanSocial

Modèle : `BilanSocial`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `date_effet` | Date du bilan | 422 |
| `texte` | Bilan court | 423 |

### CommentaireDossier

Modèle : `CommentaireDossier`.

| Champ | Libellé du modèle | Ligne models.py |
|---|---|---|
| `texte` | Texte | 673 |
| `motif` | Motif | 675 |

## Constats de parcours issus des templates

- Form2 : _etat_social dirige vers des écrans distincts pour famille, coordonnées, identité, relations et groupes spécialisés ; les trois situations globales ont leurs propres liens de changement/correction.
- Form3 : prestations avant la situation ; deux panneaux temporels ; projet réparti entre parcours, informations versionnées, professionnels, notes et anciens suivis.
- Identité principale : corrections journalisées, pas même chronologie à périodes que les déclarations personnelles. La maquette le signale.
- Coordonnées et famille : versions regroupant plusieurs champs. Une modification d’un champ doit conserver ses voisins sans prétendre disposer de versions indépendantes par champ.
- InformationsAccompagnement : versions de saisie sans date d’effet ; ne pas les redater artificiellement avec le sélecteur.
- Retirer un changement : intention nouvelle à spécifier par type ; ne pas promettre un bouton générique déjà disponible. Les séries à plusieurs ressources, protections et relations ne sont pas des valeurs uniques héritées.

## Arbitrages de présentation

- Quatre blocs principaux Form2/Form3 conformément à la discussion ; en-tête de repérage non éditable.
- Situation commune : personne comme repère ; composition et contact du ménage séparés des déclarations personnelles ; projet/objectif avec bénéficiaires et rattachement explicites.
- Vue intégrale ouverte ; sommaire latéral et sous-navigation par ancres. Vue synthèse sans dissimulation des droits.
- Hérité : gris contrasté ; à la date : texte principal ; modifications non enregistrées : repère distinct. Les origines détaillées sont optionnelles, mais la portée de correction est obligatoire.
- Date proposée commune ; dérogations par information. Sources jamais recopiées automatiquement ; contexte d’entretien facultatif avec autocomplétion, distinct de source/date.
- Validation possible par groupe métier avec état explicite des enregistrements réussis/échoués. Contexte partagé ne signifie pas transaction globale.

## Fonctions à conserver accessibles

Composition/contact du ménage ; correction d’identité et naissance imprécise ; déclarations inconnues/absence/zéro ; liens et annulations ; ajouts multiples de ressources/dettes/protections ; historique et avant/après ; demandes/décisions et lien admission ; orientations ; objectifs et avancement ; suivi du dossier ; professionnels et missions ; informations pratiques versionnées ; notes et bilans ; documents et anciennes versions ; opérations de prise (prolongation, fin prévue, clôture, bénéficiaires, PDF) ; prestations et opérations spécialisées ; appels 115, financements et répertoires via accès conservés sans dilution dans la condition sociale.

## Dépendances pour le coordinateur

Le lot de présentation et de formulaires est implémenté localement. Aucune modification des définitions ni des sources statistiques. Préserver bd6.etat et les sélections à date, droits serveur, cibles/bénéficiaires, journaux, contrôles de formulaires périmés et profils serveur/bureau/PWA. Ne pas faire dépendre le chantier d’une simplification de tables. Le contexte réutilisable d’entretien et les retraits peuvent exiger de nouvelles opérations métier, voire une persistance nouvelle : à spécifier avant migration. Le partage technique de template ne justifie pas de déplacer le métier dans pas-communs.

## Qualification

Lecture de code et templates effectuée. Maquette autonome avec données fictives : ce ne sont pas des données extraites de dossiers ni une capture applicative. Pas de parcours réel observé dans l’application ; pas de preuve de performance. Scénarios de conception : admission incomplète, entretien multi-dates, correction sur prises chevauchantes, retrait avant un changement futur, ménage multi-personnes, droits limités, conflit de versions. Les mesures runtime restent à réaliser.

## Lot livré : présentation commune et formulaires en place

- Form2/Form3 : même composant, vue intégrale ou synthèse, date explicite, origine optionnelle, sommaire et navigation par personne/rubrique.
- La composition et le contact du ménage sont sélectionnés à la date consultée ; bénéficiaires distincts.
- Champs présents directement, y compris les champs non renseignés ; formulaires métier chargés sur place seulement à la demande. Un seul formulaire actif évite de réutiliser plusieurs jetons périmés.
- Coordonnées, famille, identité, déclarations spécialisées, projets et objectifs réutilisent les validations, droits et journaux existants. Les sources ne sont pas recopiées pour une évolution.
- Les valeurs héritées proposées dans un formulaire de changement sont conservées ; le contexte facultatif préremplit seulement le motif et reste modifiable. Les motifs récents des journaux autorisés sont proposés par autocomplétion. Il n’existe pas encore d’objet d’entretien persistant reliant les journaux.
- Évolution utilise le même cadre visuel, avec chargement à la demande de la trajectoire existante ; aucune modification de ses sélections ni de ses calculs.
- Documents : métadonnées seules, fichiers non chargés à l’ouverture de la page.
- Sans JavaScript : mêmes liens et formulaires pleine page, mêmes contrôles serveur.

## Limites du lot 01 — photographie avant le lot 02

- « Retirer ce changement » : non exposé tant que les opérations de retrait par famille de modèles, la continuité antérieure, les références et la copie restaurée ne sont pas spécifiées et qualifiées. Aucun bouton factice.
- Héritage : couleur de la déclaration datée, pas reconstitution de la provenance indépendante de chaque champ à l’intérieur d’une déclaration multichamps. Les coordonnées et la famille restent des versions de groupe.
- Source/date : restent visibles dans le formulaire métier et conservent leurs contraintes ; aucune suppression artificielle des motifs exigés pour les corrections ou insertions anciennes.
- Les dates de début et les bénéficiaires d’une prise en charge, les appartenances et les missions gardent leurs écrans spécialisés pour les opérations structurelles. L’en-tête n’offre pas d’édition concurrente.
- Portée des corrections : confirmation de la période partagée, sans calcul automatique exhaustif des prises affectées. Le calcul de portée détaillée demeure à compléter.
- Intégrale : informations à plat ; édition par rubrique dans le même bloc. Ce n’est pas encore un mode où tous les champs sont simultanément en édition.
- Sommaire : latéral collant sur très grand écran, horizontal sur les autres largeurs ; la variante mobile compacte fixe reste à qualifier.

## Qualification actuelle

Contrôles Django et absence de migration vérifiés. Six tests nouveaux de lecture, droits, date, source vide, conflit et coût SQL passent ; 58 tests ciblés passent. La suite initiale de 742 tests a terminé avec 38 ignorés, cinq erreurs de dépendance PDF initialement absente et trois assertions de présentation. La dépendance PDF a été installée, deux assertions ont été adaptées aux vues séparées, et l’omission de la liste des professionnels a été corrigée. Les vérifications de reprise sont consignées dans le retour de livraison.

Le navigateur Chromium local est indisponible ; son téléchargement a renvoyé une archive ZIP invalide. Aucune observation réelle de la nouvelle application en navigateur n’est revendiquée. La maquette autonome est une simulation de conception avec données fictives, pas une qualification du patch.


### Résultat des reprises

103 tests réussis après installation de WeasyPrint : histoires familiales, identité et liens, professionnels, parcours, trajectoire unifiée et copie restaurée, exploration et PDF natifs. Les 58 tests du premier ensemble ciblé passent également. Sept tests de dernier rendu (dont les six nouveaux) ont été exécutés après réintégration explicite des témoins des anciens suivis. Il ne s’agit pas d’une nouvelle exécution verte de toute la suite : la suite complète initiale et les reprises sont distinguées.

Base Inria et miroir vérifiés identiques : bada708692221bc90e84c870128eaf2ca1650907. Aucune publication ni modification de production. Aucune migration.


## Lot BD-SOLENNE-02 — contexte visible, portée et retrait

### Navigation et interaction

Le sommaire est hiérarchisé : texte libre, documents, situation sociale et projet (composition du ménage, personnes puis rubriques, projet et parcours), puis prises en charge ou prestations. La branche de la personne consultée est déployée ; un repère suit le défilement. Sur les écrans plus étroits, le sommaire devient un menu « Dans cette page » collant et repliable. Les liens conduisent aux informations, sans changer de page.

Les raccourcis « Dossier individuel » restent disponibles auprès de chaque personne. Les en-têtes et le sommaire sont réactualisés après une correction d’identité. Les écouteurs d’édition restent opérationnels après le remplacement de page effectué par une action de prestation ; une édition de prestation et une édition sociale ne peuvent pas se remplacer mutuellement avec une saisie en attente.

La vue temporelle, sa date, la présentation et l’affichage des origines sont conservés par le contexte de retour signé. Ouvrir une prise depuis Form2 propose toujours la vue d’entrée par défaut. Revenir au dossier depuis une vue d’entrée conserve cette date sous la forme « À une date… », valable hors de la prise.

### Valeurs reprises et valeurs modifiées

Pour les séries personnelles, une lecture groupée de la déclaration précédente distingue les champs repris des champs modifiés à la date consultée. Exemple : une nouvelle déclaration avec un autre téléphone conserve l’adresse en gris. Les origines facultatives précisent « Repris de la déclaration du… ». Une période sans information n’est jamais franchie pour inventer un héritage.

C’est une indication de reprise entre déclarations successives, pas une certification de la première origine de chaque champ ni un lien permanent entre valeurs. Une correction d’une ancienne déclaration ne propage pas automatiquement cette correction à toutes les déclarations ultérieures ayant la même valeur : celles-ci restent des déclarations indépendantes. La période et la déclaration corrigées font autorité.

### Portée des corrections

Les corrections ouvertes depuis le bloc commun affichent la période touchée et les entrées de prises en charge de cette période, sous les droits correspondants. Elles demandent une confirmation serveur signée. Si la modification des dates élargit cette portée après lecture, une nouvelle confirmation est exigée ; aucune écriture n’est faite à la première soumission. Les confirmations de portée ne remplacent jamais les droits, le jeton de version ou les validations métier.

Le nombre affiché compte les entrées dans la période ; il ne prétend pas lister toutes les consultations possibles à d’autres dates. Les documents financiers émis et les fichiers figés ne sont pas réécrits. Les sources et les motifs restent propres aux déclarations.

### Retirer ce changement

L’action existe pour logement, emploi, ressources globales, famille, coordonnées, identité déclarée et situation administrative. Elle est proposée sur un changement commençant à la date consultée. Son aperçu indique les valeurs rétablies et la période ; une confirmation explicite est requise.

Le retrait conserve le changement, son identifiant et ses journaux. Il prolonge uniquement la déclaration précédente qui se terminait exactement au début du changement retiré, jusqu’à la fin de ce changement. Le changement suivant reste intact. Sans précédent continu, la période devient non renseignée. Pour une déclaration multichamps, le retrait porte explicitement sur toute la déclaration de cette rubrique.

Les écritures sont sous transaction et réservation de version de la personne ; un formulaire périmé, une preuve falsifiée, une confirmation absente ou un double retrait ne modifient rien. Les droits de lecture, d’ajout et de modification de la série sont requis, comme pour les corrections existantes.

Les ressources détaillées, dettes, protections multiples, liens, demandes, orientations et objectifs conservent leurs opérations propres. Ils ne reçoivent pas un retrait générique qui pourrait supprimer un poste réel ou invalider une admission liée.

### Persistance et migration 0040

Cinq modèles de séries personnelles reçoivent un horodatage nullable `retire_le`. Aucune ligne existante n’est retirée par la migration. Les contraintes d’unicité portent sur les déclarations non retirées ; les autres contraintes sont conservées.

Le gestionnaire ordinaire `objects` exclut les lignes retirées ; `tous` et le gestionnaire de base les conservent pour les références historiques. Les sources statistiques ne sont ni déplacées ni redéfinies : leurs lectures ordinaires des faits personnels reflètent naturellement le retrait. Tout nouveau calcul utilisant une jointure SQL brute devra respecter la même exclusion ; un gestionnaire de modèle ne filtre pas automatiquement une jointure SQL arbitraire.

Les copies natives conservent la base physique entière, y compris les lignes retirées et les journaux. Les scripts d’export technique complet utilisent désormais `dumpdata --all`. Une copie antérieure est migrable normalement. Un retour du schéma 0040 vers le schéma antérieur est refusé si un retrait a déjà été enregistré, afin de ne pas réactiver silencieusement les changements retirés.

### Qualification du lot 02

- Suite complète : 760 tests exécutés, succès, 38 ignorés selon les dépendances/profils disponibles.
- Après les finitions du contexte de navigation : 62 tests ciblés exécutés, succès.
- Les nouveaux scénarios couvrent les retraits au début/milieu/fin, les trous, la réutilisation d’une date, les séries multichamps, les droits, preuves et formulaires périmés, la concurrence réelle SQLite, l’export complet et la relecture d’une copie restaurée.
- Contrôles Django, synchronisation des migrations, syntaxe JavaScript et propreté du diff vérifiés.
- Recettes navigateur et PWA adaptées aux nouveaux accès. Deux nouvelles recettes Chromium couvrent la hiérarchie, l’édition sur place, le retrait, le rafraîchissement après prestation, la répercussion de l’identité et le sommaire mobile. Elles sont ignorées ici : module Python Playwright absent, et téléchargement du moteur Chromium (y compris Headless Shell) défectueux. Aucune observation réelle de la nouvelle interface n’est revendiquée.

### Suite réellement restante

Qualification visuelle et PWA réelle, mesures sur de gros dossiers et éventuels ajustements après usage. Un éventuel versionnement véritablement indépendant par champ, avec une filiation persistante des valeurs et une propagation des corrections entre déclarations distinctes, demande une conception métier supplémentaire ; il n’est pas simulé par le lot 02. Les opérations structurelles sur les ménages, bénéficiaires et missions gardent leurs validations spécialisées.
