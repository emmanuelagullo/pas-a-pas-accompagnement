# Établissement Les Passerelles — démonstration métier fictive

Jeu mono-espace, sans table d’établissement : « Établissement Les Passerelles » est un cadre
narratif, pas un cloisonnement entre CHRS. Données fictives exclusivement.

| Personnage | Parcours |
| --- | --- |
| Alex | Accompagnement ouvert sans hébergement ; déjeuner accordé, deux distributions passées. |
| Samira, Lina, Adam | Trois fiches et trois bénéficiaires explicites du suivi, des repas et du séjour ; unité interne puis lieu partenaire ; absence close de deux jours, séjour ouvert. |
| Thomas | Séjour terminé, accompagnement ouvert ; logement devenu autonome, formation, ressources déclarées, événement et bilan. |

Nadia illustre l’accompagnement social, Rémi l’accueil/hébergement, Camille la
restauration. Les comptes publics `nadia`, `remi`, `camille` et l’accès historique
`essai` ont les mêmes droits explicites CHRS1–7 et création de personnes, sans
suppression ni administration. Ce ne sont pas des habilitations par service.
Les écritures initiales passent par les services métier et leurs journaux.
Les enfants ont des fiches et prestations explicites, avec des naissances explicitement fictives, sans
filiation ni représentation légale déduite du ménage.

## Essayer et retrouver son espace habituel

### Dans la PWA

Choisir **Essayer avec Établissement Les Passerelles**, même si l’espace habituel existe déjà
ou si aucun compte n’y a encore été créé. Au premier accès, le jeu est généré
dans un stockage distinct. Un bandeau **Espace d’essai Établissement Les Passerelles** et les
comptes du jeu de départ sont affichés. Mot de passe public :
`Demonstration-fictive-2026!`.

**Revenir à mon espace habituel** recharge les données habituelles, sans
restauration ni fusion. Une ouverture ultérieure de l’essai retrouve les
modifications déjà enregistrées : aucune remise à zéro à l’ouverture ou à la
mise à jour. Terminer ses saisies avant de changer. Une restauration en cours
ou une copie en attente de confirmation bloque le lien de changement ; annuler
ou terminer d’abord l’opération. Fermer les autres onglets : le verrou reste
commun aux deux espaces. Les espaces partagent le quota et le profil navigateur ;
effacer les données du site peut supprimer les deux.

L’adresse `essai.html` redirige vers `?essai=oui`, comme dans Petits Pas.
Le Service Worker, les ressources et les routes Django restent communs. Le
sélecteur `configurerEspace` du stockage pas-communs conserve les noms historiques
de l’espace habituel et utilise le suffixe `-essai` pour le second espace.
Exports, restauration, secours et mises à jour sélectionnent le même espace.

### Dans les programmes Linux/Windows

Choisir **Essayer avec Établissement Les Passerelles**, puis **Fermer et ouvrir l’autre espace**.
La fenêtre ferme et le programme redémarre dans un dossier `essai-fictif`, à
côté du paquet par défaut du produit. Le dossier habituel, même personnalisé,
est conservé. Le bandeau et les comptes publics signalent l’espace d’essai.
Le retour utilise **Revenir à mon espace habituel**, puis le même bouton.

Depuis les sources, avec les dépendances de `requirements-bureau.txt` :

```sh
python scripts/lancer-local.py --paquet /chemin/absolu/habituel --essai --sans-fenetre
# Après fermeture, revenir avec le même dossier habituel :
python scripts/lancer-local.py --paquet /chemin/absolu/habituel --sans-fenetre
```

`--essai` ne copie pas le dossier passé à `--paquet` : il sélectionne le dossier
d’essai séparé. Le chemin habituel est conservé au redémarrage de la fenêtre,
y compris lorsqu’il venait de `ACCOMPAGNEMENT_DONNEES`. Un lien symbolique,
un dossier d’essai occupé sans base ou un paquet incomplet est refusé. Aucun
espace existant n’est remplacé. Le chemin habituel est aussi conservé lors d’un redémarrage après restauration.
Le changement est bloqué pendant une préparation
de restauration ou un remplacement confirmé. Dans le navigateur externe du
mode sans fenêtre, fermer puis relancer avec ou sans `--essai`.

