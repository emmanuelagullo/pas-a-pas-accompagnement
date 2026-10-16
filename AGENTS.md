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
