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
Ne pas annoncer de sauvegarde ou récupération PWA CHRS encore absente.