### Sur le serveur jetable

Le démarrage existant `bash start-render.sh` prépare le même jeu et les mêmes
comptes publics. Les modifications sont partagées entre visiteurs et perdues
à la recréation du service. Aucun changement de commande ou de profil serveur
persistant : le serveur réseau n’expose pas le sélecteur de dossiers locaux.

## Lecture de la trajectoire sociale

Chez Thomas, la page **Trajectoire d’accompagnement** met en regard les
situations datées au début et à la fin de la période sélectionnée et les
éléments chronologiques (événement, bilan, hébergement). Cette lecture ne
produit aucun score, ne déduit pas une situation de la sortie d’hébergement
et distingue les informations absentes des valeurs renseignées. Voir
`site/content/guide/trajectoire-sociale.md`.

## Découverte en cinq minutes

Depuis l’accueil, ouvrir **Découvrir le scénario fictif Établissement Les Passerelles** :
ménage de Samira → accord et réalisation chez Alex → distribution d’un déjeuner
aujourd’hui → affectations et absence de Samira → situation datée de Thomas.
Un événement ou bilan fictif reste à ajouter chez Thomas. Le guide ne charge
ni ne remplace de données et conserve ses contrôles de permissions.

## Compatibilité avec le premier patch déjà appliqué

Le premier patch pouvait charger Établissement Les Passerelles dans l’espace habituel lors
de la création du compte. Ces espaces, leurs identifiants privés, leurs droits
et leurs modifications sont **conservés sans migration ni déplacement**.
Le nouveau bouton ouvre un autre espace d’essai ; le retour retrouve exactement
l’ancien espace habituel, même s’il contient déjà Établissement Les Passerelles.

La case de chargement initial est retirée. Le premier compte habituel garde
les droits lecture/création de personnes antérieurs ; il ne reçoit plus CHRS1–7
par cette case. Un ancien POST contenant ce champ ne charge rien. Les permissions
des comptes existants ne sont pas retirées. Aucun reset ou nettoyage implicite
n’est ajouté. Une sauvegarde privée reste le moyen de conserver les essais.

## Génération, dates et copies

Le générateur `personnes/demonstration.py` est partagé par le serveur jetable
et la première ouverture de l’essai distinct. Comme Petits Pas, le parcours
sépare les espaces et conserve les essais ; ici, le contenu initial est généré
sur place, plutôt que restauré depuis un ZIP embarqué. Cela garde des dates
récentes et ne distribue ni base privée ni clé ni session. Aucun mécanisme de
sauvegarde/restauration n’est dupliqué ou ajouté.

J est la date civile locale de génération. Le suivi commence à J−60 ; la famille
est admise à J−39, change de lieu à J−15, est absente de J−7 inclus à J−5 exclu ;
Thomas sort à J−10. Les accords d’Alex et de la famille restent ouverts. Le repas
d’Alex à J est laissé libre. Sur le serveur partagé, vérifier avant de le saisir.

Contenu et décalages sont reproductibles ; UUID, horodatages techniques, clés
et mots de passe hachés restent propres à chaque espace. Les dates sont fixées
une fois et ne sont jamais redatées à l’ouverture ou à la restauration. Le jeu
ne contient aucun dossier réel et ne mesure pas la consommation physique des repas.

Une sauvegarde complète reste privée : elle contient comptes et secrets, y
compris dans l’espace d’essai. Une restauration remplace uniquement l’espace
sélectionné, avec les confirmations et l’état précédent habituels. Les comptes
du ZIP restauré remplacent ceux de cet espace ; les identifiants initiaux peuvent
alors ne plus s’appliquer. Aucune donnée n’est fusionnée entre les deux espaces.
Les limites PWA de 64 Mio et les refus des archives Petits Pas restent inchangés.

## Vérifications

```sh
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
python scripts/verifier-demonstration.py
python scripts/exercer-deploiement.py ephemere --render
node scripts/verifier-pwa-pyodide.mjs
# Après construction du bundle --test :
PWA_BUNDLE=dist/pwa-tests PWA_TEST_HTTPS=oui node scripts/verifier-pwa.cjs
PWA_BUNDLE=dist/pwa-tests PWA_BASE_PATH=/ node scripts/verifier-pwa.cjs
git diff --check
```

