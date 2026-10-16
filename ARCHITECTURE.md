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
une nouvelle connexion. La connexion de base reste celle de Django, complétée par le parcours #SOC4b.

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

## Parcours CHRS (#SOC4b)

Lire AUTHENTIFICATION.md. Les nouveaux modèles DoubleFacteur, CodeSecours et
LimiteAuthentification sont propres à identites ; le socle n’importe aucun modèle.
Le stockage chiffre le secret et utilise les primitives du wheel 0.3.0. Les mises
à jour conditionnelles consomment un pas ou un secours une seule fois même sur
SQLite, sans se reposer sur select_for_update. Une erreur de stockage refuse
l’authentification. La révision du facteur relie attentes et preuves aux données
courantes ; une réinitialisation ou un remplacement invalide les anciennes preuves.

Les compteurs de tentatives sont persistés et atomiques, par compte et adresse,
dans des fenêtres fixes. Aucune confiance aux en-têtes de proxy dans ce profil.
La récupération d’un autre compte est une commande de maintenance au terminal,
sans droit métier web associé. Le changement des droits n’est pas couplé au 2FA.

Les clés de chiffrement et la politique viennent de la configuration CHRS.
Le bureau garde son profil sans activation TOTP, mais une base déjà inscrite ou
à réinscrire est bloquée jusqu’à récupération explicite. La copie restaurée
supprime sessions et compteurs ; elle conserve facteurs et secours consommés.
La migration conserve comptes et personnes existants et ne les inscrit pas au 2FA.

Les journaux techniques et diagnostics masquent les secrets, y compris en DEBUG.
Ils ne constituent ni une preuve d’identité de l’opérateur terminal, ni un audit
métier durable. Le déploiement réseau, la rétention et le périmètre des rôles
restent à traiter dans leurs chantiers respectifs.
