# Acteurs et accès — lot d'intégration

Prototype réservé aux données fictives. Le contrôle porte sur les accès métier
qualifiés ci-dessous ; il ne constitue pas une qualification de production ni
une garantie générale d’isolation de toute requête SQL possible.

## Installation

Appliquer le patch puis exécuter `python3 manage.py migrate`. Les migrations
créent les tables, sans habilitation, affectation de données ni activation.
Tant que le contrôle n'est pas explicitement activé, les droits historiques
restent utilisés : il n'y a alors aucun cloisonnement par service.

Le parcours principal reste Dossiers → Dossier → Prise en charge → Prestation.
« Tous » signifie tous les dossiers accessibles. Le classement présente d'abord
les dossiers en attente, puis les dossiers suivis, le service courant,
l'établissement et les autres dossiers accessibles. Le choix du service courant
ne crée pas d'habilitation et ne réduit pas à lui seul le périmètre de lecture.

## Préparation volontaire d'un essai

Employer uniquement des comptes et des fiches de partenaires déjà existants.
La commande suivante crée l'organisation et autorise le compte à la configurer,
sans lui ouvrir les dossiers :

```sh
python3 manage.py preparer_organisation \
  --organisme UUID_ORGANISME --etablissement UUID_ETABLISSEMENT \
  --service 'Service fictif' --compte-configuration COMPTE_EXISTANT --confirmer
```

Dans `/organisation/`, inscrire explicitement les professionnels dans les
services, relier éventuellement leur compte existant, puis accorder les tâches
et dates choisies. Ces trois opérations sont distinctes. Aucun compte extérieur
n'est créé. Les options de statistiques regroupées, d'export et de correction
d'autrui sont explicites. Une responsabilité métier seule ne suffit pas.

Chaque service choisit entre lecture/écriture collectives, lecture collective
avec écriture sur les dossiers suivis, ou lecture/écriture sur les dossiers
suivis. Une habilitation actuellement valable reste nécessaire pour consulter
une période ancienne. Les responsabilités sont conservées après un relais ;
les habilitations et la politique courantes déterminent les accès restants.

## Données antérieures

L'affectation technique est volontaire et exacte, sans propagation récursive.
Le manifeste JSON contient `service` (identifiant numérique) et `dossiers` :

```json
{"service": 1, "dossiers": [{"nature": "menage", "id": "UUID_MENAGE", "objets": [{"modele": "personnes.menage", "id": "UUID_MENAGE"}]}]}
```

Inclure explicitement chaque objet à conserver accessible, ses versions et ses
journaux. Vérifier leurs rattachements. Les parents privés doivent être inventoriés ou
déjà affectés au même dossier/service ; l’ordre des lignes est indifférent. Un objet déjà affecté ne peut pas être déplacé par cette commande.

```sh
python3 manage.py affecter_donnees_service inventaire.json --auteur COMPTE_EXISTANT
python3 manage.py affecter_donnees_service inventaire.json --auteur COMPTE_EXISTANT \
  --appliquer --empreinte SHA256_AFFICHE
```

La première commande vérifie sans écrire. La seconde exige l'empreinte exacte.
Aucune responsabilité ni habilitation n'est créée. Les données non inventoriées
sont conservées mais ne seront pas accessibles une fois le contrôle activé.
La préparation d'un inventaire complet n'est pas automatisée dans ce lot.

Sur une copie d'essai sauvegardée, après vérification des affectations et des
habilitations, l'activation explicite est :

```sh
python3 manage.py activer_acces_services --auteur COMPTE_HABILITE --confirmer
```

## Limites de qualification

Les tests `acteurs` couvrent notamment politiques de service, accès directs,
listes, fragments, prestations seules, auteurs, relais périmés, révocation,
pièces jointes, statistiques regroupées et exports. Ils ne démontrent pas une
isolation exhaustive de toute requête possible.

