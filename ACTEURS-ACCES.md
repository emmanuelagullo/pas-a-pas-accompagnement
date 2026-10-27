# Acteurs et accès — lot d'intégration

Prototype réservé aux données fictives. Ce lot ne constitue pas encore la
qualification finale d'une isolation entre structures.

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
journaux. Vérifier leurs rattachements et présenter les parents avant leurs
éléments. Un objet déjà affecté ne peut pas être déplacé par cette commande.

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

La qualification finale reste à compléter : relais réellement concurrents,
copies restaurées avec ces habilitations, fin des responsabilités lors d'une
clôture de prise en charge, performances avec le contrôle actif, PostgreSQL et
observations dans un vrai navigateur. Les fins automatiques de responsabilités
ne sont pas livrées ; les dates de fin restent explicites. Ne pas assimiler une
fin de prise en charge à une révocation d'habilitation.

Les missions professionnelles historiques restent distinctes de ces
responsabilités : aucune définition statistique n'est changée ni aucune
correspondance de personnes déduite de leur nom. Les chiffres regroupés ne
sont pas présentés comme anonymes. L'organisme exploitant et le lieu physique
restent distincts ; « interne/externe » est qualifié relativement à
l'établissement de référence et à la date, à partir de l'exploitation déclarée.
