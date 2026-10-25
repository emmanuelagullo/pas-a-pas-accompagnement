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

## BD1–BD2 — lecture unifiée, écritures existantes

`personnes.lecture_dossier` prépare les listes et sélections de la fiche
accompagnement, avec préchargement des bénéficiaires et des périodes autorisées.
Les affectations et absences ne sont pas chargées sans leurs droits. Les
formulaires de sélection GET et les liens restent utilisables sans JavaScript.

`personnes.dossier` porte un contexte signé de navigation lié à l’accompagnement,
aux deux sélections et à l’origine connue. `dossier_url` construit uniquement des
routes nommées ; aucune URL de retour fournie par le client n’est acceptée.
Chaque vue ne propage ce contexte qu’après vérification contre sa cible réelle.
Les écritures et leurs verrous/journaux/jetons restent dans les services actuels.
Le contexte de navigation n’est jamais transmis aux arguments des services.
Aucune modification des profils serveur, bureau, PWA ou du socle partagé.

## BD3 — décisions d'accord

`personnes.accords` sépare prolongation d’autorisation et correction d’erreur.
`EvolutionAccord` porte un seul accord typé (repas ou hébergement), le motif,
l’auteur, l’horodatage et les fins avant/après. Les marqueurs d’annulation sont
cohérents par contrainte SQL. Les anciens journaux ne sont pas réécrits.

Les décisions, corrections d’accord, admissions et distributions se sérialisent
sur le même ménage. L’état signé contient la révision d’accord, ses bornes,
bénéficiaires, bornes du suivi et nombre de réalisations. Les corrections
incrémentent aussi la révision pour refuser un ancien formulaire après un
aller-retour de dates. L’annulation refuse toute réalisation liée, même annulée ;
l’admission et la distribution rechargent et refusent un accord annulé dans leur
transaction métier. Aucune lecture préalable seule ne sert de garantie concurrente.

Les statistiques restent fondées sur les réalisations. Un accord annulable n’en
a aucune ; les rapports n’ont donc aucune quantité à retrancher. Le travail du
jour et le résumé courant filtrent les accords de repas annulés. Les listes du
dossier et les détails les conservent avec un état explicite. Les anciennes fins
sont journalisées, sans annoncer une reconstruction des droits à une date passée.


## BD4 — synthèse indépendante des périodes de suivi

`personnes.vues_dossiers` fournit recherche paginée, création explicite et
synthèse au niveau personne/ménage, sans modèle ni migration. Les requêtes de
prestations sont bornées aux périodes visibles puis aux bénéficiaires en vue
personne ; les lieux, absences et informations sociales gardent leurs droits
propres. Les relations affichées sont préchargées, pas une requête par ligne.

Le contexte BD1–BD2 accepte une cible de synthèse signée en plus du parent
accompagnement. Chaque boîte signe le parent réel de sa sélection ; la lecture
vérifie que ce parent appartient au ménage ou compte la personne parmi ses
bénéficiaires. Un contexte spécifique à l’identité/aux notes personne vérifie
la personne cible. Les destinations sont des routes internes connues ; aucun
`next` libre. La recherche, la page, les sélections et le ménage d’origine sont
conservés ; les sélections sont revalidées dans chaque synthèse.

Le JavaScript local annule les recherches précédentes et compare leur numéro
avant d’afficher une réponse ; les anciens résultats sont inertes pendant la
saisie. Aucun CDN ni bibliothèque. Le rendu intégral GET reste fonctionnel sans
JavaScript. L’accueil et ses fragments privés sont marqués no-store.
Les services d’écriture, verrous, révisions et journaux existants sont réutilisés.


## BD5 — amélioration progressive de Form2

`vues_prestations_dossier.nouveau` borne les suivis au ménage ou à la personne,
valide le choix et les bénéficiaires, puis appelle admission.accueillir,
repas.accorder ou repas.accorder_services. Aucun nouveau service d’écriture,
modèle ou droit. Les jetons de concurrence des services sont conservés.

`dossier-en-place.js` réutilise les pages complètes : il extrait leur main dans
la boîte, fixe l’action des formulaires sur leur URL réelle et conserve CSRF et
contexte signé. Les scripts reçus ne sont pas exécutés. Le succès retourne à la
synthèse serveur pour renouveler ensemble sélections et jetons de navigation.
Un seul chargement à la fois ; aucune relance automatique de POST, saisie
conservée sur panne et protection contre la perte d’une saisie modifiée.
Les liens/formulaires gardent leur fonctionnement normal sans ce script.

