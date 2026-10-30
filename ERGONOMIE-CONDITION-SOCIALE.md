# Bande Dessinée — inventaire, conception et livraison

**Présentation actuelle :** les [rubriques repliables de NAV3](NAVIGATION-DOSSIERS.md#nav3--rubriques-repliables) complètent le sommaire et les accès de NAV2. Le [volet entier de NAV4](NAVIGATION-DOSSIERS.md#nav4--volet-social-repliable) et ses rubriques démarrent repliés avec JavaScript, puis retrouvent les choix de session ; sans JavaScript ils sont initialement ouverts. Les lectures datées et les données restent inchangées.

Les sections BD-SOLENNE ci-dessous conservent l’inventaire et les jalons historiques. Le lot BD-SOLENNE-02 s’appliquait après le lot 01 et nécessitait sa propre migration ; NAV3 ne comporte aucune migration.

Référence de l’inventaire initial : `bada708692221bc90e84c870128eaf2ca1650907` (miroir GitHub téléchargé le 25 octobre 2026). Les main Inria et GitHub ont ensuite été revérifiés au même SHA le 26 octobre 2026.

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


## BD-SOLENNE-03 — finitions après essais utilisateur

Base publique vérifiée sur Inria et GitHub :
`892a0c2775d25ea76611265e155b6212447a2686` (arbre identique au lot 02 local).
Le sommaire conserve les entrées principales et la composition du ménage ; les
personnes, rubriques et projet sont accessibles par un dépliage natif fermé par
défaut. Déplier la navigation ne replie pas les données de la vue intégrale.
Les documents disposent d'un unique bloc et d'une ancre dans le sommaire ; le
raccourci hérité du commentaire est supprimé. Les appels au 115 conservent leur
espace dédié, accessible depuis une carte et le sommaire, selon les droits.
Le lien autonome vers la trajectoire est supprimé des Forms 2 et 3 : Évolution
utilise déjà cette restitution. Son fragment intégré n'affiche plus de retour
au dossier ; la page autonome conserve ce retour et ses filtres.
L'action courante est Modifier : changer à la date sélectionnée pour une valeur
héritée, ou corriger la déclaration commencée à cette date. Une correction
antérieure et le retrait restent explicitement accessibles dans Autres actions,
avec les contrôles de portée et les droits existants. Si seul le droit de
correction est disponible sur une information héritée, son libellé reste
explicite : aucun changement de période ne se cache derrière Modifier.
Aucun changement de modèle, migration, source statistique ou format de copie.
Vérification HTML et tests automatisés ; pas d'observation réelle navigateur.

Retour CI captures : le comptage du lien dans le sommaire mobile doit inclure
les éléments masqués sur écran large. Pour le retrait, la valeur précédente
étant déjà présente dans l'aperçu, sa visibilité ne prouve pas la fin du POST :
la recette attend désormais la disparition du formulaire avant de vérifier la
base. Les parcours sont aussi adaptés aux menus secondaires et à Modifier.
La CI conserve le journal complet des tests navigateur dans un artefact distinct,
sans modifier les paramètres HTTPS des profils locaux.


## BD-SOLENNE-04 — saisie sur place et contexte facultatif

Base publique vérifiée sur Inria et GitHub : `2cd70e7d2c672db06f212401e6c0d721c5120b07` (lot 03, arbre identique à la
livraison locale). Ce lot s’applique après BD-SOLENNE-03 et ajoute la migration
0041. Aucun changement du socle ni des définitions ou sources statistiques.

L’encadré Vue et saisie réunit les sélecteurs et le contexte commun. Les dates
implicites sont calculées, désactivées et grisées. Une date explicite reste
éditable ; un champ caché garantit aussi le repli GET sans JavaScript.
Présentation et origines s’appliquent au changement avec JavaScript. La synthèse
sélectionne trois valeurs renseignées au maximum, pas les trois premières colonnes.
Les dates et sources sont visibles sur demande dans les deux présentations.

L’éditeur remplace la lecture de la déclaration concernée, avec Enregistrer et
Annuler. Les autres déclarations restent visibles et intactes. Les sources et
précisions facultatives sont regroupées ; leurs erreurs ouvrent ce groupe. Un
conflit garde les valeurs saisies et ne crée pas de journal supplémentaire.
La navigation de vue est bloquée pendant l’écriture ; le focus revient dans la
rubrique après enregistrement, et au déclencheur après annulation.

Le contexte est un champ propre aux journaux sociaux et versions de projet,
distinct de la source du fait et du motif. Il est propagé uniquement pendant
l’appel métier explicite, par un scope ContextVar réinitialisé même sur erreur.
Les journaux participants enregistrent le contexte dans la même transaction.
Pas de conversion des anciens motifs, pas de source/date fabriquée ou recopiée
sur toutes les données. Une source inconnue reste vide. Les champs source des
faits sociaux et les motifs des rectifications ordinaires deviennent facultatifs.
Les annulations et fins explicites gardent leurs contrats spécialisés. Les autres
usages de séries personnelles (répertoire, contact désigné) restent inchangés.

Le contexte choisi est conservé pour ce compte, ce dossier et ce jour, dans la
session de l’onglet si disponible ; les suggestions viennent des journaux
consultables, sans nouvelle table d’entretien. Sans JavaScript, le formulaire
complet propose son propre contexte facultatif. Les copies natives et exports
intégraux incluent le nouveau champ ; un retour de migration refuse de supprimer
des contextes déjà renseignés.

La portée compte les prises dont la période croise la correction, y compris une
prise commencée auparavant. Les rectifications à la date du renseignement sans
déplacement de période ni autre prise concernée conservent une preuve signée,
sans case de confirmation supplémentaire. Les autres corrections, les retraits,
les droits, les bénéficiaires explicites et les contrôles périmés restent contrôlés.

Les déclarations multichamps demeurent des unités métier : leurs couleurs ne
créent toujours pas de filiation persistante par champ. Les recettes Chromium
couvrent dates, présentations, origines, annulation et formulaires sur place ;
distinguer leur exécution CI d’une vérification HTML locale.

Validation du lot : suite complète (770 tests, 38 ignorés), puis dernière passe
ciblée (44 tests, dont 3 recettes Chromium ignorées ici faute de navigateur).
Les passes ciblées précédentes de 79 et 69 tests couvrent aussi concurrence,
migrations et copies restaurées. Contrôles Django, absence de migration manquante,
application locale de 0041, syntaxe JavaScript et diff sans erreur. Le dernier
polissage des libellés, de la grille de saisie et des liens de repli est vérifié
en lecture de code et compilation des templates, sans observation graphique.


## BD-SOLENNE-05 — présentations, sommaire et bornes d’évolution

Base Inria examinée : `8c155884587e733eb4cc1ca84aca1af25d21e7f5`, arbre identique au lot 04 local.
Ce lot s’applique après le 04, sans migration ni changement du socle ou des statistiques.

Complet remplace le libellé Intégrale. Informations renseignées remplace Synthèse :
tous les champs renseignés, sans limite de nombre ni troncature, mêmes rubriques et
accès de saisie. Les valeurs explicitement inconnues restent des renseignements.
Les anciennes clés d’URL integrale/synthese restent compatibles ; la règle à trois
valeurs du lot 04 est abandonnée. Pas de nouvelle synthèse métier implicite.

Le sommaire présente deux dépliants indépendants et fermés par défaut : Composition
du ménage (personnes puis rubriques) et Projet et parcours (rubriques de projet).
En dossier individuel, le premier s’appelle Informations personnelles. Les liens
des titres permettent de rejoindre le bloc ; le triangle déplie les accès détaillés.
Les ancres de projet sont stables et spécifiques à leurs rubriques.

Évolution propose pour chaque borne entrée, dernier jour connu ou prévu, aujourd’hui,
et date libre selon le contexte. Les raccourcis sont recalculés au serveur, même si
une date différente est envoyée. Une prise sélectionnée initialise entrée → dernier
jour (fin effective prioritaire, sinon prévue) si passé, sinon entrée → aujourd’hui.
La fin est exclue : utilisation de la veille pour comparer les états. Une prévision
future reste annoncée comme telle, sans consultation de faits futurs. Les anciennes
URL avec dates explicites gardent leurs bornes. Les dates libres ne sont pas bornées
artificiellement à la prise : l’histoire personnelle demeure indépendante.

Sans JavaScript, les formulaires GET restent utilisables par validation explicite,
avec un miroir des dates grisées. Le choix date libre s’applique avant de remplir
le calendrier. Dans le bloc intégré, JavaScript active le calendrier ou applique le
raccourci, sans navigation vers une autre page. Aucun nouveau mécanisme d’écriture.

## Options communes et correction depuis Évolution

Base publique examinée : `f45eb1bb93df42b4efdd2f41b5dbb01403d82da2`.

Dans les dossiers et prises en charge, une commande Options à droite du sélecteur
Situation / Évolution ouvre les réglages de la vue active. Ils sont repliés à la
première arrivée ; leur ouverture est retenue par compte, dossier et mode dans
la session de l'onglet, y compris après une correction. Les deux formulaires
partagent une grille adaptative et les conventions de dates symboliques. Les
choix propres à chaque vue gardent leur sens : informations renseignées et
informations ayant évolué ne sont pas fusionnées. La date de Situation et les
bornes symboliques avec leurs dates effectives d'Évolution restent visibles.
Les erreurs d'un filtre ouvrent ses options. Sans JavaScript, les résumés natifs
Options donnent accès aux formulaires GET ; l'évolution garde son lien dédié.

Les éléments datés d'Évolution complètent les accès existants des déclarations
personnelles et économiques : événements, bilans, anciennes valeurs de suivi,
distributions de repas non annulées et dates des séjours. Le bouton Modifier
vise l'objet précis, réutilise son formulaire, ses droits, sa preuve d'état et
son journal. Les dates d'un séjour ne deviennent pas une nouvelle admission ;
les règles de continuation et de dépendances restent celles du service existant.
Les opérations nécessitant un motif le demandent toujours. Une correction de
bilan reste collective ; le filtrage personnel ne montre pas ces bilans.

Enregistrer ou Annuler conserve la vue sur place. Après une écriture, la vue est
relue avec ses filtres et bornes, et ses dépliants identifiés sont restaurés.
Les identifiants des lignes modifiables dépendent du fait, pas de sa place dans
le tri ; une correction de date ne désigne donc pas accidentellement une autre
ligne. Si une correction fait sortir le fait du filtre, il disparaît normalement
de la sélection. Les liens de source restent des accès secondaires à l'historique.
Les anciennes URL et les formulaires en pleine page restent disponibles.
Aucun modèle, migration, droit ou dépendance n'est ajouté.

Recette reproductible avec données fictives :

```sh
python3 manage.py test personnes.tests_trajectoire_unifiee personnes.tests_condition_sociale personnes.tests_frises_objectifs --noinput
PWA_CHROMIUM=/chemin/vers/chromium python3 manage.py test personnes.qualification_evolution --noinput
```

La recette navigateur vérifie le clavier, les deux modes, les options et leur
mémoire après rechargement, une annulation puis correction d'événement daté,
le maintien de la vue, l'historique déplié, l'écran 390 px et les formulaires
sans JavaScript. Les tests HTTP couvrent aussi bilans, refus de correction en
lecture seule, formulaires périmés et accès aux formulaires de prestations.
Cette observation Chromium ne qualifie pas Firefox, Pyodide/OPFS, les programmes
natifs ni PostgreSQL.

Validation du lot : 47 tests ciblés distincts réussis (trajectoire, condition
sociale, objectifs et saisie sociale), deux recettes réelles Chromium réussies,
contrôles Django, absence de migration, syntaxe JavaScript et diff sans erreur.
Le patch est vérifié par git am sur la base publique indiquée ci-dessus.

Suite générale exécutée : 964 tests, trois ignorés et trois échecs. Deux sont
les échecs ACT13 déjà constatés sur la base :
`personnes.tests_ergonomie.ErgonomieTests.test_notes_correction_annulation_et_conflit_conservent_contexte`
et `personnes.tests_textes_integration.ParcoursTests.test_refus_document_malveillant_sans_ecriture`.
Le troisième exigeait l'ancien titre « Vue et saisie » : cette assertion est
adaptée à Options, puis les neuf tests de saisie sociale sont tous réussis.
La suite générale n'a pas été répétée après cette adaptation du seul test ;
les derniers ajustements de disposition sont vérifiés par la recette Chromium.

## Dépliants et catégories de repas

Base publique examinée : `73ee74317818cfd7d16ad3fa3e20195db498234d` (ACT18).
Options conserve sa position et sa mémoire, avec l'indicateur de dépliage et le
cadre discret des commandes Liaisons / Équipe de suivi. L'état reste annoncé par
aria-expanded ; le triangle est décoratif. Le repli sans JS reste natif.

La catégorie de repas reste visible lors d'une distribution et de sa correction.
Le champ propose les catégories enregistrées sur des distributions non annulées,
accessibles au compte et rattachées au même service que l'accord visé. Le service
courant de l'interface ne remplace pas le service de l'accord. Sans rattachement
de service, la recherche reste limitée à cet accord. Au plus 50 propositions
alphabétiques sont présentées ; une autre valeur reste saisissable librement.
Aucun dossier inaccessible n'est lu pour compléter cette liste.

Une nouvelle distribution n'a pas de catégorie présumée : la valeur vide porte
le repère « Non renseignée ». En correction, la catégorie enregistrée est
préremplie et une modification de quantité ne la remplace pas. L'aide facultative
existante de proposition selon l'âge reste explicite, avec vérification avant
l'enregistrement. Aucun tarif n'est déduit automatiquement.

Le motif de correction ordinaire d'une distribution devient « Précision sur la
correction (facultative) ». Il est regroupé dans Précisions facultatives, fermé
initialement, ouvert si ce champ contient une erreur, sur place comme en pleine
page. Le champ catégorie n'est pas replié. Le regroupement réutilise le composant
commun avec les noms de champs explicitement déclarés par le formulaire.
Les corrections gardent auteur, horodatage, avant/après, preuve d'état et refus
d'une distribution annulée. Les motifs d'annulation et des autres opérations
conservent leurs règles. Le modèle du journal accepte déjà un motif vide :
aucune migration, nouvelle permission ou dépendance.

Recette automatisée : `personnes.tests_categories_repas`, `personnes.tests_repas`,
`personnes.tests_meta_c`, `personnes.tests_saisie_sociale` et
`personnes.tests_trajectoire_unifiee`. La recette Chromium
`personnes.qualification_evolution` comprend une correction de repas sur place
sans motif, la conservation de sa catégorie, le formulaire en pleine page et la
création avec suggestions sans catégorie imposée.

Contrôle indépendant signalé sur cette base :
`node scripts/verifier-recherche-dossiers.cjs` échoue avec
`ReferenceError: window is not defined` depuis l'utilisation de
`window.PasRecherche` par la recherche. Le banc et les scripts de recherche
sont identiques au main public ; ce lot ne les modifie pas. La recette réelle
Chromium charge les ressources de la page normalement. Ce diagnostic concerne
l'adaptation du banc Node au module partagé, pas les catégories de repas.

Validation ciblée de ce lot : 62 tests réussis (59 tests repas, méta-C, saisie
sociale et trajectoire ; trois tests spécifiques aux catégories et aux accès).
Trois recettes Chromium réelles réussies, dont clavier, 390 px, sans JavaScript,
correction de repas sur place et en pleine page. Captures inspectées ; aucune
erreur JavaScript observée. Contrôles Django, absence de migration, syntaxe du
script de condition sociale et diff sans erreur. Les programmes natifs,
Firefox, PostgreSQL et Pyodide/OPFS n'ont pas été exécutés pour ce lot.

## Harmonisation transversale des corrections

La règle de précision facultative est généralisée aux corrections ordinaires,
y compris les anciens suivis, prestations, textes, documents et financements.
Elle ne dépend plus du type de journal. Les formulaires complets et sur place
utilisent le même regroupement. Les formulaires mixtes affichent l'exigence
selon l'opération et la recalculent au serveur. Ce lot actualise la restriction
historique aux seuls journaux sociaux et le périmètre limité aux repas du 0008.
L'inventaire et les exceptions par opération sont dans CORRECTIONS-COHERENTES.md.
