# Export d'une personne — SOC7b

Le lien Télécharger la fiche PDF appelle une vue GET/HEAD avec connexion et
permission personnes.view_personne ; aucune permission de création requise.
Une personne inconnue est refusée, sans génération. Les réponses sont privées
et non conservables en cache ; le nom du fichier contient un UUID, sans nom
d'usage. Les textes HTML sont échappés et aucun fichier, média ou réseau n'est
autorisé par le récupérateur de cette fiche native.

Contenu : désignation, prénom s'il existe, identifiant stable, création et
date d'édition. Pas de compte professionnel créateur dans le document.
Aucun fichier PDF n'est enregistré dans la base ou dans les médias.

En serveur/bureau, le template personnes/fiche_pdf.html et la feuille
static/fiche-pdf.css passent par le moteur natif commun. Le programme Windows
nécessite les DLL Pango du profil de construction, comme Petits Pas.

En PWA, le même contenu est composé en texte via le backend facultatif du
socle (fpdf2, FontTools, DejaVu Sans et Pillow du runtime Pyodide). Les PDF
ont une mise en page propre à ce backend ; la police ne couvre pas tous les
systèmes d'écriture. Un caractère non représentable produit une erreur 422
sans révéler le diagnostic interne. Aucun recours distant à un convertisseur.
La PWA Petits Pas conserve son impression navigateur ; elle n'emploie pas
ce backend pour remplacer les carnets avec images.

Tests : personnes.tests_pdf (droits avant rendu, vrai PDF, échappement, ressource
externe refusée, backend PWA, erreur privée), tests du socle (Unicode, pagination),
vrai Pyodide et téléchargement Chromium hors ligne. Les parcours d'authentification
et les copies conservent leurs limites et politiques. Cette fonction reste sur
données fictives et ne qualifie pas l'exploitation de dossiers réels.

## Restitutions des aides — méta-lot C

L'autorisation d'aide et son relevé de réalisation peuvent être téléchargés en
PDF sous les droits complets de lecture de cette prestation. Moteur HTML natif
serveur/bureau et fiche texte du socle en PWA, même contenu sans ressource externe.
Réponses privées no-store, nom de fichier fondé sur l'UUID, erreur de caractères
sans diagnostic interne. Aucun fichier PDF n'est enregistré dans la base.
Le document distingue autorisation, remises actives/annulées et utilisation
déclarée ; il ne compte aucun trajet depuis une carte. Il restitue le courant :
numérotation d'émission, montant facturé, signature habilitée et réédition figée
relèvent du méta-lot D. Les impressions HTML restent également disponibles.

## Documents financiers émis — méta-lot D

Les trois gabarits engagement/prescription/relevé figent les textes et coordonnées
lors de l'émission, dans `DocumentFinancement`. Le numéro PAP et l'empreinte du
contenu sont restitués ; les rééditions réutilisent le contenu conservé, même si
le calcul ou le répertoire a été corrigé. Une annulation est affichée en tête,
sans modifier ce contenu. La stabilité porte sur le contenu métier, pas sur les
octets PDF ni une signature électronique. Aucun PDF binaire n'est stocké, aucun
rendu distant n'est utilisé. Droits complets de financement et de la prestation
contrôlés avant lecture ; réponses privées no-store, caractères non représentables
refusés avec message 422 privé, sans diagnostic interne.

## Appels, relève et exploration — E

La synthèse d'appel peut restituer une ancienne version sélectionnée ; les
répertoires sont des identités liées et leurs libellés courants peuvent avoir été
corrigés. Ce document reste une restitution, pas une émission financière figée.
La relève indique date déclarée ou repli explicite sur la saisie, auteur initial,
dernière correction et annulation éventuelle. L'exploration conserve dans son PDF
les paramètres de population, période, référence, mesures et classes, les totaux
recalculés et les unités. Même rendu de contenu en HTML/texte natif ou PWA, sans
réseau, privé no-store ; caractères non représentables refusés sans diagnostic.
Les tests PDF PWA se déclarent ignorés si la dépendance facultative fpdf2 manque,
sans réduire le contrat des profils où elle est installée.
