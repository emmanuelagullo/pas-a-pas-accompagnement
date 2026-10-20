# Première V0 métier — préparation après #SOC7a

## Cadrage retenu pour démarrer CHRS1 (AUD)

La première tranche reste **fictive, mono-espace**, avec un seul service d'essai.
Ce service décrit le périmètre du prototype ; il n'impose pas une table
d'organisation avant qu'une action en ait besoin. Aucun cloisonnement entre
établissements n'est revendiqué. Une extension multi-structure exigera un
cadrage explicite, des règles de visibilité et une stratégie de migration.

Les personnes gardent leur UUID et restent distinctes des comptes. Le suivi
porte sur le ménage, personne seule comprise ; ses bénéficiaires sont
enregistrés explicitement et ne dépendent pas de la composition courante.
Plusieurs appartenances ou suivis simultanés ne sont pas interdits par analogie
avec les classes ; leurs cas et invariants doivent être testés dans CHRS1.

Lecture, création et modification des nouveaux objets exigent des permissions
Django explicites propres au CHRS, contrôlées dans les vues et services. Les
comptes existants ne reçoivent aucun nouveau droit automatiquement à la
migration. Le premier compte et les fixtures devront attribuer seulement les
droits nécessaires au parcours d'essai ; l'administration technique n'est pas
un rôle social. Le profil actuel de création de personne reste inchangé.

Pour les périodes de CHRS1, retenir des dates civiles avec début inclus et fin
exclue, fin absente pour une période ouverte. Refuser fin antérieure ou égale au
début ; ne pas déduire une clôture des réalisations ou d'une absence. Distinguer
dates d'effet et horodatages d'enregistrement. Les conventions de repas et de
nuitées seront fixées avec CHRS2/3, sans les déduire de cette convention.

Les décisions ouvertes ci-dessous restent l'inventaire des autres points à
préciser lors des tranches. Ce cadrage précède la livraison CHRS1 décrite ci-dessous.
Avant de livrer CHRS1 : accès sans droit refusé, migration depuis SOC1/SOC4b,
reprise des anciennes copies, mêmes UUID et mots de passe, nouvelles migrations
embarquées dans bureau/PWA, export/restauration des nouvelles relations. Les
premières écritures définiront leurs événements d'audit applicatifs, sans
copier le journal scolaire ni construire un moteur générique.

Les tranches CHRS2–4 restent des propositions. CHRS1 étend le prototype
avec les ménages et accompagnements ; le socle adopté reste en 0.8.0.

## CHRS1 livré

Ménages, appartenances, accompagnements et journal applicatif sont maintenant
implémentés dans personnes. Attribution volontaire via autoriser_chrs1, sans
modification des droits existants. Dates inclus/exclu ; bénéficiaires explicites
figés à l’ouverture. Clôture conditionnelle ; pas de correction ou réouverture
dans cette tranche. CHRS2 est livré ci-dessous ; CHRS3–4 restent proposés.

## Modèle minimal proposé

| Entité | Responsabilité et relations |
| --- | --- |
| Personne | Identité durable, éventuellement incomplète. Garder l'UUID existant et la distinction avec un compte professionnel. Ne pas rendre une date de naissance obligatoire pour distinguer adulte/mineur ; traiter explicitement l'information inconnue. |
| Ménage | Unité accompagnée ensemble, y compris personne seule. Appartenances avec début et fin, sans déduire les liens familiaux ni la représentation légale. |
| Accompagnement | Période de suivi d'un ménage par un service, ouverte puis close ; peut exister sans hébergement. Les bénéficiaires des prestations restent explicites. |
| Prestation accordée | Hébergement ou repas seulement ; accompagnement, bénéficiaires, période et quantité/unité adaptées au type. Source « 115 / SIAO » et référence externe facultative selon le niveau retenu. |
| Réalisation de repas | Date, bénéficiaire, quantité et accord concerné. Les cumuls se comparent à l'accord selon les règles à fixer ; modifier l'accord ne réécrit pas les repas réalisés. |
| Séjour d'hébergement | Admission effective et fin éventuelle, bénéficiaires et accord concerné. Une absence temporaire n'entraîne pas automatiquement la sortie. |
| Affectation | Sous-période d'un séjour à un lieu identifié ; changements successifs, y compris lieu partenaire. Aucun moteur de réservation ou de capacité dans la première tranche. |
| Situation sociale | Quelques dimensions choisies avec valeurs et dates d'effet, événements significatifs et courts bilans. Ne pas déduire automatiquement une nouvelle valeur d'un événement. |

Les bénéficiaires enregistrés d'un accord, repas ou séjour ne sont pas calculés
à chaque lecture à partir du ménage courant : une modification de composition
ne doit pas modifier rétroactivement une prestation. Les règles de correction
et de datation doivent être définies au moment de la tranche concernée.

Les relations familiales et la représentation légale restent distinctes. Ne
pas inventer ces liens à partir du nom ou de l'appartenance au ménage ; ne pas
les ajouter à la V0 tant qu'aucune action ne les utilise.

## Tranches courtes et écrans