Les tests du lanceur vérifient les chemins séparés, le retour au dossier
personnalisé et le refus des liens symboliques. Le banc natif ouvre vraiment
le programme sans fenêtre, passe de l’essai au dossier habituel personnalisé,
rouvre l’essai modifié sans reset et vérifie que le dossier habituel est intact.
Il conserve aussi l’aller-retour de sauvegarde/restauration du jeu complet.
Pyodide exerce les comptes, droits, réouverture et copie native du jeu d’essai.
Chromium exerce les allers-retours hors ligne dans le même profil navigateur,
la conservation de chaque espace et les parcours de copie existants.
La qualification des fenêtres WebKit/WebView2 et du setup Windows reste à
confirmer en CI et sur les postes cibles ; CPython ne la remplace pas.

### Résultats de cette livraison (20 octobre 2026)

- Référence examinée : Petits Pas `c0ec188`, notamment le lanceur, le sélecteur
  de fenêtre, les coques/Workers PWA et le guide « Essayer avec l’école fictive ».
- Suites Django 5.2.18 et 6.1.2 : 107 tests chacune, dont 3 ignorés pour PostgreSQL, contrôles Django,
  absence de migration nouvelle et diff sans erreur.
- Banc natif : sauvegarde/restauration, vrai serveur sans fenêtre, essais conservés,
  chemin habituel personnalisé, commandes de fenêtre simulées et refus pendant
  préparation/confirmation d’une restauration. Serveur jetable HTTP également validé.
- Construction PWA et vrais runtimes Pyodide/Python 3.14.2 : essai distinct,
  identités et droits, réouverture et copies natives, anciennes sauvegardes reprises.
- Restent à confirmer en CI : parcours Chromium aux deux chemins, constructions
  Linux/Windows et Hugo ; puis essai interactif WebKit/WebView2. L’installation
  Chromium et Headless Shell a échoué ici (archives téléchargées incomplètes).

## Parcours quotidien et corrections (CHRS5–7)

Les jeux nouvellement créés accordent CHRS1–7 aux quatre comptes, toujours sans
rôle professionnel distinct. Les espaces déjà générés sont préservés : leurs
droits ne changent pas à l’ouverture. Pour étendre volontairement un compte
existant, utiliser autoriser_chrs7 au terminal. Aucun reset n’est nécessaire.
La fiche personne conduit à l’accompagnement. Le travail du jour permet la
saisie explicite des repas. Les erreurs de dates ou de texte se corrigent avec
motif et conservation de l’avant/après ; ne pas utiliser la suppression.

## CHRS11 — Trajectoire datée

Depuis « Situation et parcours sociaux », ouvrir « Explorer la trajectoire ».
La chronologie est filtrable par bénéficiaire et par dates d'effet inclusives.
Elle juxtapose les situations déclarées, événements, bilans de ménage, repas
réalisés ou annulés et admissions/sorties, selon les droits de lecture.
Elle ne produit ni score ni déduction automatique sur le progrès social.
Les bilans de ménage sont masqués dans la sélection d'une personne.

## Relève quotidienne (CHRS12)

Parcours à essayer avec les comptes fictifs habilités : ouvrir **Travail du
jour**, consulter les transmissions, vérifier les fins proches d'accords et
les repas, puis créer volontairement une action de relève si une intervention
reste à effectuer. Revenir avec un autre compte disposant du droit de clôture
pour marquer l'action comme réalisée. Une transmission informative ne crée
aucune action. Les notes sociales de Thomas ne sont pas reprises dans la
liste transversale : leur consultation reste soumise aux droits du dossier.


## Qualification transversale CHRS-Q — relève et date métier

Sur « Travail du jour », choisir une date ancienne : les séjours, repas et accords
sont affichés à cette date ; la **relève actuelle** conserve les transmissions
récentes et les actions encore ouvertes. Ces informations ne constituent pas
une photographie historique. Les actions sont réparties entre *en retard*,
*à traiter aujourd’hui* et *à venir ou sans échéance* ; l'échéance est
facultative et aucune tâche n'est déduite d'une transmission.

Parcours de recette avec des profils fictifs distincts :

