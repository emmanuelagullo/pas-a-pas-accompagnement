# Cahier de liaison unifié

Un même cahier s’ouvre depuis le menu et le bouton **Liaisons**, placé à gauche
d’**Équipe de suivi**. Le menu choisit le service de travail. Un dossier inclut
ses prises et prestations ; une prise ses prestations. Une prestation reste
sur sa propre portée. **Inclure les niveaux inférieurs** permet de restreindre
la lecture. Les renvois supérieurs ouvrent le bon écran, directement sur son
cahier ; ils ne mélangent pas automatiquement les messages supérieurs.

Messages et Équipe sont cochés par défaut. Prestations et Actions à faire
complètent la lecture. Le service commence sur les trente derniers jours ;
les dossiers, prises et prestations n’imposent pas de borne historique.
Les dates et types restent modifiables. Les filtres masquent sans supprimer.

Les messages existants, leurs corrections et annulations sont réutilisés.
Une note peut désormais viser directement un ménage, sans désigner une personne
à sa place. Sa cible reste unique. Les événements d’équipe proviennent des
responsabilités et de leurs journaux : aucune copie automatique en note.
Le message facultatif d’attribution est partagé avec les lecteurs autorisés
à cet événement ; ce n’est pas une messagerie privée. L’auteur est conservé
avec son compte et son nom affiché lors de la nouvelle attribution.

Le repérage d’une identité et les droits statistiques ne donnent pas accès au
cahier. Chaque élément est autorisé avant recherche, compte et pagination.
Les écritures revalident cible, tâches, politique et dates. Les nouvelles
saisies du cahier portent une clé d’envoi signée pour éviter les doubles
publications lors d’un réessai. Les anciens messages restent inchangés.

Le panneau et la pleine page appellent le même service. Sans JavaScript, un
lien ouvre la pleine page. Les brouillons sont conservés pendant les filtres ;
la navigation avertit d’une saisie non publiée. Aucun courriel, compte extérieur,
calcul statistique ni mécanisme de frise n’est ajouté.

Recettes : `personnes.tests_liaisons`, `acteurs.tests_messages_attribution`,
`personnes.tests_transmissions`, `personnes.qualification_liaisons` (Chromium).
