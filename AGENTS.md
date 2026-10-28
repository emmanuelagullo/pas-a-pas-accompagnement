# Consignes pour les agents

## Écosystème, dépôts et responsabilités

Ces dépôts forment un même écosystème, avec trois responsabilités distinctes :

| Dépôt | Responsabilité | Référence Inria | Miroir GitHub |
| --- | --- | --- | --- |
| `pas-communs` | Socle et architecture techniques communs | <https://gitlab.inria.fr/pas-communs/pas-communs> | <https://github.com/emmanuelagullo/pas-communs> |
| `petits-pas` | Application métier : carnets de suivi en maternelle | <https://gitlab.inria.fr/petits-pas/petits-pas> | <https://github.com/emmanuelagullo/petits-pas> |
| `pas-a-pas-accompagnement` | Application métier : accueil et accompagnement social, notamment CHRS | <https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement> | <https://github.com/emmanuelagullo/pas-a-pas-accompagnement> |

Inria est la référence du code ; GitHub est le miroir utilisé notamment pour
les constructions Windows/Linux et la publication des wheels et programmes.
Examiner le main public récent avant de préparer un patch. Les miroirs d'un
même dépôt doivent recevoir les mêmes commits et tags ; les versions des trois
dépôts restent indépendantes.

Les deux applications importent `pas_communs`, jamais le code de l'autre
application. Le socle est une bibliothèque embarquée, pas un service central.
Les mécanismes techniques partagés y résident : paquets et sauvegardes,
primitives d'authentification, exécution et construction locales, installateur
Windows, ressources navigateur, contrats serveur, recettes CI, intégrité des
publications et moteurs PDF. Se fier aux API réellement présentes et à leurs
contrats, sans supposer que toute l'infrastructure est déjà extraite.
Les modèles et migrations métier, rôles, permissions, parcours et contenus
restent propres aux applications. Comptes, bases, médias, secrets et espaces
navigateur sont séparés ; une primitive commune ne crée ni SSO ni équivalence
entre une école et un CHRS.

Les sites Hugo restent dans `site/` de chaque application. Les quatre dépôts
auxiliaires de publication ont les références Inria suivantes :

| Produit | Racine du domaine : redirection | Application navigateur : inclusion CI |
| --- | --- | --- |
| Petits Pas | <https://gitlab.inria.fr/petits-pas/petits-pas.gitlabpages.inria.fr> | <https://gitlab.inria.fr/petits-pas/petits-pas-pwa> |
| Pas à Pas | <https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement.gitlabpages.inria.fr> | <https://gitlab.inria.fr/pas-a-pas-accompagnement/pas-a-pas-accompagnement-pwa> |

Ces auxiliaires ne contiennent ni second exemplaire de l'application, ni
bibliothèque métier, ni fork du socle. Aucun miroir GitHub de ces auxiliaires
n'est déclaré ici : ne pas en inventer un. Le préparateur PWA, les constructeurs,
les manifestes et les sources des sites se modifient dans le dépôt applicatif.

## Coévolution et séparation des préoccupations

- Pour une évolution strictement métier, intervenir dans l'application concernée.
  Dès qu'une évolution dépasse cette couche, examiner aussi le socle, l'autre
  application et les dépôts de publication affectés. Lire leurs AGENTS.md et
  contrats ; expliciter les impacts et les adaptations nécessaires.
- Factoriser ce qui est factorisable et harmoniser ce qui est harmonisable.
  Rechercher un mécanisme existant avant d'en recopier un. Extraire les mécanismes
  techniques communs dans pas-communs avec des paramètres ou façades propres aux
  produits ; harmoniser les conventions et recettes qui peuvent rester dans
  leurs dépôts. Justifier l'abstraction par les usages des deux applications,
  sans imposer un modèle métier commun ni une abstraction spéculative.
- Préparer ensemble les changements du socle et les adaptations des consommateurs.
  Vérifier les deux usages touchés, leurs compatibilités et leurs profils
  serveur/bureau/PWA pertinents. La CI du socle ne qualifie pas à elle seule
  les applications ; préserver sauvegardes historiques, données et identités.