1. **Nuit** : ouvrir le travail du jour, consulter le cahier si autorisé,
   transmettre une information factuelle sans données sociales sensibles.
2. **Journée** : consulter la relève, créer explicitement une action à reprendre,
   puis la marquer réalisée avec le droit de modification.
3. **Référent social** : consulter la trajectoire et les bilans avec les droits
   correspondants ; vérifier séparément les chiffres d'activité.
4. **Contrôle négatif** : retirer `view_transmission` et `view_actionrelais` ;
   vérifier l'absence des textes dans la page et le refus des URLs dédiées.
5. **Date historique** : vérifier que le changement de date métier ne transforme
   pas la relève actuelle en historique de cette date.

Les captures Hugo ne constituent pas à elles seules un test de confidentialité :
la recette doit aussi vérifier les réponses HTTP et les textes absents.

## Qualification ergonomique CHRS13 — captures et parcours

La CI `captures-demonstration` ouvre le serveur jetable Établissement Les Passerelles et
contrôle, dans Chromium, les titres de la relève, la séparation avec la date
métier et les accès à la transmission et aux statistiques. Elle produit
`travail-du-jour.png` en complément du cahier de liaison et des statistiques.
La galerie Hugo affiche ces captures fictives.

Cette vérification confirme la présence et la navigation des repères, **pas**
leur facilité d'utilisation par un veilleur ni les droits de profils distincts :
les comptes de démonstration partagent actuellement les mêmes permissions.
Le jeu fictif nouvellement généré reçoit explicitement les droits de relève ;
les comptes et espaces existants ne sont pas modifiés.
Une recette humaine sur petit écran, avec les profils réels prévus, reste
nécessaire avant de qualifier l'ergonomie ou la confidentialité en situation.

## CHRS14 — Qualification par profils fictifs (recette)

Les trois profils ci-dessous sont **des jeux de droits de test**, pas des rôles
créés en production ni des recommandations universelles d'habilitation.
L'établissement doit définir ses propres responsabilités avant toute donnée réelle.

| Profil fictif | Parcours attendu | Refus à vérifier |
| --- | --- | --- |
| Veilleur | Travail du jour → cahier de liaison → transmission → action de relève | Trajectoire sociale et statistiques |
| Équipe de journée | Travail du jour → transmissions en lecture → action ouverte → clôture | Saisie de transmission/action sans droit de création, trajectoire sociale |
| Référent social | Accompagnement → trajectoire sociale | Cahier de liaison, actions de relève et statistiques sans autorisation spécifique |

La commande `python3 manage.py test personnes.tests_profils` contrôle les réponses
HTTP et certaines écritures, avec permissions explicites et données fictives.
Elle ne remplace **ni** une vérification humaine de l'ergonomie **ni** une
validation juridique des habilitations. Les informations libres dans les
transmissions et actions de relève sont accessibles à tous les titulaires du
droit de lecture correspondant : ne pas y consigner de détails sociaux sensibles.

### Recette humaine à réaliser avec Établissement Les Passerelles

Pour chaque profil, chronométrer et compter les changements d'écran nécessaires
pour accomplir la tâche ci-dessus ; noter les libellés ambigus, retours perdus,
contrôles proposés sans droit, informations manquantes et informations affichées
sans nécessité. Sur petit écran, vérifier notamment le passage entre la relève
actuelle et la situation à une date choisie. Ne corriger que les difficultés
observées ; ne pas inventer un système de rôles ou de tâches supplémentaire.

### CHRS14-02 — Recette navigateur par permissions

Le job `captures-demonstration` exécute aussi `personnes.qualification_navigateur`
avec Chromium et un serveur Django jetable. Trois profils fictifs sont recréés
indépendamment : veilleur (lecture et saisie de transmission), équipe de journée
(lecture et clôture d'actions), référent social (trajectoire sans accès implicite
à la relève). Les contrôles portent sur les liens réellement rendus, les
retours de navigation et les refus HTTP directs. Le format mobile (390 px) est
utilisé pour détecter les problèmes grossiers de navigation ; **ce n'est pas**
une validation ergonomique par des professionnels.

Pour lancer cette recette avec Playwright/Chromium installés :