## BD6 — histoire personnelle et navigation en trois vues

`Accompagnement.fin_prevue` est une prévision exclue ; `fin` garde son sens de
clôture effective. `EvolutionPriseEnCharge` trace les prolongations, sous droit
dédié. `SituationPersonnelle` porte les intervalles par personne et dimension ;
`RevisionSituationPersonnelle` conserve les séries avant/après, auteur et motif.
Les tables sociales historiques, leurs liens et journaux ne sont pas réécrits.
Le lecteur expose leurs divergences plutôt que choisir arbitrairement un suivi.
`CommentaireDossier` ajoute des versions immuables pour une cible exclusive
personne/ménage/prise. Un effacement est une nouvelle version vide motivée.

Toutes les écritures liées gardent l’ordre ménage puis prise. Les écritures
sociales personnelles et commentaires de personne réservent uniquement la
révision personnelle par UPDATE conditionnel : elles ne prennent ensuite aucun
verrou ménage. Les formulaires utilisent des états signés et refusent les états
périmés sans rejouer les POST. L’ajout de membre réserve le ménage avant
l’identité nouvelle et l’appartenance ; le tout est atomique.

Les routes `dossiers:detail` et `dossiers:prise` partagent le lecteur borné par
ménage/bénéficiaire, avec un filtre supplémentaire sur la prise pour Form3.
Les jetons de retour incluent l’écran et le parent ; ils ne remplacent pas les
droits. Les routes historiques restent accessibles aux historiques existants.
Aucune nouvelle dépendance ni changement du format ZIP : les nouvelles tables
et migrations accompagnent les sauvegardes complètes serveur/bureau/PWA.

## Solenne L1 — ouverture et prévisions

`ouverture_prise` réserve les UUID de ménage et de prise dans un contexte signé
lié au dossier. Pour un nouveau ménage, l'INSERT de cet UUID est la première
écriture et précède les validations dans la même transaction ; la contrainte
primaire interdit le rejeu sans verrou personne puis ménage. Pour un ménage
existant, la réservation conditionnelle de sa révision précède les lectures.
Les services CHRS et leurs journaux sont réutilisés ; un échec annule tout.
Les formulaires ouverts avant ce changement doivent être rechargés.

EvolutionPriseEnCharge distingue prolongation et correction ; une nouvelle fin
nulle signifie retrait motivé de prévision. Les anciennes lignes deviennent des
prolongations. La correction dispose d'un droit explicite, non attribué par la
migration. La clôture BD réserve l'état de la prise puis réutilise suivi.clore.
Aucune modification du socle, des formats de copies ou des profils d'exécution.

## Solenne L2a — déclarations individuelles

DeclarationFamiliale est une série typée par personne, pas un moteur de champs
configurables. Les bornes sont dérivées des changements successifs. Le service
famille réserve la révision personnelle avant de relire la série ; il ne prend
ensuite aucun verrou de ménage. RevisionDeclarationFamiliale conserve l'ensemble
avant/après, la nature du changement, son auteur et son motif. Les contrôles
SQL garantissent une date par personne, une ligne ouverte et des périodes positives.
Les anciennes données ne sont pas modifiées par la migration. Les copies complètes
conservent automatiquement ces tables ; aucune dépendance commune n'est ajoutée.
Les rapports et sorties CSV restent soumis aux droits des déclarations et des
historiques. Les cellules textuelles CSV commençant comme une formule sont
neutralisées ; la restitution HTML échappe les déclarations.

## Solenne L3a — coordonnées et chronologie partagée

CoordonneesPersonnelles et son journal restent des tables métier typées,
indépendantes de DeclarationFamiliale. Les deux services utilisent le même petit
algorithme de séries personnelles : réservation avant lecture, bornes dérivées,
refus du changement d'ordre par correction et journal avant/après atomique.
Cette réutilisation ne crée ni champs configurables, ni stockage attribut/valeur,
ni nouveau moteur d'événements. Les wrappers métier contrôlent leurs propres
droits avant la transaction ; le service ne reçoit aucun modèle choisi par le web.
Les réservations communes de personne refusent aussi un ancien formulaire ouvert
avant la modification d'une autre rubrique personnelle. Les lectures BD sont
préchargées par date et par droit ; aucune requête par personne ajoutée au rendu.
La fiche PDF reçoit une projection déjà autorisée, sans requête ni droits implicites
dans le moteur commun. Les règles de chronologie et d'export sont partagées
uniquement entre ces deux usages établis ; aucun changement du wheel.