- La version réellement adoptée est fixée par requirements-communs.txt (URL du
  wheel et SHA-256). Les mentions de versions dans les anciens jalons décrivent
  leur historique. Pour du code ou des ressources du socle, publier une nouvelle
  version immuable avant de pousser les consommateurs qui la requièrent. Une
  modification de documentation seule ne nécessite pas de nouveau wheel.
- Livrer les patches par dépôt avec l'ordre d'application, de publication et de
  vérification. Maintenir cette carte et les AGENTS.md affectés cohérents. Annoncer
  à l'avance tout changement de profils d'installation ou de commandes de
  déploiement pour permettre la préparation des instances existantes.
- Dans les deux applications, les tags numériques qualifiés déclenchent les
  releases GitHub ; seuls les tags sans suffixe publient automatiquement la PWA,
  à partir des artefacts validés sans
  reconstruction ; la reprise manuelle reste disponible. Sur main, la publication
  PWA reste manuelle. Les déploiements serveur gardent leur procédure séparée
  et ne sont pas modifiés implicitement
  par une extraction du socle ou une publication de programme/PWA.

## Travail dans l’application CHRS

Lire README.md et ARCHITECTURE.md. Le prototype propose les profils serveur,
bureau et navigateur ; il reste réservé aux données fictives et n’est pas
une application qualifiée pour des dossiers réels.
Ne pas copier les modèles scolaires, ni créer d'équivalences école/CHRS ou
classe/service. Les comptes et personnes accompagnées sont distincts.
Préserver le modèle utilisateur et ses migrations ; ne pas changer
AUTH_USER_MODEL par simple renommage. Les permissions sont contrôlées dans
les vues, y compris si les boutons sont cachés. Pas de nouveau droit implicite.
Conserver les écrans en français, les formulaires accessibles et CSRF.
Pour un changement applicatif, vérifier `python manage.py check`, `python manage.py test`,
`python manage.py makemigrations --check --dry-run` et `git diff --check`.
Commits français avec #SOC. Utiliser l’identité de commit explicitement
indiquée ; si elle n’est pas précisée, la demander avant de créer les commits.
Livraison par patch git am, sans Signed-off-by.

## Contrats techniques hérités des jalons

#SOC2 : les sauvegardes passent par `pas_communs.paquets`. Conserver le profil
CHRS distinct, l'exclusion des sessions dans les copies et le refus d'écrasement.
La dépendance épinglée requiert la publication préalable du wheel ; les tests
de copie utilisent des données fictives et un dossier indépendant.

#SOC3 : tester aussi l’installation locale et les programmes Windows/Linux.
Le serveur de développement et la fenêtre locale sont deux profils distincts.
Ne pas déplacer .local automatiquement ni créer d’identifiants prédéfinis.

#SOC4a : le backend de plafond ne connecte personne ; conserver le backend
standard et les droits explicites. Le parcours TOTP est ajouté ensuite sous #SOC4b.
Tester la révocation ciblée et le premier compte avec les deux backends.

#SOC4b : lire AUTHENTIFICATION.md. Tester serveur avec requirements-2fa.txt et
bureau sans ces dépendances. Ne pas activer le TOTP dans le programme local par
simple présence des clés. Ne jamais rendre une base inscrite accessible sans son
facteur ; la récupération technique est explicite et ne modifie pas les droits.
Préserver les UPDATE conditionnels et tester la concurrence réelle sur SQLite,
la migration depuis 0001, les preuves périmées et la copie restaurée.
Masquer clés et formulaires sensibles dans les diagnostics, même en DEBUG.

#SOC5a : lire pwa/README.md. Ne jamais distribuer une base ou un secret de test.
Tester le vrai Pyodide et le navigateur, à la racine et sous un préfixe.
Conserver le stockage propre au produit et l'arrêt sur persistance incertaine.
Les copies PWA sont ajoutées sous #SOC5b ; distinguer téléchargement préparé
et copie effectivement conservée hors appareil.

