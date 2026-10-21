# Architecture — état courant et historique des jalons

Les sections #SOC retracent les introductions successives. La version adoptée
est fixée par requirements-communs.txt (0.8.0 publiée et adoptée au 20 octobre 2026),
non par les mentions anciennes ci-dessous. La fiche PDF est désormais disponible
(voir PDF.md). Le cadrage retenu avant CHRS1 est dans V0-METIER.md.

## Architecture initiale de #SOC1

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

## Première PWA (#SOC5a)

Lire pwa/README.md. Le wheel 0.4.0 fournit stockage immuable, vérification des
capacités, transport et primitives WSGI/crypto. Le bridge définit les fichiers
CHRS et vérifie les migrations ; les vues, permissions et modèles ne changent pas.
La coque, le Worker et le Service Worker CHRS demeurent des adaptateurs du
produit. #SOC5b ajoute les copies et restaurations sans transférer les flux scolaires.
Le profil reste un prototype fictif, sans déploiement CHRS de production.

## Copies et cycle de vie (#SOC5b)

Les outils techniques de la coque lisent le dernier état confirmé dans un
Worker neuf. Une restauration prépare/valide/migre un autre Worker sans lire
ni modifier les données courantes. Le moteur actuel ne s'arrête qu'à la
confirmation ; la sauvegarde OPFS commune active le nouveau pointeur avec
préservation de l'ancien et sans réemploi de blobs potentiellement corrompus.
Annuler ou refuser le ZIP ne produit aucune écriture OPFS. La réouverture
impose la connexion, sans reprise de cookies ni élargissement de droits.
La copie de secours est exportable même si le moteur Django ne démarre pas.

#SOC5 est clos sur le périmètre des bancs Chromium/Linux. Garder les Workers
et coques propres au produit ; pas de factorisation supplémentaire imposée.
Les types d'organisation, documents et habilitations restent des décisions métier.

## Profil serveur volontaire (#SOC6a)

settings_serveur conserve les modèles et la disposition base/clé du produit.
Le contrat HTTPS vient de pas_communs.serveur ; les choix SQLite, statiques,
TOTP, droits et adresse cliente restent ici. Lire SERVEUR.md. Aucun hébergeur,
proxy ou établissement n'est créé. Les recettes sont complétées sous #SOC6b ci-dessous.

## Recettes et candidats (#SOC6b)

Les deux forges utilisent la recette Django du wheel. Le banc serveur prépare
les données fictives puis exerce aussi un vrai Gunicorn local ; les contrôles
de droits/TOTP restent dans le produit. Le script manifeste-publication.py
utilise le format pas-a-pas-accompagnement-publication et les primitives
communes, sans publier. La PWA normale est vérifiée puis archivée ; un bundle
test ou non marqué est refusé. Les programmes gardent leurs propres noms et
leur qualification. Les adaptateurs et politiques Petits Pas ne sont pas copiés.

## Extensions et première V0 métier (#SOC7a)

L'inventaire `EXTENSIONS.md` du dépôt pas-communs ne justifie pas d'extraction
supplémentaire à ce stade. Images, PDF et traitements scolaires restent dans
Petits Pas. Le document [V0-METIER.md](V0-METIER.md) propose les premières
tranches CHRS et les décisions à prendre avant leur code ; il ne décrit pas
des fonctions disponibles. Le socle reste en 0.5.0, sans nouvelle publication.

## Déploiements et promotions (#SOC6c)

Voir [DEPLOIEMENTS.md](DEPLOIEMENTS.md). Deux scripts serveur distincts :
start-render.sh prépare un espace temporaire neuf avec identifiants publics
fictifs ; start-persistent.sh conserve le dossier et crée une sauvegarde privée
avant migration d'une base existante, après arrêt explicite du service.
Les bancs d'intégration lancent les scripts, vérifient HTTP et redémarrent.
Aucune dépendance PostgreSQL/S3 n'est ajoutée à ce prototype sans fichiers.
Les distributions portent une version applicative distincte du socle 0.5.0.
La PWA est promue depuis un job GitLab réussi vers un projet dédié ; les archives
programmes depuis une construction de tag GitHub réussie. Les actions de
publication et le hook de démonstration sont explicites. Aucun hébergement ou
projet distant n'est créé par le code.


Le futur backend serveur est cadré dans [BASE-CIBLE.md](BASE-CIBLE.md) :
PostgreSQL retenu, avec qualification CI distincte de SQLite,
sans modification du profil serveur actuel.

## Harmonisation des copies (#SOC, candidat 0.9.0)

Le programme reprend le parcours Petits Pas avec RestaurationLocale du socle,
arrêt HTTP, close_all puis renommages avec copie précédente. La PWA accepte
les médias au format existant et conserve ses plafonds mémoire ; ses Workers
séparés et sa confirmation OPFS ne changent pas. Les tables à neutraliser
restent une politique applicative. Lire la section Copies du README et
SAUVEGARDES.md du socle. Aucun modèle, rôle ou migration métier n'est ajouté.


## CHRS25-04 — identité

Personne ajoute une naissance facultative (date ou année seule, précision
explicite) et un numéro de révision. RevisionIdentite conserve les valeurs
avant/après typées. Le service de correction réserve la révision par UPDATE
conditionnel comme première requête SQL d’une transaction, puis valide et écrit
l’identité et son journal ensemble. Une erreur annule aussi la réservation.
Ce service ne touche aucun lien de ménage, suivi ou séjour et n’acquiert donc
pas leurs verrous ; aucun service lié n’acquiert un verrou d’identité ensuite.
Les migrations initiales restent intactes ; les anciennes identités deviennent
simplement des identités sans naissance renseignée, sans attribution de droits.


## CHRS25-05–08 et CHRS26-02

InformationsAccompagnement conserve des versions complètes et typées des champs
facultatifs, sans nouveau moteur générique de champs ni effet sur les prestations.
Les ajouts de versions, les insertions de situations et les actions collectives
prennent le verrou du ménage avant le suivi ou les séjours. Les lots restent
sous une transaction externe ; les services unitaires et leurs journaux sont
réutilisés. Les jetons signés refusent les états périmés.

Une insertion de situation modifie au plus la borne de la précédente et trace
cet avant/après dans CorrectionPeriode ; la suivante reste intacte. Un événement
historique antérieur ne modifie aucune borne de suivi. Les avertissements repas
ne sont pas une contrainte globale d’unicité entre accords. Le résumé imprimable
est une vue de lecture filtrée par les droits existants, sans nouveau moteur PDF.
