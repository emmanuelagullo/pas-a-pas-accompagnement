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
application. #SOC2 adopte `pas_communs.paquets` : enveloppe ZIP, copie SQLite,
empreintes et préparation de restauration. Les commandes de gestion sélectionnent
le profil CHRS ; elles n'importent aucun modèle scolaire. Les sessions sont
supprimées uniquement dans la copie restaurée. Le compte existant permet ensuite
une nouvelle connexion. La connexion reste provisoirement celle de Django.

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


## #SOC3 : programme local

`settings_local` active WhiteNoise et l'installation du premier compte, avec
des noms de cookies propres au CHRS. `scripts/lancer-local.py` choisit le paquet,
configure Django et délègue verrou, serveur et fenêtre à `pas_communs.local`.
Le `.spec` énumère les seuls modules et ressources CHRS ; il utilise le même
assembleur que Petits Pas. Les données du développeur sont isolées des hooks
Django de construction dans un dossier temporaire, jamais embarqué.

L'installation n'existe que dans le profil local, sans compte ni personne.
La sérialisation des requêtes du lanceur et le verrou interprocessus protègent
ce premier compte ; l'opération reste transactionnelle et n'accorde que les
droits de consultation et création. Ce n'est pas encore une politique d'équipe
ou de plusieurs établissements. Les fichiers de #SOC1 restent utilisables.

## Frontière d’authentification (#SOC4a)

Le modèle identites.Utilisateur et ses migrations restent propres au CHRS.
Seuls le plafond et la fermeture des sessions DB emploient les mécanismes du
socle. Le premier compte local utilise explicitement le backend standard après
création validée ; le backend de plafond n’authentifie jamais personne.
Aucun modèle ou rôle TOTP scolaire n’est copié. Avant #SOC4b, fixer les règles
CHRS d’obligation, de récupération et de révocation, et tester les limites de
tentatives ; ne pas assimiler administration technique et fonction sociale.