#SOC5b : lire pwa/README.md. La vérification d'un ZIP reste dans un Worker
séparé ; ne jamais modifier le pointeur actif avant confirmation. Conserver
la reconnexion, les refus TOTP locaux et l'export brut sans migration.
Tester le vrai Worker aux deux côtés du commit, les ZIP natifs et la mise à
jour ; ne jamais publier un bundle --test. Garder les nouvelles injections
inaccessibles dans une construction normale.

#SOC6a : lire SERVEUR.md. Conserver le profil local et sa clé persistante.
Le serveur exige un dossier absolu explicite ; pas d'installation du premier
compte par le web. Tester scripts/verifier-profil-serveur.py ; aucune confiance
implicite au proxy et aucune assimilation au déploiement de dossiers réels.

#SOC6b : la CI appelle pas_communs.ci ; garder les bancs métier dans les scripts
du produit. Les manifestes décrivent les octets, pas une preuve de CI réussie.
Les publications suivent les règles actuelles de #SOC6c. Tester le refus
d’un bundle --test lors de la préparation du candidat ; les tests Gunicorn
restent loopback.

#SOC6c : lire DEPLOIEMENTS.md. Le profil Render est jetable et refuse tout
emplacement existant ; le persistant ne crée aucun compte ni fiche. Les essais
utilisent les scripts réels, des dossiers temporaires et un Gunicorn loopback.
Ne pas assimiler cette qualification SQLite à PostgreSQL/S3 ou à la production.
Les promotions vérifient projet, commit, tag, job et empreintes ; aucune
reconstruction ni remplacement d'une release existante. Préserver les reprises
manuelles, les secrets hors dépôt et la séparation des projets Pages. Toute
activation réelle exige les destinations configurées par l'exploitant.

#SOC7b : le rendu PDF natif est dans pas_communs.pdf (0.6.0), appelé par
les façades du produit. Les droits, contenu et templates restent ici. Tester
les vrais PDF, le téléchargement et les dépendances propres aux profils.
Ne pas importer WeasyPrint/Pango dans le navigateur ni remplacer les carnets
scolaires par le backend texte. Préserver le chargement autorisé des médias.

#SOC6c — Pages : lire site/README.md. Le site Hugo reste dans le dépôt
applicatif ; les deux autres projets contiennent redirection et inclusion CI.
Vérifier Hugo et scripts/verifier-site-public.py ; ne pas annoncer une fonction
métier seulement prévue ou publier une base, des secrets ou des ZIP privés.

Versionnement : le tag Git exact définit la version ; les branches CI utilisent
dev.<sha8>. Ne pas commiter version-application.txt : il est généré pour les
programmes et la PWA. Les notes viennent de CHANGELOG.md et accompagnent les
artefacts vérifiés ; préserver la promotion sans reconstruction.

#SOC3b : l’installateur Inno Setup et son banc viennent du wheel 0.7.0.
L’identité du produit reste dans scripts/installateur-windows.json. Préserver
les données à la désinstallation et inclure le setup vérifié dans les manifestes
et promotions. Tester les refus d’un candidat sans setup ou altéré.

#SOC6c — publications automatiques : un tag numérique qualifié déclenche
la release GitHub ; la PWA automatique exige un tag sans suffixe. Le workflow de publication GitHub utilise le code de
main et les artefacts du run terminé ; ignorer branches, PR, forks et échecs.
Conserver les vérifications des deux forges et la reprise manuelle. Les
déploiements serveur restent indépendants, sans changement de déclenchement.


#AUD : lire les contrats actualisés et la recette QUALIFICATION.md de pas-communs.
La version 0.8.0 est publiée et adoptée ; préserver son tag et ses octets.
Une modification documentaire seule ne demande pas de nouveau wheel. Les
consommateurs peuvent conserver des versions différentes, explicitement épinglées.
Préserver les noms ZIP historiques portables ; refuser les alias Windows à
l'export comme à l'import sans renommer les données. Le runtime Pyodide est
sélectionné explicitement dans les constructeurs ; les politiques de promotion
et de déploiement restent applicatives. Qualifier les octets du wheel et les
deux consommateurs ; aucune installation pip n'est implicite dans cette recette.