| Tranche | Parcours / écrans | Critère d'acceptation fictif |
| --- | --- | --- |
| CHRS1 | Personne → ménage → ouvrir un accompagnement ; fiche de suivi. | Créer un ménage seul ou composé, ajouter une appartenance datée, ouvrir un suivi sans hébergement et le retrouver. Les UUID historiques restent valides. |
| CHRS2 | Accord de repas → saisie des repas réalisés → historique du suivi. | Accorder puis enregistrer des repas pour des bénéficiaires explicites ; distinguer clairement prévu/accordé et réalisé, refuser une quantité invalide. |
| CHRS3 | Accord d'hébergement → admission → affectations → sortie. | Un séjour conserve ses deux affectations successives ; une absence temporaire ne le clôt pas. Refuser une affectation hors séjour et les chevauchements interdits. |
| CHRS4 | Situation datée, événement et bilan court dans la fiche de suivi. | Consulter les valeurs successives et les réalisations dans l'ordre des dates, sans reconstruire tout l'état depuis les événements. |

CHRS1 ne nécessite ni pièce jointe, ni moteur de formulaires, ni génération PDF.
Réutiliser la navigation et les formulaires Django simples ; n'ajouter HTMX
que lorsqu'il simplifie un parcours concret. Ne pas installer d'infrastructure
de tâches pour ces petites écritures transactionnelles.

## Décisions avant le code concerné

Les points déjà retenus sont précisés dans le cadrage AUD ci-dessus. Les autres
choix suivants restent à préciser avant le code concerné :

- **CHRS1 retenu :** espace fictif unique et service d'essai, permissions
  explicites sans droits nouveaux attribués par migration. La connexion seule
  ne confère aucun droit. Le multi-établissement reste hors de cette tranche.
- **CHRS1 retenu :** accompagner le ménage avec bénéficiaires explicites et
  périodes datées selon le cadrage ci-dessus. Décrire les exemples de simultanéité
  et les contrôles de cohérence dans les tests de la tranche.
- **Avant CHRS2 :** repas par personne et jour, ou par service de repas ? Quelle
  quantité, quelles limites de consommation, et comment corriger/annuler ? Où
  porte l'orientation : suivi ou accord ? Ne pas collecter deux fois la même
  information pour anticiper une future interconnexion.
- **Avant CHRS3 :** conventions de nuitées, dates/heures d'entrée-sortie,
  affectation par ménage ou personne, absences et chevauchements. Décider si
  une réalisation sans accord préalable doit être refusée ou régularisable.
- **Avant CHRS4 :** choisir deux ou trois dimensions sociales réellement utiles,
  leurs valeurs et leur datation. Définir correction, visibilité et conservation
  des événements, bilans et changements de valeurs.

L'historique de suivi raconte l'accompagnement. Le journal d'audit raconte les
modifications et leur acteur ; il n'est pas à confondre avec ce parcours. Ses
événements, champs autorisés et règles de consultation seront définis avec les
premières écritures métier, dans les transactions applicatives. La date et
l'auteur de création actuels ne sont pas un journal complet. Ne pas recopier
le modèle d'audit scolaire ou accumuler tous les textes dans un JSON générique.

## Réutilisation et limites

Conserver les comptes, mécanismes TOTP/sessions, paquets, lanceurs, primitives
PWA et recettes de pas-communs. Modèles, migrations, droits, formulaires,
chronologies et données sociales restent dans Pas à Pas. Aucune équivalence
école/CHRS, classe/service, élève/personne ou trace/prestation.

Chaque nouvelle table exige des essais de migration depuis le prototype et
de sauvegarde/restauration ; la PWA doit embarquer les nouvelles migrations.
Tester les refus d'accès dans les vues et les invariants de dates/quantités,
avec des données fictives. Les anciennes copies sans nouvelles migrations
doivent pouvoir être reprises selon les contrôles habituels ; ne pas contourner
le refus des migrations inconnues dans une ancienne version.

Hors V0 : appels du 115, synchronisation SI-SIAO, facturation, dossier médical,
moteur de formulaires, reporting réglementaire exhaustif et gestion documentaire
non justifiée par un parcours. Aucun dossier réel avant un chantier explicite
sur les périmètres d'accès, la conservation et l'exploitation.


## Base serveur et garanties concurrentes

Lire [BASE-CIBLE.md](BASE-CIBLE.md) avant un modèle utilisant des contraintes
ou verrous propres à PostgreSQL. Le backend serveur est une décision distincte
du mono-espace fictif ; bureau et PWA restent SQLite. La qualification doit
exercer chaque garantie sur les deux backends concernés, pas la déduire de
la validation de formulaire ou d'une CI scolaire.

## CHRS2 livré — conventions

Accord de repas immuable par accompagnement, service et bénéficiaires explicites.
Début inclus, fin exclue, service quotidien ; pas de quota global dans cette V0.
Réalisation par bénéficiaire/date avec quantité entière positive ; doublon actif
refusé au niveau SQL dans un même accord. Annulation motivée et nouvelle saisie
pour corriger ; total hors annulations et journal propre aux repas. Prestataire
extérieur possible. Aucun droit automatique. Voir le parcours dans README.md.
Les accords distincts peuvent se chevaucher ; ni réservation ni commandes ni
consommation physique observée ne sont modélisées. L’orientation n’est pas
collectée sur l’accord : elle reste réservée au futur parcours d’orientation.
