# Architecture de #SOC1

## Composants

- `pas_a_pas_accompagnement` : configuration locale, routes, accueil, contrôle SQL.
- `identites.Utilisateur` : compte Django minimal, défini dès la première migration.
- `personnes.Personne` : UUID, désignation obligatoire, prénom facultatif, auteur
  et horodatage de création. Pas de date de naissance, de statut adulte/mineur,
  d'adresse, de relation familiale ou de dossier social à ce stade.
- `templates` et `static` : écrans HTML/CSS simples ; HTMX n'est pas nécessaire
  pour cette première tranche. Pas de dépendance JavaScript ou CDN.

La désignation accepte un nom d'usage ou un identifiant provisoire. Ce n'est pas
une vérification d'identité et elle n'est pas unique. Ne pas déduire un ménage
d'une égalité de nom. Les personnes suivies n'ont pas de compte de connexion.

## État de la factorisation

Les trois dépôts restent distincts : Petits Pas, pas-communs et cette
application. #SOC1 établit le second consommateur et les frontières. Le socle
contient le cadrage ; aucun code Petits Pas n'est copié, déplacé ou modifié.
La connexion utilise provisoirement les vues Django standard. Elle sera adaptée
lors de #SOC4 ; les politiques sociales resteront propres à cette application.

Ne pas imposer des organisations ou habilitations génériques avant d'avoir
confronté les deux métiers. Préserver l'identité des modèles et des migrations
lors des extractions futures, notamment celle du modèle utilisateur.

## Jalons suivants

- #SOC2 : paquets et sauvegardes avec identité du produit et refus croisé.
- #SOC3 : lanceur et construction des programmes locaux.
- #SOC4 : authentification commune, politiques propres à chaque produit.
- #SOC5 : PWA ; les documents nécessiteront un rendu adapté au navigateur.
- #SOC6 : profils serveur, CI et publication réutilisables.

La V0 métier pourra ajouter ménages datés, accompagnements indépendants de
l'hébergement, prestations accordées et réalisations effectives distinctes,
puis séjours et affectations successives. Hébergement et repas seulement au
début. Une absence ne clôt pas automatiquement le séjour. Situation sociale
simple avec valeurs datées, événements et bilans, sans moteur d'événements.
Seule une source d'orientation « 115 / SIAO » et une référence facultative sont
prévues ; pas d'interconnexion ou de gestion des appels du 115.

À décider avant ces ajouts : périmètre d'isolation des structures, habilitations,
bénéficiaires des prestations, unités et bornes de dates. Ces choix ne sont pas
tranchés par la fiche personne fictive de #SOC1.