La clôture d’une prise en charge termine ses responsabilités et celles de ses
prestations, sans terminer celles du dossier. Pour une clôture rétrospective,
la fin métier et l’arrêt des accès au moment de l’opération restent distincts.
Les responsabilités futures exclues sont annulées et conservées. Un relais
antérieurement préparé est alors périmé. Une fin d’accord d’hébergement ne
remplace pas la sortie effective d’un séjour encore ouvert.

`acteurs.tests_operations` exerce les relais et reprises réellement concurrents
et la sauvegarde/restauration ZIP avec ces habilitations. Les sélections de
lecture sont mémorisées dans la requête seulement, invalidées lors des mutations
d’organisation ; les écritures sont revalidées sans ce cache. Les répertoires de
partenaires et de professionnels restent communs à cette base applicative. Les
outils de copies du programme local et de la coque PWA sont ceux du propriétaire
de l’appareil : ils portent sur la base entière, hors du périmètre du compte
métier. Le contrôle Django ne protège pas contre le détenteur de cette copie
ou des fichiers SQLite. Ne pas confondre ce contrôle métier avec une isolation
matérielle entre comptes sur un poste partagé.

Recettes supplémentaires :

```sh
python3 manage.py test acteurs.qualification_navigateur --noinput
python3 scripts/qualifier-acteurs-profils.py
```

La seconde exerce les vues Django et les vrais PDF des configurations
bureau/serveur/PWA ; elle ne constitue pas une exécution de Pyodide, de l’OPFS
ou des programmes Windows/Linux. Les observations Chromium sont séparées de ces
contrôles HTML. La recette `scripts/verifier-pwa-pyodide.mjs` exerce aussi le
contrôle actif dans le vrai Python/SQLite WASM sous Node ; elle ne remplace pas
les essais OPFS dans un navigateur. La qualification PostgreSQL reste celle du job existant ; les
essais locaux SQLite ne la remplacent pas.

## Voir immédiatement les changements sur une base fictive séparée

Les commandes suivantes créent un espace temporaire vide. Le mot de passe du
compte d’essai est demandé au terminal. Aucun compte n’est créé par la commande
de préparation des acteurs ; elle affecte les tâches aux comptes explicitement
désignés et refuse une base métier déjà remplie.

```sh
export ACCOMPAGNEMENT_DONNEES="$(mktemp -d /tmp/pas-acteurs-fictifs-XXXXXXXX)"
python3 manage.py migrate
python3 manage.py creer_compte_essai essai-acteurs
python3 manage.py preparer_essai_acteurs --compte-social essai-acteurs --confirmer
python3 manage.py runserver 127.0.0.1:8001
```

Ouvrir <http://127.0.0.1:8001/> puis se connecter avec ce compte. Le service
commence en lecture/écriture collectives. Dans **Dossiers**, essayer **Tous**,
**Mes dossiers** et **En attente**. Ouvrir le dossier en attente et **Commencer
le suivi**, puis **Passer le relais** au collègue fictif sans compte. L’histoire
reste consultable et aucun accès n’est accordé à ce collègue par sa désignation.

Dans **Organisation et accès**, passer le service en politique individuelle :
le dossier relayé n’est plus accessible au premier professionnel ; le dossier
réservé à l’autre service n’était déjà pas visible. Le dossier « Ma prestation
seule » reste un exemple de responsabilité limitée à une prestation. Le compte
social de cet essai a explicitement les options statistiques du service, export
et correction d’autrui ; aucun accès global n’est ajouté.

Pour essayer l’accueil ou la coordination, créer volontairement leurs comptes
sur une autre base d’essai vide, puis ajouter `--compte-accueil NOM_EXISTANT`
et/ou `--compte-coordination NOM_EXISTANT` à la préparation. La coordination
arrive sur les statistiques regroupées et n’ouvre pas les dossiers.

Les missions professionnelles historiques restent distinctes de ces
responsabilités : aucune définition statistique n'est changée ni aucune
correspondance de personnes déduite de leur nom. Les chiffres regroupés ne
sont pas présentés comme anonymes. L'organisme exploitant et le lieu physique
restent distincts ; « interne/externe » est qualifié relativement à
l'établissement de référence et à la date, à partir de l'exploitation déclarée.