Compléments AUD : lire BASE-CIBLE.md avant une garantie métier dépendant du
backend. La cible PostgreSQL est retenue pour le futur serveur ; seuls les tests sont ajoutés. Pour la PWA, Python
constructeur >=3.12 et Python embarqué Pyodide sont distincts et journalisés.
La politique du canal stable est décrite dans DEPLOIEMENTS.md.

Politique PWA adoptée : seuls les tags sans suffixe publient automatiquement
à l’adresse habituelle. Les préversions sont construites et testées, mais refusées
par le préparateur Pages. La publication de main reste manuelle.

#SOC — copies : adoption candidate de 0.9.0, à pousser après publication du wheel.
Lire SAUVEGARDES.md dans pas-communs. Les ZIP restent privés, complets et propres
au produit ; ne pas les transformer en démonstration distribuable. Conserver les
sessions de la source et vider seulement celles de la préparation restaurée.

#SOC — démonstration métier : lire DEMONSTRATION.md. Le jeu est généré dans
le produit via les services CHRS1–4. Les professionnels fictifs du répertoire sont distincts des comptes ; aucun
ZIP privé distribué, aucun reset ni nouvelle restauration. Garder l’espace
habituel intact, y compris les jeux chargés par le premier patch ; le bouton
d’essai ouvre un autre espace persistant (stockage -essai / dossier essai-fictif),
avec retour au chemin habituel personnalisé. Réutiliser configurerEspace et les
parcours de copie existants, sans nouveau format ni reset.

#SOC — sites : lire site/README.md et site/theme-communs/HUGO.md. Initialiser
le sous-module épinglé avant Hugo. Ne pas recopier les layouts/styles du thème.
Conserver contenus, démonstration, URL et paramètres de couleur propres au produit.

# CHRS5–7 : ergonomie et corrections

Lire les sections CHRS5–7 de README.md et les services de personnes. Retourner à
la fiche/accord concerné après POST ; destinations construites côté serveur,
pas de next arbitraire. Travail du jour : aucun repas implicite, lots atomiques
et doublons refusés. Corrections motivées avec jeton d’état signé, avant/après
typé, règles de dépendances et permissions explicites ; ne pas supprimer ou
réécrire les journaux d’origine. Aucune attribution de droits en migration.
Les services liés prennent le verrou métier du ménage avant ceux du suivi et
du séjour, pour qualifier concurrence et corrections sur SQLite/PostgreSQL.
Toute nouvelle écriture liée doit respecter cet ordre. Vérifier les refus,
rollback, stale forms, concurrence et reprise ZIP des nouveaux journaux.
La démonstration existante reste intacte ; seuls les jeux nouvellement générés
reçoivent CHRS1–7. Ne pas rouvrir le socle pour ces parcours strictement métier.

# BD3 — décisions d'accord

Lire les sections BD3 de README.md et ARCHITECTURE.md. Ne pas assimiler une
prolongation à une correction ni une annulation à une sortie. Les droits BD3
sont dédiés, attribués volontairement par autoriser_bd3 ; aucune attribution en
migration ni à la réouverture d’un ancien jeu. Les accords annulés restent
consultables mais ne reçoivent plus d’admission/distribution/correction. Toute
nouvelle écriture liée doit recharger l’état sous le verrou commun de ménage.
Préserver la révision des accords, leurs décisions et les anciens journaux dans
les copies ; tester dépendances, conflits, migration et reprise ZIP.


# BD4 — entrée et synthèse

Le dossier est une vue personne/ménage, pas un alias de l'accompagnement ni un
nouveau modèle. Filtrer la vue personne sur les bénéficiaires et la vue ménage
sur le ménage ; ne pas importer implicitement les prestations des autres ménages.
Conserver les actions collectives et leurs bénéficiaires explicites. Aucune
création silencieuse de ménage, période ou accord. Les droits existants restent
nécessaires ; les fragments de recherche ont les mêmes contrôles que l'accueil.
Préserver le repli GET, les retours signés et les sélections du ménage d'origine.
Tester `node scripts/verifier-recherche-dossiers.cjs` et actualiser les recettes
navigateur/PWA lors d'un changement des libellés ou de la navigation.