```sh
python3 manage.py test personnes.qualification_navigateur --noinput
```

Cette recette ne crée aucun compte dans la base persistante : Django utilise
sa base de test et les données sont fictives. Elle complète, sans remplacer,
les tests de permissions `personnes.tests_profils` et la recette humaine.

## Qualification CHRS15 — Explorations statistiques

Le parcours navigateur de `scripts/capturer-site-chrs.py` ouvre les deux explorations
sur la période J−60 à J+1, sélectionne le regroupement par catégorie,
vérifie les colonnes du tableau et le téléchargement CSV, puis génère les
captures `exploration-repas.png` et `exploration-hebergement.png`.
Le site Hugo reprend ces captures. Les tests Django vérifient les agrégats
du scénario, indépendamment des dates civiles et des UUID. Les nuitées
d'affectation restent théoriques, et les exports ne sont pas nominatifs.

### Modèles personnels de rapports (CHRS16)

Dans la démonstration jetable Établissement Les Passerelles, le parcours Chromium ouvre les statistiques des repas sur le mois courant, enregistre le modèle personnel « Repas du mois — démonstration », le rouvre et vérifie que la période relative est conservée et que le CSV reste disponible. La capture `modele-rapport.png` est produite dans les artefacts CI, sans ajout automatique à la galerie Hugo. Le modèle n’est créé que dans la base fictive jetable.

## BD3 — décisions sur les accords

Les nouveaux jeux attribuent volontairement les décisions BD3 aux comptes fictifs.
Les anciens jeux sont conservés, sans extension automatique des permissions ;
`python3 manage.py autoriser_bd3 IDENTIFIANT` permet une attribution explicite.
Les accords ouverts du jeu initial ne se prolongent pas : pour essayer une
prolongation, créer un accord fictif avec une fin prévue. Pour essayer une
annulation, utiliser un accord sans admission ni distribution. Vérifier ensuite
sa présence dans l’historique et son absence des propositions de distribution.
Le parcours PWA CHRS5–7 reste indépendant de ces nouvelles décisions.


## Scénario enrichi — méta-lot A, fondations

Les **jeux nouvellement générés** contiennent 36 personnes, 18 ménages et 51
prises en charge (12 ouvertes, 39 closes). Les anciens espaces d'essai,
leurs droits et leurs modifications sont conservés sans enrichissement implicite.
La page Découvrir Établissement Les Passerelles donne les parcours détaillés dans la BD.

| Cas | Usage à essayer |
| --- | --- |
| Samira, Lina, Adam | Dates de naissance fictives ; contact de ménage explicite ; relais de référent et suivi extérieur ; prestations familiales conservées |
| Thomas | Versions d'adresse, correction motivée d'un complément, professionnel référent, logement autonome après séjour |
| Alex | Accompagnement sans hébergement ; orientation saisie par erreur puis annulée ; repas du jour toujours libre |
| Noor | Retour après ancienne prise close ; deux co-référents ; trois petits déjeuners réalisés |
| Inès | Dossier individuel sans ménage ni prise en charge ; naissance inconnue ; tester le premier accueil court |
| Gabriel et Éva | Ménage avec deux bénéficiaires ; séjour terminé dans un lieu rattaché au répertoire ; aucune parenté déduite |
| Yannis | Année de naissance estimée seule ; prise close sans hébergement |

Trois organismes, trois identités professionnelles et des propositions de saisie
fictives complètent le jeu. Les professionnels ne sont pas les comptes connectés.
Aucune donnée personnelle de dossier ne nourrit automatiquement les propositions.
Les comptes publics ne reçoivent ces droits que lors de la génération neuve.

Contrat sur J−60 inclus à J+1 exclu : 18 ménages et 18 prises dans la fenêtre,
trois séjours, six bénéficiaires de séjours, trois admissions et deux sorties,
**215 nuitées théoriques, 209 hors absences déclarées et huit repas distribués**.
Les 56 nuitées ajoutées correspondent à deux bénéficiaires × 28 nuits ; les
repas ajoutés sont les trois petits déjeuners de Noor. L'ancienne prise de Noor
est hors de cette fenêtre. Ces chiffres ne prouvent pas une présence physique.


