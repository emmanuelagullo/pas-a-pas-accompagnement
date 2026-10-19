# Consignes pour les agents

Lire README.md et ARCHITECTURE.md. #SOC1 est un prototype local sur données
fictives, pas une application exploitable avec des dossiers réels.
Ne pas copier les modèles scolaires, ni créer d'équivalences école/CHRS ou
classe/service. Les comptes et personnes accompagnées sont distincts.
Préserver le modèle utilisateur et ses migrations ; ne pas changer
AUTH_USER_MODEL par simple renommage. Les permissions sont contrôlées dans
les vues, y compris si les boutons sont cachés. Pas de nouveau droit implicite.
Conserver les écrans en français, les formulaires accessibles et CSRF.
Vérifier `python manage.py check`, `python manage.py test`,
`python manage.py makemigrations --check --dry-run` et `git diff --check`.
Commits français avec #SOC. Utiliser l’identité de commit explicitement
indiquée ; si elle n’est pas précisée, la demander avant de créer les commits.
Livraison par patch git am, sans Signed-off-by.

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
Aucune release/site CHRS automatique. Tester le refus d'un bundle --test lors
de la préparation du candidat ; les tests Gunicorn restent loopback.

#SOC6c : lire DEPLOIEMENTS.md. Le profil Render est jetable et refuse tout
emplacement existant ; le persistant ne crée aucun compte ni fiche. Les essais
utilisent les scripts réels, des dossiers temporaires et un Gunicorn loopback.
Ne pas assimiler cette qualification SQLite à PostgreSQL/S3 ou à la production.
Les promotions vérifient projet, commit, tag, job et empreintes ; aucune
reconstruction ni remplacement d'une release existante. Préserver les jobs
manuels, les secrets hors dépôt et la séparation des projets Pages. Toute
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