## Aides contextuelles et erreurs compréhensibles

Pour chaque champ ou action dont le sens n'est pas évident, expliquer l'intention,
la cible (personne, groupe, période), l'effet et les limites utiles. Éviter les
aides qui répètent simplement le libellé ; ne pas imposer une bulle à chaque item.
Les informations indispensables à la saisie ou au consentement restent visibles,
près du champ ou de la confirmation, avec `help_text` / `aria-describedby`.
Les détails secondaires peuvent être dépliables (`details` / `summary` natifs),
accessibles au clavier et au tactile, sans dépendance nouvelle par défaut.
Une vraie info-bulle au survol doit aussi être accessible au focus, rester
lisible quand on la survole et pouvoir être fermée avec Échap. Ne pas utiliser
`title` comme unique aide. Référence :
https://www.w3.org/WAI/WCAG22/Understanding/content-on-hover-or-focus.html .

Une erreur de champ est rattachée au champ nommé, visible dans le choix de saisie
actif, et associée à son contrôle. Un résumé d'erreurs renvoie aux champs ; ne
pas aplatir une ValidationError structurée en message global anonyme. Préserver
les valeurs saisies et la validation serveur sans JavaScript.

Avant une nouvelle abstraction d'aide, examiner les mécanismes existants des
deux produits. Les mots et règles métier restent dans chaque application ; le
socle ne fournit un composant que si des usages réels justifient son extraction.
Vérifier les parcours modifiés au clavier, sur écran étroit et sans JavaScript ;
distinguer les tests du HTML des observations réelles en navigateur.

# BD6 — dossier et prise en charge

Form2 met en premier situation sociale, commentaire et prises en charge ; la
composition appartient à la situation sociale. Form3 borne les prestations à
une prise explicite. Conserver les anciens suivis et journaux sans fusion
arbitraire ; signaler les divergences avec leur provenance. Les restitutions
sociales datées ne sont pas des instantanés figés. Ne pas inventer une annulation
de prise ni assimiler fin prévue, clôture, accord et réalisation. Les durées sont
des unions civiles, sans multiplication par bénéficiaire/service. Les nouveaux
droits BD6 restent volontaires. Pour les écritures personnelles, réserver la
personne sans prendre ensuite de verrou ménage ; pour les écritures liées,
garder ménage puis prise. Tester migration, concurrence, copies et vrai parcours
navigateur/PWA lorsque ces chemins changent.

Hébergement : une seule entrée « Nouveau séjour » réunit accueil prévu et
arrivée effectuée. Une prévision n’ajoute ni nuitée réalisée ni lieu effectif.
Confirmer l’arrivée réutilise l’accord ; les personnes encore attendues restent
visibles lors d’une arrivée partielle. Ne pas réintroduire une entrée séparée
« hébergement sans admission » pour refléter la seule structure des tables.

## Textes narratifs enrichis

Lire TEXTES-ENRICHIS.md. Conserver le format explicite, les anciennes colonnes
texte et les documents de chaque version/correction. Ne jamais interpréter
automatiquement les textes historiques en HTML/Markdown. Les projections
textuelles sont dérivées du document validé ; les droits et motifs restent
métier. Une modification du format exige les essais de reprise et de conflits.
Les fichiers JS embarqués sont reconstruits avec le lock de outils/editeur ;
conserver leurs licences et tester scripts/verifier-editeur-textes.cjs ainsi
que le vrai parcours PWA. Ne pas assimiler Chromium à WebView2/WebKitGTK.

## Solenne — contacts et personnes

Le contact désigné du ménage est facultatif et daté, sans responsabilité légale
ou professionnelle implicite. Il peut être extérieur au ménage ; ne créer ni
appartenance ni bénéficiaire depuis ce rôle. Le service réserve le ménage avant
lecture et réutilise la chronologie typée ; les journaux gardent UUID/libellés
avant/après. Un retrait est une nouvelle période sans contact, pas une suppression.
Préserver les retours BD, droits distincts, copies et la restitution à l'entrée.