Le jeu élargi inclut 26 personnes supplémentaires, réparties entre personnes
seules, duos et groupes de six. Deux fiches distinctes portent le même nom Robin ;
les UUID les distinguent et aucun rapprochement n'est proposé. Les quatre anciennes
prises de Noor et de trois autres ménages sont hors de la fenêtre de 60 jours.
Les situations personnelles comportent informations inconnues, sans ressources
explicitement déclarées et passages de l'emploi à la formation. Noé change de
ménage : les bénéficiaires antérieurs restent conservés et aucune prise du
nouveau ménage ne l'intègre automatiquement. Dans un groupe, un membre n'est pas
bénéficiaire de la prise ; aucune prestation n'est déduite de sa présence.
Les 36 fiches permettent aussi de tester la pagination des personnes et la
recherche avec accents. Les projets des douze ménages ajoutés sont renseignés.


### Des trajectoires avec quatre ou cinq prises en charge

Robin A, Robin B, Léo, Noor, Samira et Thomas ont chacun cinq prises ; Gabriel,
Maïa et Sol en ont quatre. Les 29 prises historiques supplémentaires sont hors
de la fenêtre des 60 jours : son contrat chiffré reste inchangé. Chaque étape
ajoutée comprend un accord d'hébergement avec séjours individuels clos, une
absence close, deux services de repas avec distributions, un projet et un
commentaire. Les appartenances anciennes nécessaires sont explicites et datées.
La clôture de l'hébergement ne clôt pas automatiquement la prise.

Dans une prise en charge, le repère **Prestations** rassemble Hébergement et
Repas ; Situation sociale et projet reste un autre ensemble dans la même page.
Le transport rejoindra le groupe Prestations quand son lot sera livré, sans
ajout de page de passage ni de bouton factice dans cette version.


### A02 — identité et relations déclarées

Les nouveaux jeux de l'Établissement Les Passerelles ajoutent, sans changer les
36 personnes, 18 ménages, 51 prises ni les chiffres d'activité :

- Samira : une nationalité fictive à l'entrée, puis deux à J−20 ; correction du
  lieu de naissance, sans changement de nom ni de date de naissance.
- Samira → Lina et Adam : liens parent/enfant explicitement déclarés à J−60 ;
  Lina ↔ Adam : fratrie déclarée. Rien n'est déduit de la composition du ménage.
- Noor : Thomas comme personne à contacter à J−20, extérieur à son ménage ;
  correction d'une consigne. Ce rôle ne change pas le contact du ménage.
- Gabriel et Éva : couple déclaré à J−90 puis lien de proches à J−5 ; leurs
  appartenances et prestations ne sont pas modifiées par ce changement.
- Les deux Robin : lien de fratrie saisi par erreur puis annulé. Ils restent
  deux identités distinctes et leurs dossiers ne sont pas fusionnés.
- Yannis : nationalités et apatridie non renseignées, sans valeur inventée.

Depuis un dossier ou sa prise en charge, ouvrir Compléments et historique ou
Consulter et mettre à jour dans Liens personnels. Vérifier les deux sens d'un
lien et la restitution à l'entrée dans le résumé. La date de début du lien est
celle de la déclaration applicable, pas une filiation rétroactivement supposée
depuis la naissance. Les prises plus anciennes peuvent donc ne pas avoir ce
renseignement. Les anciens espaces ne sont pas enrichis automatiquement.

## Tester ensemble le dossier personnel complet

Dans un espace **neuf** de l'**Établissement Les Passerelles**, les 36 personnes,
18 ménages et 51 prises en charge gardent leurs prestations et chiffres
d'activité. Le dossier personnel comporte désormais aussi :

- Samira : deux ressources dont un montant inconnu, évolution d'allocation,
  deux créanciers et un total de dette corrigé (sans double comptage), deux
  pièces et deux couvertures avec renouvellement annoncé.
- Thomas : salaire puis rémunération de formation, aide ponctuelle, dette en
  autre devise, échéances de pièce/couverture dépassées qui ne valent pas fin.
- Noor : ressource mensuelle à zéro et ressource annuelle, absence de protection
  explicitement déclarée ; Alex : absence de ressources et couverture inconnue.
