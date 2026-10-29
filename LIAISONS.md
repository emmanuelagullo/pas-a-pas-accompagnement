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

Les périodes symboliques réutilisent les calculs civils existants, sans modifier
les statistiques. Toutes les dates reste le défaut des dossiers et prestations.
Les mentions @ sont proposées uniquement parmi les collègues actuellement
habilités à lire le message dans sa portée exacte. La publication revalide
chaque destinataire ; une mention n'accorde aucun droit et ne rend pas le texte
privé. Retirer la mention du texte ou décocher le destinataire évite sa
notification. Les mentions concernent les nouveaux messages, pas les corrections.
Les notifications de mention conduisent au message exact ; leur visibilité et
la pastille du compte suivent les accès actuels, y compris après révocation,
annulation ou changement de politique. Aucun compteur ni courriel n'est ajouté.

La recherche est regroupée et repliée par défaut avec son résumé. Rechercher et
Effacer ont le même GET avec ou sans JavaScript ; la frappe est temporisée
comme dans Dossiers. Écrire un message reste accessible sans ouvrir les filtres.
Les destinataires de mentions retirées du texte sont retirés de la sélection.

Une réponse est une contribution attachée par fil_cle à une entrée autorisée,
avec exactement la même portée. Aucun sous-fil ni destinataire implicite.
Les droits de la racine et de chaque réponse précèdent recherche et comptage.
Le fil remonte selon les réponses visibles récentes, sans changer la date de
la racine. Les réponses restent chronologiques et repliées, sauf ouverture
explicite, recherche dans une réponse ou notification. Les corrections et
annulations réutilisent l'histoire des contributions. Les clés d'envoi évitent
les doublons ; une réponse ne peut être déplacée par le service de publication.
Les brouillons de message et de réponse restent distincts en mémoire dans le
panneau ; ils ne sont pas enregistrés sur le serveur avant publication.
Les actions terminées restent consultables dans Actions de suivi pour conserver
leurs discussions ; les actions annulées ne permettent pas de nouvelle réponse.