Le répertoire Partenaire représente des organisations/services, pas les comptes
ni les personnes accompagnées. Les fiches sont datées et leurs corrections
journalisées. Ne pas rapprocher automatiquement un ancien libellé libre.
La réservation d'une fiche de répertoire n'acquiert aucun verrou de ménage.
Les nouveaux lieux peuvent référencer l'organisme sans recopier ses coordonnées.
Les droits et exports du répertoire ne donnent aucun accès implicite aux dossiers.


Les professionnels sont distincts des comptes, des personnes accompagnées et du
contact du ménage. Une mission est attachée à la prise, avec une cible exclusive
professionnel/organisme et un rôle explicite ; ne pas inférer de représentation
légale. Préserver co-intervenants, portée temporelle du parent, annulation motivée,
journaux atomiques et verrou ménage puis prise. Ne jamais convertir un ancien
référent libre par rapprochement de nom. Les exports doivent réutiliser les
mêmes sélections datées que la consultation.


Saisie : utiliser les bases de champs_saisie et l'adaptation des champs dynamiques.
Préserver codes textuels, valeurs inconnues, dates d'effet, source non recopiée,
validation serveur et saisie sans JavaScript. Les propositions sont volontaires,
journalisées et ne collectent jamais automatiquement une valeur de dossier.
Les champs d'authentification conservent leurs attributs propres. Dans les textes
visibles écrire « prise en charge » ; conserver routes et variables internes.
Les jeux Les Passerelles enrichis ne sont créés que dans un espace neuf ; ne jamais
réinitialiser, redater ni enrichir implicitement un ancien essai.


Identité déclarée et liens : garder les nationalités comme collection typée,
inconnu distinct d'apatride, et aucune inférence depuis le pays, le sexe ou le
ménage. Les liens déclarés ne valent pas représentation légale. Une mutation de
paire réserve les personnes dans l'ordre des UUID et n'acquiert aucun verrou de
ménage ensuite. Conserver les vues réciproques, le CAS, les annulations, les
sources/auteurs et les cibles immuables ; aucune création implicite de personne,
appartenance ou bénéficiaire. Les recherches/CSV ne doublent pas les liens et
ne font pas d'une déclaration à date une file active. La fiche PDF reste soumise
aux droits propres des compléments.

Dossier complet : conserver les schémas typés des déclarations personnelles,
leurs journaux atomiques et le CAS personne avant lecture. Ne pas additionner
le total déclaré des dettes aux créanciers détaillés ni convertir monnaies ou
périodicités implicitement. Inconnu, absence et zéro restent distincts. Une
échéance prévue n'est jamais une fin effective. La déclaration globale d'absence
exige confirmation ; les anciennes synthèses sociales sont conservées. Les
identifiants administratifs sont exclus du rapport par défaut ; les inclure
reste un choix explicite sous droits. Aucune déduction de pouvoirs juridiques.

Parcours B : conserver cible et bénéficiaires immuables, chronologies typées,
CAS et journaux atomiques. Admission liée = demande acceptée, mêmes bénéficiaires ;
verrou ménage puis demande. L'ouverture et sa liaison échouent ensemble. Ne
déduire ni séjour, ni sortie, ni prescription, ni état juridique d'une demande
ou d'une orientation. Objectifs et suivi survivent aux prises ; l'état terminé
du dossier ne bloque rien. Préserver les récits enrichis existants et ne pas
les découper automatiquement. Les rapports de dernières informations de prise
ne deviennent pas des histoires à date d'effet. Respecter les droits des ménages,
prises et répertoires dans les contextes et exports.

Prestations C : garder unités et libellés photographiés dans chaque accord ;
le catalogue ne réécrit pas l'histoire. Plafond global, remise et usage déclaré
sont distincts ; zéro et inconnu ne se confondent pas. Ne pas multiplier une
remise collective par ses bénéficiaires, des cartes par leur nombre de voyages,
ni des bons par un tarif supposé. Conserver droits, CAS sous verrou ménage et
journaux atomiques. Les jours de repas s'appliquent à la saisie et au travail
du jour. Une continuité individuelle ne devient pas une nouvelle admission ;
préserver les compteurs d'épisodes et les nuitées de fragments. Les départs
partiels se lisent dans le détail individuel. Les corrections de lieux doivent
rester sans cycles et journalisées. Les PDF de restitution ne sont pas des
documents émis ou figés ; le méta-lot D porte ces usages.