- Maïa : deux ressources puis absence globale confirmée, avec historique conservé.
- Yannis : ressources/dettes inconnues, mesure fictive avec organisme et
  interlocuteur ; Gabriel : professionnel désigné distinct de l'interlocuteur.
- Robin A : protection saisie pour le mauvais homonyme puis annulée ; Robin B
  reste un dossier distinct. Les identifiants administratifs sont tous inventés.

Depuis le dossier ou une prise en charge, ouvrir **Ressources et dettes** ou
**Administration et droits**. Changer la date pour comparer les situations,
ouvrir les historiques, puis revenir à la même cible. Tester ajout, changement,
correction motivée et fin réelle ; l'annulation reste une action séparée. Une
déclaration globale d'absence demande confirmation avant de terminer plusieurs
postes. Les anciens espaces d'essai ne sont pas enrichis automatiquement.

Depuis Statistiques, ouvrir le rapport Dossier personnel : choisir une rubrique,
une date et des filtres, comparer HTML et CSV, puis imprimer. Les montants connus
sont partiels et séparés par devise ; un total déclaré de dette n'est pas ajouté
aux créanciers. Les identifiants administratifs sont masqués par défaut dans ce
rapport. Le parcours complet ne nécessite aucune nouvelle bibliothèque.

## Tester le méta-lot B en entier

Dans un espace neuf de l'**Établissement Les Passerelles**, les 36 personnes,
18 ménages et 51 prises en charge sont conservés. Dix demandes montrent le
parcours avant admission : cinq demandes acceptées explicitement liées aux
prises existantes, celle d'Inès acceptée sans prise ni prestation, celle de
Robin A en attente, celles d'Alex/Robin B refusées et celle de Maïa retirée.
Le motif de refus d'Alex est corrigé avec l'avant/après. Demandeur, prescripteur
et auteur de saisie sont distincts dans les exemples collectifs.

Depuis le dossier, la ligne Parcours et l'aperçu des demandes conduisent à la
même page de rubriques. Une demande acceptée permet d'ouvrir la prise par le
formulaire habituel, ou d'associer une prise existante, après confirmation.
Une erreur ou un formulaire périmé ne laisse ni ménage ni prise orpheline.
La liaison ne crée aucun séjour : l'arrivée reste une action d'hébergement.

Samira a deux orientations avec résultats différents ; Inès a une proposition
future sans admission. Chaque orientation s'imprime avec destination et contacts
datés. Les objectifs de Samira/Thomas/Noor/Yannis montrent réalisation, suspension,
poursuite et abandon ; Thomas conserve aussi un objectif à long terme provenant
d'une prise ancienne close. Un objectif du mauvais Robin est annulé. Les récits
anciens de projet et de bilan restent disponibles.

Le suivi de Thomas passe en veille puis redevient actif ; les autres états de
suivi ne ferment aucune prise. Son ancienne activité CHRS et l'activité urgence
plus récente illustrent un relais sans sortie définitive du dossier.

Tester les changements à leur date, une correction motivée et l'historique ;
revenir ensuite à la personne ou à la prise de départ. Dans Statistiques, le
rapport Parcours propose états, cohortes, délais vers une prise débutée, filtres
exacts, impression et CSV. La rubrique Entrées/sorties réutilise les dernières
informations versionnées des prises et leur activité, sans inventer une date
d'effet pour les anciens récits. Tous ces exemples restent fictifs ; les anciens
espaces d'essai ne sont pas enrichis automatiquement.

## Tester le méta-lot C : prestations et gestes quotidiens

Ouvrir un espace neuf de l'**Établissement Les Passerelles**. Les nombres de
personnes, ménages et prises en charge et le contrat d'activité des 60 derniers
jours sont conservés. Le catalogue présente huit types fictifs/historiques :
TAM1/TAM3/TAM10, autres transports/SNCF, bons restaurant et supermarché, produits
en kg et accueil de jour en passages. Les cartes sont des titres remis, pas des
trajets réalisés. Ce catalogue n'est pas créé dans une base ordinaire existante.

- Samira : autorisation TAM3 avec quantité remise corrigée, autorisation TAM10
  sans remise, bons restaurant remis mais déclarés non utilisés.
