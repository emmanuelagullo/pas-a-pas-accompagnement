# CHRS10 — Dictionnaire initial des indicateurs

Période de consultation : `[début, fin[`, en dates civiles. Un séjour ou
accompagnement chevauche la période si `debut < fin_consultation` et si sa
fin est absente ou postérieure au début de consultation.

| Indicateur | Définition |
| --- | --- |
| Ménages accompagnés | Nombre de ménages distincts ayant au moins un accompagnement chevauchant la période |
| Accompagnements | Nombre d'épisodes d'accompagnement chevauchant la période |
| Personnes avec séjour | Nombre de personnes distinctes bénéficiaires d'au moins un séjour chevauchant la période |
| Séjours | Nombre d'épisodes de séjour chevauchant la période |
| Admissions | Nombre de débuts de séjour dans la période |
| Sorties | Nombre de fins de séjour dans la période (fin exclue) |
| Nuitées théoriques | Pour chaque séjour, jours d'intersection × nombre de bénéficiaires explicitement rattachés ; puis somme |
| Repas distribués | Somme des quantités enregistrées dans la période, hors distributions annulées |

**Limites importantes** : les nuitées sont des nuitées théoriques d'hébergement,
non des présences constatées. Les absences ne sont pas déduites et deux séjours
simultanés peuvent contribuer deux fois pour une personne. Les bénéficiaires
sont ceux actuellement rattachés à chaque séjour : ce premier indicateur ne
reconstitue pas une composition historique. Les repas sont des réalisations
saisies, et non des droits accordés. Les sorties sont des fins de séjours,
non des sorties définitives de l'établissement.

Ces indicateurs ne mesurent ni l'occupation des places ni les capacités,
ni les trajectoires sociales. Les agrégats ne sont pas ventilés par professionnel
et ne doivent pas servir à classer les équipes.

L'accès à la page nécessite les permissions de lecture sur les accompagnements,
les séjours et les distributions. Aucun droit nouveau n'est accordé par défaut.