Financements D : ne jamais dériver un paiement d'une imputation ni une réalisation
physique d'une ligne de coût. Garder phases/devises/unités séparées, prix décimaux,
arrondi par ligne et reliquat explicite. Une suggestion depuis les faits reste à
confirmer ; les personnes-nuitées ne sont pas des chambres et les absences ne
sont pas implicitement déduites. Les versions de tarifs et de calcul sont conservées,
les corrections datées ne ressuscitent pas un ancien prix. Les documents émis
photographient coordonnées et contenu ; leur annulation est une ligne séparée,
jamais une réécriture. Numéro et lien de remplacement restent uniques. Préserver
le verrou ménage, CAS, droits volontaires, contexte BD/date/retour, PDF privés et
copies ; tester `personnes.tests_meta_d` et les trois profils Solenne.

E — 115 et relève : un appel n'est ni un séjour ni une demande admise. Garder
heure inconnue, date du fait et horodatage de saisie distincts. Rappel = nouvel
appel ; identification ultérieure et correction ne se confondent pas. Vérifier
les cibles et leurs droits, y compris anciennes versions/PDF. Aucune création ou
fusion de personne/ménage depuis téléphone ou libellé. Les listes manquantes ne
s'inventent pas ; les propositions locales sont volontaires et versionnées.
Notes : une cible SQL, dates nullable héritées, corrections et annulations
conservées. Une action de relève est explicite, ne se déduit pas du texte, et
son annulation n'est pas une réalisation. Garder le CAS dans les formulaires.
Exploration : registre fermé, droits revalidés, critères personnels sur la même
personne, totaux distincts recalculés et unités/phases non mélangées. Ne jamais
présenter un compteur maximum familial ancien comme des personnes distinctes,
ni une première entrée connue comme absolue. Les classes modernes ont une fin
exclue et refusent les chevauchements. Tester personnes.tests_meta_e et les trois
profils ; distinguer couverture fonctionnelle et audit sémantique exhaustif,
qui ne se conclut pas par la seule existence d'un explorateur générique.


F — consolidation : les documents joints sont opaques et versionnés, avec
une seule cible immuable, CAS du parent et ordre ménage puis prise. Conserver
les octets dans la transaction, contrôler taille/empreinte et télécharger en
pièce jointe privée sans exécution. Une annulation n'efface rien. Les besoins
d'accueil et antécédents réutilisent les faits personnels et journaux existants ;
aucune date d'institution ou donnée médicale n'est déduite d'un récit.
Les imports de modèles/propositions sont explicites : registres fermés, droits
revalidés, aucune donnée de dossier, identité ou permission importée, propositions
existantes inchangées et rollback intégral en cas d'erreur. Ne pas confondre
catégorie de repas proposée et majorité légale, ni suggestion et réalisation.
Pour les statistiques, réconcilier nuitées majeurs + mineurs + inconnus, conserver
la même personne dans tous les axes et la prise exacte des missions ; bornes
d'entrée/sortie distinctes du chevauchement. Tester personnes.tests_meta_f.


Trajectoire : l’entrée dossier est transversale ; l’ancienne URL garde son filtre
de prise. La comparaison réutilise bd6.etat : déclaration personnelle applicable,
puis projection économique détaillée si autorisée. Les anciens suivis restent des
témoins distincts, jamais un repli consolidé ni une continuité inventée. Le filtre
de prise porte sur ses bénéficiaires et faits liés, sans borner l’histoire
personnelle à sa période. Une vue personne exclut les bilans collectifs ; une vue
ménage borne les déclarations personnelles aux appartenances ou bénéfices datés.
Tester personnes.tests_trajectoire_unifiee ; conserver les statistiques et les
documents financiers émis. Aucun changement de tables ni de format de copie.