- Noor : titre SNCF remis, bon supermarché déclaré utilisé, passage d'accueil
  de jour sans nuitée artificielle ; futur service de déjeuner les mercredis
  et vendredis, sans distribution automatique.
- Thomas : remise TAM1 erronée annulée avec son historique conservé.
- Yannis : produits alimentaires remis en kg pendant sa prise en charge, avec
  quantité fractionnaire distincte des titres et repas.
- Répertoire des lieux : établissement/chambre/place facultatifs et correction
  motivée d'un libellé, sans déplacement implicite de personne.

Dans la prise en charge, les aides restent dans **Prestations**. Autoriser ne
remet rien ; Enregistrer une réalisation choisit personnes, date, quantité et
source. Le plafond est global à la sélection, non par personne. Tester correction,
annulation, prolongation et constat d'utilisation, puis le PDF ou relevé imprimable.
Dans Travail du jour, choisir une date : le formulaire de réalisation conserve
cette date et revient à ce travail après enregistrement. Les repas non autorisés
ce jour de semaine ne sont pas proposés.

Pour essayer les départs/absences/lieux partiels sur le séjour collectif de la
famille de Samira, choisir **Continuer individuellement pour agir sur une
personne**. Confirmer une date après les faits existants et un motif. L'histoire
commune reste intacte avant cette date ; les nouveaux fragments conservent lieu
et absence ouverts. Sélectionner ensuite un ou plusieurs séjours individuels
pour absence, retour, changement de lieu ou sortie. Les compteurs d'admission
ne sont pas augmentés par cette continuité. Les arrivées déjà individuelles
gardent leur parcours direct.

Statistiques propose prestations/remises/CSV et le détail individuel d'hébergement,
avec nuits théoriques et hors absences déclarées. Les lignes de fragments ne sont
pas des admissions supplémentaires. Le catalogue des aides et le répertoire des
lieux sont accessibles depuis ces rubriques transversales. Les PDF restituent les
données courantes sous droits ; les émissions numérotées, tarifs et rééditions
figées arrivent avec le financement. Aucun ancien espace n'est enrichi ou remis
à zéro automatiquement.

### Financements et documents (jeu neuf, D)

Dans une prestation d'hébergement de Samira, ouvrir **Financement, tarifs et
documents** : chambres et petits déjeuners séparés, prévu/autorisé, deux financeurs
et reliquat. Le premier bon est annulé pour erreur de quantité ; son remplacement
utilise le calcul corrigé. Le catalogue change ensuite le prix de chambre : ouvrir
l'ancien document vérifie que son prix et ses coordonnées restent conservés.
Les repas de Samira montrent des catégories explicitement déclarées et un tarif
petite enfance à zéro. Son transport TAM3 distingue quantité autorisée et remises
documentées, avec un relevé numéroté. L'accueil de jour de Noor montre une gratuité
explicite ; les autres prestations peuvent rester sans coût connu. Aucune recette
ne demande de contacter un organisme, signer ou payer. Ces compléments concernent
uniquement les nouveaux espaces Établissement Les Passerelles.

### Appels, relève et croisements (jeu neuf, E)

L'Établissement Les Passerelles propose quinze appels, dont un doublon annulé.
Le premier appel pour Samira reste d'abord anonyme puis identifie explicitement
les trois personnes ; il est lié à une prise existante sans admission nouvelle.
Le rappel du lendemain est un autre appel, de l'autre côté de minuit. Noor,
Thomas et Alex ont aussi un appel identifié ; d'autres restent anonymes, avec
heure connue/inconnue, demande alimentaire/hébergement, réponse inconnue ou
absence de réponse déclarée. Un effectif déclaré zéro est distinct d'un effectif
non renseigné. L'heure d'un appel est corrigée en conservant sa première version.

Une action de rappel erronée est annulée sans être déclarée réalisée ; une autre
est clôturée puis rouverte avec motif. Une transmission porte une date déclarée
corrigée, distincte de l'enregistrement. Depuis le compte Nadia, deux modèles
personnels illustrent demandes/réponses et classes horaires (nuit/journée/soir).
Ils conservent les paramètres, pas les résultats. Les autres comptes n'héritent
pas de modèles privés. Les anciens espaces d'essai restent intégralement conservés.
