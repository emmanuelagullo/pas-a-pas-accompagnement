# Authentification du prototype — #SOC4b

Les comptes professionnels restent dans `identites.Utilisateur`. Ils ne sont
ni des personnes accompagnées ni des comptes partagés avec Petits Pas.
Cette étape ne crée aucun rôle social ou périmètre d’établissement.
Le prototype reste réservé à un espace unique et à des données fictives.

## Profil serveur d’essai

Installer les dépendances et appliquer les migrations :

```sh
python -m pip install -r requirements.lock -r requirements-2fa.txt
python manage.py migrate
```

Les variables suivantes appartiennent à cette application :

| Variable | Valeurs et effet |
| --- | --- |
| `ACCOMPAGNEMENT_2FA` | `desactive` (défaut), `optionnel` ou `obligatoire`. L’obligation s’applique à tous les comptes de cet espace, sans distinction de rôle. |
| `ACCOMPAGNEMENT_2FA_CLES` | Clés Fernet dédiées, séparées par des virgules. La première chiffre ; toutes peuvent déchiffrer. Ne pas employer la clé Django ou une clé Petits Pas. |

Générer une clé sur le poste d’administration, la conserver dans la configuration
privée du déploiement puis définir ces variables avant de démarrer le processus :

```sh
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Ne jamais inscrire une vraie clé dans Git, une capture, un exemple, un ticket ou
les logs. Pour les essais, `ACCOMPAGNEMENT_2FA=optionnel` permet l’activation
individuelle ; `obligatoire` bloque immédiatement les fiches jusqu’à l’inscription.
La clé et les dépendances manquantes, un mode inconnu ou une clé mal formée sont
refusés au démarrage lorsque le profil serveur demande le 2FA.

`desactive` ne retire jamais une protection existante : un compte déjà inscrit
ou marqué à réinscrire reste bloqué tant que le service n’est pas utilisable.
Retirer une variable ou ouvrir la base dans le programme autonome ne contourne
pas le facteur. Restaurer la configuration ou utiliser la procédure technique
explicite décrite plus bas. Il n’y a pas de désactivation silencieuse.

## Parcours utilisateur

1. Se connecter avec le mot de passe, puis ouvrir **Sécurité du compte**.
2. Confirmer le mot de passe pour préparer le QR et la clé de saisie manuelle.
3. Ajouter le compte dans une application TOTP, puis confirmer le mot de passe
   et un premier code du téléphone.
4. Conserver les dix codes de secours affichés une seule fois, séparément du
   téléphone. Chaque code ne peut servir qu’une fois.

Le compte connecté est affiché dans la navigation ; se déconnecter avant de
changer de compte sur le même navigateur.

Après activation, le mot de passe ouvre une attente de cinq minutes, pas une
session authentifiée. Un code TOTP ou de secours valide termine la connexion.
Les permissions `view_personne` et `add_personne` restent indispensables ; le
second facteur n’accorde aucun droit métier, y compris au premier compte.

Les comptes soumis à l’obligation peuvent seulement s’inscrire ou se déconnecter
avant d’accéder aux fiches. Une session née sans preuve actuelle est fermée.
La révision du facteur est vérifiée à chaque requête protégée : une ancienne
preuve ne redevient pas valide après remplacement ou réinitialisation.

**Changer mon mot de passe** demande le mot de passe actuel et les validations
habituelles. La session courante reste connectée ; les autres sessions et les
attentes de connexion utilisant l’ancien mot de passe ne sont plus valides.
Le second facteur n’est pas retiré par un changement de mot de passe.

## Téléphone perdu ou remplacé

Avec le mot de passe et un code de secours, se connecter puis choisir
**Remplacer mon téléphone**. Confirmer à nouveau le mot de passe et un autre
code de secours (ou un code du téléphone encore utilisable). Les anciens
secrets, secours et sessions sont révoqués ; la session courante est limitée
à la nouvelle inscription tant qu’elle n’est pas terminée.

**Renouveler les codes de secours** exige le mot de passe et un facteur à usage
unique. Les anciens secours et les autres sessions sont révoqués, et les dix
nouveaux codes ne sont affichés qu’une fois. Le téléphone reste inscrit.
**Retirer le second facteur** exige les mêmes confirmations et n’est proposé
que si le déployeur ne l’impose pas. Le serveur refuse aussi un POST direct
qui tenterait de contourner cette règle.

## Récupération par l’administration technique

Aucune permission métier ne permet de réinitialiser le facteur d’un autre compte.
Il n’existe pas de lien public de récupération ni de récupération par courriel.
L’accès au terminal et à la configuration privée est réservé à l’administration
technique de l’essai. Vérifier humainement le demandeur par un canal convenu,
puis, dans le profil serveur 2FA configuré et utilisable :

```sh
python manage.py reinitialiser_double_facteur nom-utilisateur --confirmer
```

La commande supprime le secret et les secours, change la révision, ferme les
sessions DB du compte et impose une inscription avant tout accès aux fiches.
Les attentes existantes ne peuvent pas valider le nouveau facteur. Elle ne
change ni le mot de passe, ni le statut actif, ni les permissions du compte.
Si le mot de passe est également perdu, utiliser la commande Django interactive
`python manage.py changepassword nom-utilisateur`, après la même vérification
humaine. Cette commande ne retire pas le second facteur.

Une reprise volontaire dans un profil sans 2FA nécessite une opération distincte :

```sh
# Uniquement en profil désactivé ou local ; jamais en profil serveur 2FA actif :
python manage.py reinitialiser_double_facteur nom-utilisateur --confirmer --profil-sans-2fa
```

Pour le dossier d’un programme autonome, fermer le programme et définir
`ACCOMPAGNEMENT_DONNEES` vers son dossier et `DJANGO_SETTINGS_MODULE` vers
`pas_a_pas_accompagnement.settings_local`. L’option retire explicitement la
protection et l’obligation de réinscription pour ce compte, sans lui ajouter
de droit. Elle est refusée dans un profil serveur 2FA actif. Sauvegarder avant
une opération de récupération ; ne pas publier cette copie.

## Clés, sauvegardes et rotation

Les clés de chiffrement ne sont jamais placées dans les sauvegardes par
l’application. La base contient le secret chiffré, le dernier pas accepté,
la révision et les seules empreintes des secours. Le QR et la clé en cours
ne s’affichent qu’après confirmation du mot de passe ; les pages sensibles
portent `Cache-Control: no-store` et sont protégées par CSRF et contre l’encadrement. Les diagnostics Django
masquent aussi les clés et les champs sensibles, même dans le profil DEBUG.

Lors d’une rotation, placer la nouvelle clé en tête tout en gardant les anciennes.
Les inscriptions nouvelles utilisent la première ; les secrets déjà chiffrés
restent lisibles grâce aux anciennes. Il n’y a pas de rechiffrement automatique
massif : ne pas retirer une ancienne clé tant que les comptes concernés n’ont
pas été réinscrits avec une nouvelle clé. Un secret illisible ne déclenche jamais
une nouvelle inscription silencieuse d’un compte confirmé. Avec une nouvelle
configuration valide, un secours restant peut permettre le remplacement du
téléphone ; sinon utiliser la récupération technique.

Une restauration indépendante conserve les facteurs, les révisions et les
secours déjà consommés. Elle supprime uniquement les sessions et les compteurs
transitoires dans la copie, sans modifier le dossier source. Une copie ancienne
reste un instantané : elle peut contenir un ancien état des secours. Ne pas
utiliser plusieurs copies comme des répliques synchronisées. La configuration
privée des clés doit être sauvegardée et conservée séparément.

## Tentatives, sessions et journaux

Les saisies de connexion, vérification et gestion sont limitées dans des fenêtres
fixes de quinze minutes : cinq par compte, trente par adresse pour chaque usage.
Les réussites comptent aussi. Les compteurs HMAC ne stockent ni IP ni identifiant
en clair. Les opérations sont atomiques en base et partagées entre processus ;
une erreur du stockage refuse l’essai. Une fenêtre fixe peut permettre des
rafales de part et d’autre de sa frontière ; ce n’est pas une fenêtre glissante.
Les limites sont fixes pour ce prototype et ne dépendent pas des rôles.
L’adresse est `REMOTE_ADDR` : les en-têtes de proxy ne sont pas acceptés.
Configurer et qualifier une chaîne de proxy avant un déploiement derrière proxy.

Supprimer régulièrement les seules fenêtres expirées, sans lever les blocages
actuels : `python manage.py purger_limites_authentification`. Cette tâche reste
à planifier dans l’exploitation ; aucune automatisation externe n’est créée.

Les sessions sont en base, limitées à une heure et expirent à la fermeture du
navigateur. Cookies propres au produit, session HttpOnly et SameSite=Lax,
CSRF, déconnexion POST et plafond de 1 024 caractères sont conservés.
Les profils actuels servent en HTTP sur boucle locale : les cookies n’y sont
pas Secure. Ils ne constituent pas un profil réseau de production ; HTTPS,
cookies Secure et exploitation restent le chantier serveur #SOC6.

Le logger `identites.securite` écrit les événements techniques sur stderr :
connexion/refus, usage d’un secours, activation, renouvellement, remplacement,
retrait, changement de mot de passe et récupération au terminal. Il mentionne
l’ID technique du compte quand il est connu, jamais les mots de passe, codes,
QR ou clés. L’événement terminal ne prouve pas l’identité humaine de l’opérateur.
La collecte et la durée de conservation des logs restent à définir à l’exploitation ;
ce n’est pas un historique métier ni un journal réglementaire pérenne.

## Vérification

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python scripts/verifier-authentification.py
```

Le banc HTTP crée une base et une clé éphémères sur données fictives. Les tests
exercent aussi deux connexions concurrentes : un code ne réussit qu’une fois,
y compris sur SQLite où les verrous de ligne ne sont pas disponibles.
La CI serveur installe les dépendances crypto pour que ces tests ne soient pas
ignorés. La CI bureau teste le profil sans crypto ; les essais graphiques
Windows/GTK restent distincts de ces contrôles HTTP.

### Régression PostgreSQL : secours à usage unique

La CI PostgreSQL a révélé un double succès avec l’ancienne requête de
consommation. Une jointure Django déplaçait le filtre `utilise_le IS NULL`
dans une sous-requête, sans réévaluation utile après l’attente du verrou.
Ce filtre reste désormais sur la ligne mise à jour ; une sous-requête explicite
séparée contrôle la révision du facteur. Le test PostgreSQL attend que deux
connexions soient bloquées sur le même code avant de libérer son verrou.
Le reset concurrent est testé séparément. Les clés et codes existants sont
conservés ; aucune migration n’est nécessaire.