Condition sociale commune : `condition_sociale` est une présentation des modèles
existants, pas une nouvelle définition des sources. Garder les lectures groupées
par modèle, les droits par rubrique et les documents binaires hors du chargement
de la page. Les fragments de formulaire réutilisent les vues et services métier,
CSRF, journaux et contrôles périmés ; conserver le repli en pleine page sans JS.
Une date de consultation n'est pas une date de saisie ni un motif partagé.
L'identité principale et les anciennes informations de projet ne deviennent pas
des faits personnels datés. Ne pas exposer un retrait générique sans traiter la
continuité, les références et la copie restaurée. Tester
`personnes.tests_condition_sociale`, les histoires personnelles, interventions,
parcours et trajectoire. Lire ERGONOMIE-CONDITION-SOCIALE.md pour les limites du lot.

BD-SOLENNE-02 : les cinq séries personnelles retirables conservent leurs lignes
et journaux ; `objects` les exclut après retrait, `tous` et le gestionnaire de
base les conservent. Les copies physiques restent complètes ; employer
`dumpdata --all` pour un export technique intégral. Ne pas contourner ce contrat
dans une nouvelle jointure brute. Un retrait rétablit uniquement un précédent
continu, conserve la borne suivante et peut laisser « non renseigné ». Les
collections et décisions liées ne sont pas des séries à valeur unique.
La portée des corrections est confirmée côté serveur et liée aux bornes ;
les droits et le CAS restent indépendants. La couleur d'un champ repris ne
constitue pas une filiation persistante entre déclarations distinctes.
Préserver les événements de coordination entre édition sociale et prestations,
le contexte de retour signé et les en-têtes non éditables réactualisés.
Tester `personnes.tests_retraits_chronologiques`,
`personnes.tests_condition_sociale` et les histoires/migrations existantes.


BD-SOLENNE-04 : le contexte de l’opération est distinct du motif et de la source.
Seuls les journaux optant pour TraceSaisie le conservent ; le scope ouvert par
saisie_sociale.executer doit toujours être réinitialisé. Ne pas fabriquer une
source lorsque celle-ci est inconnue, ni remplacer une source ancienne avec le
contexte commun. Garder les contrats spécialisés des annulations/fins et des
séries du répertoire. Les champs désactivés de date ont un repli GET explicite ;
une date implicite est toujours recalculée côté serveur. Tester
personnes.tests_saisie_sociale, les séries sociales, copies et recettes navigateur.
Les sources inconnues et les motifs des rectifications sociales ordinaires sont
facultatifs : cela actualise, pour ce périmètre, les anciennes consignes exigeant
systématiquement un motif. La preuve d’état, les dates, droits, journaux et
confirmations de portée ne sont pas remplacés par le texte du contexte.


Acteurs : lire ACTEURS-ACCES.md. Ne pas confondre appartenance professionnelle,
responsabilité métier et habilitation actuelle. La migration n’active ni contrôle
ni droit. « Tous » signifie tous les dossiers accessibles. Les nouveaux faits
ont une portée explicite ; ne pas déplacer l’histoire lors d’un relais/service.
Les gestionnaires de base intégraux sont réservés aux migrations, copies et
opérations techniques explicitement contrôlées, pas aux lectures ordinaires.
Préserver le contrôle des écritures et l’invalidation du cache limité à la
requête. Les statistiques regroupées n’ouvrent pas les justificatifs ; les
options d’export restent bornées à leur service. Tester acteurs,
acteurs.qualification_navigateur et scripts/qualifier-acteurs-profils.py ;
distinguer les vues Django PWA des vrais essais Pyodide/OPFS et les recettes
SQLite de PostgreSQL. Ne pas introduire de nouvelle définition statistique.


Chronologie : lire CHRONOLOGIE.md. Garder les lectures contrôlées avant agrégation,
les bénéficiaires explicites et les autorisations distinctes des réalisations.
Une période ouverte ne démontre pas de présence future ; les prévisions ont leur
propre ligne. Préserver les retours signés, la fenêtre, les filtres et l'ancre.
Tester personnes.tests_chronologie ; distinguer HTTP/HTML, navigateur Chromium
et vrais programmes/Pyodide. Aucun nouveau droit ni migration pour cette lecture.