## Solenne L2b — série datée au niveau ménage

ContactMenage et RevisionContactMenage réutilisent l'algorithme de chronologie
avec une cible ménage explicitement fournie par le service. La réservation CAS
porte sur Menage.revision ; aucune écriture de personne n'est acquise ensuite.
Les journaux des trois usages restent typés et distincts. Les références aux
personnes conservent UUID et libellé au moment de la saisie dans l'avant/après.
Une absence de ligne signifie non renseigné ; une ligne avec contact nul est un
retrait explicite depuis sa date d'effet. Aucune donnée ancienne ni permission
n'est déduite du libellé du ménage, de l'ordre des membres ou de son créateur.

## Solenne L3b — identités stables du répertoire

Partenaire porte l'UUID et une révision ; FichePartenaire et son journal portent
les renseignements datés. La création réserve l'UUID signé par INSERT comme
première requête ; un échec de fiche/journal annule l'identité. La mise à jour
réutilise la chronologie typée en réservant uniquement la révision de partenaire,
sans verrou de personne ou ménage. Le libellé d'index est dérivé de la fiche
applicable aujourd'hui ; les recherches à date utilisent le nom de la fiche.
LieuHebergement.organisme est un lien protégé facultatif, exclusif du libellé
libre pour les nouvelles saisies. Les données anciennes restent inchangées.
Le répertoire ne transforme ni une organisation en personne, ni une fiche
professionnelle en compte utilisateur. Les liens de retour BD restent signés
et ne servent jamais d'autorisation d'accès aux partenaires ou aux dossiers.


## Solenne L4a — professionnels et missions

Intervenant est une identité stable indépendante d'auth.User et de Personne.
FicheIntervenant utilise la chronologie typée et le jeton de révision du répertoire,
sans verrou de ménage ; le lien Partenaire ne copie pas ses coordonnées.
AffectationIntervenant porte un rôle dans une prise et exactement une cible :
professionnel ou organisme. Les mutations réservent ménage puis prise, contrôlent
le jeton BD et écrivent un journal atomique. Les chevauchements d'une même cible
pour un même rôle sont refusés ; les co-intervenants restent possibles.
Les périodes sont semi-ouvertes et bornées par la prise, y compris lorsqu'une
mission n'a pas de fin propre. Une annulation motivée conserve le fait et son
auteur ; les dépendances de dates et consultations l'excluent explicitement.
La présentation lit les fiches professionnelles à la date demandée ; une fiche
absente n'est pas inventée. Les identités de répertoire restent stables et leurs
anciens libellés libres ne sont jamais rapprochés automatiquement.


## Saisie typée et propositions partagées

champs_saisie adapte les formulaires métier sans modifier leurs règles de
validation ni leurs cibles. Deux bases Django et une adaptation idempotente à
l'affichage couvrent les champs ajoutés dynamiquement ; aucun monkey patch global.
Les contrôles d'authentification gardent leur rendu indépendant. Les listes de
propositions ne constituent ni un moteur de formulaires ni une table d'attributs
de dossier : seules sept rubriques textuelles nommées sont autorisées.
PropositionSaisie et son journal ne stockent aucun rapprochement automatique avec
les valeurs individuelles ; désactiver une proposition ne corrige aucun dossier.
La réservation CAS et le journal sont atomiques ; les droits restent volontaires.
La recherche transverse des missions recoupe la fiche d'organisme du professionnel
à date, et borne toute mission par sa prise en charge.


La durée civile est une aide de formulaire, jamais une colonne redondante :
seules les dates validées vont aux services. Les formulaires compatibles déclarent
explicitement leur couple début/fin ; la création de prise vise sa fin prévue,
pas sa clôture. Le serveur recalcule sans JS selon le mode choisi, vérifie le
calendrier puis conserve toutes les validations et réservations métier existantes.
Le script utilise des jours UTC pour éviter les écarts de changement d'heure.
Les dates incohérentes ne sont jamais inversées automatiquement.


## Identité déclarée et relations indépendantes des prises

ComplementIdentite est une série personnelle typée, avec nationalites comme
collection JSON spécifique de libellés (pas un moteur d'attributs). L'apatridie
est une déclaration nullable séparée ; ni nationalité ni sexe ne sont déduits.
La chronologie et son journal réutilisent series_personnelles sous réservation
personnelle. Les valeurs datées ne réécrivent pas le nom/la naissance de Personne.

RelationPersonnelle porte une paire canonique ordonnée de UUID et un sens
explicite ; le rôle présenté est relatif à la personne consultée. Les mutations
réservent les deux personnes dans l'ordre des UUID, avec le CAS de la personne
portant le formulaire, et invalident la révision sociale de l'autre. Tous les
contrôles de chevauchement et journaux ont lieu sous ces réservations. Aucun
verrou de ménage, prise ou répertoire n'est acquis ensuite. Les lectures depuis
les deux extrémités partagent le même fait. Les filiations inverses superposées
sur une même paire sont refusées ; aucune généalogie ni habilitation légale n'est
inférée. Une erreur de cible s'annule, la paire n'est jamais réaffectée.

Une succession ferme l'ancien lien et ouvre le nouveau atomiquement. La fin
réelle conserve les autres valeurs ; correction et annulation sont motivées.
Les liens survivent aux changements de ménage et aux clôtures de prise.
Le résumé à l'entrée est une restitution à date, pas un document figé.

## Dossier personnel complet — fin du méta-lot A

Les ressources, dettes, pièces administratives, couvertures et protections sont
des déclarations personnelles datées, indépendantes des prises en charge. Les
schémas sont fixes et typés ; le registre Python ne définit aucun champ dynamique.
Plusieurs postes coexistent. Une absence ou une situation inconnue explicite se
distingue d'une rubrique jamais renseignée. La fin d'effet est exclusive ; une
échéance annoncée n'expire jamais automatiquement une déclaration.

Chaque rubrique distingue ajout, insertion rétroactive, changement, correction
motivée, fin effective et annulation motivée. Une déclaration globale d'absence
ou d'inconnu demande confirmation avant de terminer les postes concernés. Les
services réservent la personne par CAS avant lecture, sans verrou ménage ensuite ;
les écritures et journaux avant/après sont atomiques. Les droits de lecture,
ajout, modification et annulation restent explicites. Aucun droit n'est attribué
par les migrations.

La situation administrative conserve identifiants textuels, qualification, séjour
déclaré et origines des périodes sans emploi/domicile, avec précision explicite.
Les durées historiques seulement déclarées restent textuelles ; aucune date
précise n'en est inventée. Une protection distingue portée déclarée, personne ou
professionnel ou organisme désigné, et interlocuteur ; aucune mission, relation,
appartenance ou qualité juridique n'est déduite.

La BD expose deux entrées courtes : Ressources et dettes ; Administration et
droits. Les droits sont consultés rubrique par rubrique sur la même page. La
date, la cible et le retour de recherche sont conservés. Les déclarations de
ressources projettent la synthèse sociale lorsque leurs droits le permettent,
sans écraser les anciennes situations, dont les divergences restent lisibles.
Les propositions de saisie sont volontaires et journalisées ; elles ne collectent
ni identifiants ni montants de dossier. Les imprimés et CSV réutilisent la sélection
datée du rapport.

## Demandes, orientations et projet longitudinal — méta-lot B

DemandeAccueil, OrientationParcours, ObjectifParcours et RepereDossier ont une
identité stable, une cible personne ou ménage exclusive et des bénéficiaires
explicitement choisis. Une erreur de cible s'annule et se ressaisit ; aucune
appartenance, personne ou prestation n'est créée depuis une démarche. Les quatre
séries de versions sont des schémas Django fixes, pas des attributs configurables.
Dates d'effet et fins exclues permettent les changements et insertions antérieures ;
une correction motivée ne traverse pas une autre version. Les échéances et dates
annoncées peuvent être futures et ne changent aucun état automatiquement.

Les journaux avant/après sont atomiques. Création sous CAS du dossier ; mutations
sous CAS de l'élément. Les permissions sont chargées avant la transaction. La
liaison demande/prise réserve le ménage puis la demande ; elle exige une acceptation
à l'admission et actuellement, les mêmes bénéficiaires et le même ménage lorsqu'il
est la cible. L'ouverture existante crée/rattache explicitement le ménage et la
prise, puis lie la demande dans la même transaction : un conflit annule tout.
Retirer une liaison erronée est motivé et conserve la prise en charge. Aucun
séjour, accord ou arrivée d'hébergement n'en découle.

Une orientation a sa destination, son organisme/interlocuteur, une prévision et
un résultat effectif distincts. Plusieurs orientations peuvent coexister. Un
objectif est personnel ou collectif, thématisé, daté et suivi par état/horizon ;
son récit enrichi et ses versions sont conservés. La prise de contexte est un
repère d'origine, sans borne de fin imposée à la démarche longitudinale. Les
anciens récits de projet/bilans ne sont ni parsés ni remplacés. Le repère de suivi
actif/veille/terminé ne bloque aucune correction, ouverture ou prestation.

L'activité CHRS/urgence/autre est une information versionnée de la prise ; vide
signifie non renseigné. Une activité demandée n'est pas copiée silencieusement
dans cette information. Un changement d'activité ne vaut pas sortie définitive
du dossier. Les anciennes informations sont conservées sans activité inventée.

La BD garde une ligne d'accès au parcours et un aperçu borné des demandes en
attente/acceptées sans prise. La même page sélectionne demandes, orientations,
objectifs ou suivi. Les actions portent sur l'élément, les précisions facultatives
occupent un seul groupe, et les retours conservent cible/date/recherche/prise.
Les coordonnées des répertoires sont restituées à la date choisie sous leurs droits.
Les rapports utilisent une version applicable par élément, des filtres structurés
et un CSV de toute la sélection ; les anciens motifs d'entrée/sortie ont leur
rapport propre sur la dernière information versionnée, explicitement distinct
d'une restitution historique à date d'effet.

## Prestations et continuité individuelle — méta-lot C

TypeAide définit un catalogue simple de quatre natures fixes : transport, bon
alimentaire, produits alimentaires et accueil de jour. Chaque type indique
libellé, unité, fractionnement éventuel, explication et disponibilité. Les
modifications sont motivées et journalisées ; chaque AccordAide conserve une
photographie de la nature/libellé/unité/explication/fractionnement de son type.
Modifier le catalogue ne change aucun accord existant. Aucun tarif, réseau ou
nombre de trajets n'est déduit de ces titres. Les sigles historiques TAM1/3/10
sont des cartes de 1/3/10 voyages dans les impressions Java ; les cartes remises
ne sont pas des voyages effectués.

AccordAide porte période, bénéficiaires explicites, plafond global facultatif,
prestataire/financeur annoncés et source. La valeur faciale d'un bon est nullable,
avec devise ; ce n'est ni un tarif facturé ni une imputation. RemiseAide porte
une quantité globale pour sa propre sélection de bénéficiaires, une date réelle
et une source. Les remises actives respectent le plafond s'il est chiffré, les
périodes d'accord et de prise, les unités entières/fractionnables et le refus
des réalisations futures. Vide n'est pas zéro. Une correction de personnes
exige annulation/nouvelle remise ; corriger quantité/date conserve les cibles.
Les annulations ne suppriment aucune ligne. Un accord ayant eu une remise est
conservé, même si les remises ont été annulées.

UsageAide est un constat déclaré versionné, distinct de la remise : quantité
inconnue, zéro explicitement non utilisé, utilisation partielle ou complète.
Il ne consomme pas une seconde fois le plafond. Les révisions avant/après
conservent quantités, unités, sources, bénéficiaires et acteurs. Écritures
liées : ménage avant CAS de prise/accord ; catalogue : CAS propre. Les plafonds
restent vérifiés sous réservation et transaction unique.

Les repas existants restent des repas, avec petit déjeuner/déjeuner/dîner.
Jours autorisés facultatifs (vide : tous, compatibilité historique), validation
à la distribution et sélection dans le travail du jour ; synthèse des jours
autorisés par union civile. Catégorie déclarée facultative par distribution,
sans déduction tarifaire depuis la naissance. Corrections de quantité/catégorie
et de jours/prestataire motivées et journalisées ; des jours corrigés ne peuvent
exclure une distribution active. Un changement réel de service utilise une
nouvelle période, pas une correction d'erreur.

Un ancien séjour collectif ouvert peut être continué individuellement à une
date explicite après son admission et les périodes déjà datées. La période
commune s'arrête à cette date ; un fragment par personne continue le même accord
avec lieu et absence ouverts recopiés. ContinuiteSejour garde l'avant/après et
la filiation des fragments. Aucun ancien séjour n'est converti par migration.
Ce n'est pas une sortie suivie de nouvelles admissions : les compteurs historiques
regroupent l'épisode initial, dont la sortie est celle du dernier fragment clos.
Les nuitées et absences utilisent les fragments non chevauchants. Le détail
individuel montre les dates de chaque départ et ses nuits ; ses lignes ne sont
pas des admissions. Les corrections ne déplacent pas isolément la coupure.

Les lieux ont un parent/type facultatifs, sans imposer quatre niveaux. Un
changement effectif reste une affectation datée. Les corrections de libellé ou
de rattachement ont un journal ; leurs rares mutations réservent le petit
répertoire dans l'ordre des identifiants avant de revérifier l'absence de boucle.

Form3 garde les prestations regroupées ; les aides complémentaires ont leurs
autorisations et actions directes. Le travail du jour conserve date et retour
après réalisation. Les rapports distinguent autorisations chevauchantes non
proratisées, remises dans la période, repas et détail individuel d'hébergement.
Les quantités sont séparées par nature/type/libellé/unité/catégorie, sans somme
de bons, kg, cartes, repas ou euros. Les PDF serveur/bureau et texte PWA utilisent
le socle existant, sans ressources externes ; ce sont des restitutions, pas des
documents émis numérotés/figés ni une facturation.

## Financements de prestations (D)

`FinancementPrestation` cible exactement un accord hébergement/repas/aide, sans
GenericForeignKey ni nouvelle notion de dossier. Sous verrou ménage, un jeton
signé vérifie cible/période/bénéficiaires et révision du financement. Les versions
complètes `VersionFinancement`, `LigneCout` et `ImputationFinancement` sont écrites
atomiquement, sans droits de modification/suppression de version. Les écritures
ne modifient aucune prestation. Une nouvelle décision et une correction sont
distinguées dans la version avec motif. Les trois phases ne s'additionnent pas.

`TarifPrestation` sérialise ses nouvelles `VersionTarif` par CAS. À une date,
prendre d'abord la dernière date d'effet puis sa dernière correction ; une fin
corrigée ne ressuscite pas l'ancienne version. Un prix futur ne masque pas un
prix antérieur. Un nouveau prix prend une nouvelle date ; une correction porte
sur une date existante. Une ligne référencée conserve libellé/unité/catégorie/prix
et exige la même devise et le même prestataire éventuel. Les calculs précédents
ne sont jamais recalculés lors d'une correction du catalogue.

`DocumentFinancement` utilise sa clé séquentielle pour un numéro stable, conserve
un contenu JSON de restitution (gabarit version 1), titre/lignes textuelles et
SHA-256 canonique. Les données de recherche restent dans les modèles typés,
le JSON sert uniquement à la réédition. `AnnulationDocument` conserve motif/auteur/
horodatage sans modifier le contenu émis. Un remplacement exige l'annulation,
la même prestation et un lien unique. Émission/annulation consomment aussi le
jeton du financement. La réédition n'interroge pas les répertoires courants.
Les PDF serveur/bureau/PWA réutilisent les moteurs communs, sans nouvelle
bibliothèque, configuration ou ressource réseau.

Un prix déjà utilisé peut être conservé lors d’une correction de quantité dans
la même phase et à la même date de calcul, même si le catalogue a été corrigé
depuis ; il reste explicitement lié à sa version de tarif d’origine.

## 115, relève et exploration (E)

Appel115 est indépendant des périodes de prestation. VersionAppel115 porte un
événement daté, heure facultative, personnes explicitement concernées et valeurs
nominales multiples validées. CAS du parent avant écriture ; anciennes versions
conservées. Une suite ne déplace pas une date/heure déjà connue et ne retire pas
une personne identifiée ; une correction motivée le peut si les liens explicites
restent cohérents. LienAppelParcours référence une demande ou une prise existante,
avec annulation séparée ; aucune écriture d'admission implicite. Les écritures
ne prennent pas de verrou ménage après celui d'appel : elles ne modifient aucun
objet lié. Les droits des cibles et répertoires sont contrôlés avant restitution,
y compris pour une ancienne version et son PDF. Téléphone et libellés ne servent
jamais de clés de rapprochement.

Transmission/NotePartagee reçoivent une date_fait nullable, sans inventer de dates
pour l'existant. RevisionContribution conserve avant/après de cette date avec les
textes enrichis ; le jeton et le CAS incluent la date. AnnulationContribution
conserve le statut hors du contenu. Une note n'a toujours qu'une cible, contrainte
SQL étendue aux trois accords. ActionRelais reçoit un contexte facultatif,
révision CAS et RevisionActionRelais. Réalisation et annulation ont des états
séparés ; les historiques précisent aussi la réouverture. Les anciens POST de
clôture sans jeton restent idempotents et conditionnels ; les formulaires livrés
transmettent le jeton de révision. Les journaux sont atomiques avec les écritures.

Exploration utilise un registre fermé de populations/champs des modèles métier,
jamais un chemin ORM ou du SQL transmis par le client. Les données personnelles
utiles sont chargées par domaine à la référence, selon droits ; identifiants
administratifs et textes libres ne deviennent pas des axes de regroupement.
Les conditions personnelles multiples et leurs croisements s'évaluent sur le
même bénéficiaire. Les cellules dédoublonnent les objets et participants ; le
total global est recalculé sur la sélection. Unités/devises/périodicités/phases
sont préservées. Les valeurs inconnues sont distinctes de zéro. Les épisodes de
séjour utilisent la continuité déjà livrée ; seuls leurs fragments produisent
les nuitées de personnes. Les champs de date de saisie et date du fait sont séparés.

Les modèles d'exploration réutilisent ModeleRapport, privés par auteur, avec
schema=1/exploration=true et paramètres validés seulement. Une version inconnue
est refusée ; les modèles historiques gardent leur parcours. Toute lecture est
recalculée et revalidée sous les droits du compte courant. Les limites d'objets,
cellules, filtres et classes sont explicites ; aucun total de résultat tronqué.
Les PDF textuels de restitution réutilisent les moteurs existants et refusent
les ressources externes. La recette native accorde 120 s à chaque ouverture,
migrations/scénario compris ; le lanceur journalise séparément ces deux phases
uniquement en mode sans fenêtre. Aucun délai de fonctionnement n'est ajouté.


### Consolidation F : documents et déclarations

PieceDossier porte exactement une cible personne/ménage/prise en charge.
VersionPieceDossier conserve titre, date du document nullable, provenance,
nom, octets, taille et SHA-256. Les fichiers sont opaques, limités à 5 Mio,
sans chemin fourni, aperçu HTML ou lancement externe. Un BinaryField permet
une version atomique avec ses métadonnées, sans nouveau protocole de médias
ou nettoyage de fichiers orphelins après rollback. Les octets ne sont chargés
que pour la version téléchargée ; listes et historiques les différèrent.
Le parent est réservé par le CAS BD existant ; pour une prise, le ménage
précède cette réservation. Annulation distincte, versions conservées. Les
droits restent volontaires et les téléchargements privés sans cache.

BesoinAccueil et AntecedentInstitutionnel étendent FaitPersonnelDate et
JournalPersonnel dans le registre fermé dossier_complet. Ce ne sont ni des
attributs configurables, ni un diagnostic inféré. Les anciennes chaînes et
notes ne sont pas analysées pour créer des déclarations. Les copies conservent
les octets et journaux sans nouveau format. Aucun nouveau droit en migration.

Le registre d'exploration reste fermé. Les situations longitudinales et les
missions ne se déduisent pas d'une appartenance : bénéficiaires explicites
pour les premières, prise exacte pour les secondes. Chaque niveau d'axe
garde la carte de la même personne ; les totaux sont recalculés sur les UUID.
La borne de 2 000 cellules porte sur toutes les mesures réunies. Les dates
personnelles par objet sont regroupées par référence (366 références au plus).
