# Protocole d'enchères (v1.2)

# TODO : gérer les erreurs et me relire svp

# Note :
Attention Exit =/= LEAVE (quitter l'enchère vs quitter le serveur)

## Format général
- UTF‑8, une commande par ligne, terminée par "\n"
- Champs séparés par un espace
- Longueur max d’une ligne: MAX_LINE
- Pseudos et noms d’enchère: `[a-zA-Z0-9_-]{1,16}`
- Montant: entier positif en centimes (≥1)
- Durée: entier en secondes (≥1)

## États
- CONNECTED → AUTHENTICATED → IN_AUCTION

## Connexion et inscription
- srv: BIDS 1.2

### Inscription - création de Client: ajouteClient
- clt: SIGN <pseudo> <pwd_hash> <pubkey>
- srv: OKAY! | ERROR 41

### Auth - vérif MDP avec authentification():
- clt: HELLO <pseudo>
- srv: CHALL <nonce_int> # faire un challenge nonce en int en hexadécimal (pas encore d'idée de quoi choisir comme nonce)
- clt: AUTH <hmac_int>
- srv: HELLO <pseudo> | ERROR 42

### Déconnexion
- clt: LEAVE
- srv: OKAY!

## Keep‑alive (vérifier les déconnexions)
- clt: PING <ts>
- srv: PONG <ts> 

## Chat (optionnel)
- clt: SPEAK <msg>
- srv: SPEAK <pseudo> <msg>      (broadcast)

## Fonctionnement des enchères

### Création (ajouteEnchere)
- clt: CREAT <auction_name> <min_price> <increment> <duration_sec>
- srv: OKAY! <auction_id> | ERROR 30 | ERROR 32 | ERROR 33
- srv: CREAT <auction_id> <auction_name> <min_price> <increment> <duration_sec>   (broadcast)

### Entrer / Quitter une enchère (entrerEnchere / quitterEnchere)
- clt: ENTER <auction_id>
- srv: OKAY! | ERROR 31 | ERROR 39 | ERROR 35
- srv: STATE <auction_id> <auction_name> <current_bid> <leader_anonymous> <time_left>
- srv: ENTER <pseudo> <auction_id>   (broadcast)
- clt: EXIT <auction_id>
- srv: OKAY! | ERROR 31 | ERROR 34
- srv: EXIT <pseudo> <auction_id>    (broadcast) 

### Liste des enchères (listeEncheresEnCours)
- clt: LSAUC                      (Liste toutes les enchères actives)
- srv: LSAUC <nb>
- srv: <auction_id> <auction_name> <current_bid> <time_left> <nb_bidders>  (répété <nb> fois)

### Etat de l'enchère 
- clt: STATE <auction_id>
- srv: STATE <auction_id> <auction_name> <current_bid> <leader_anonymous> <time_left> | ERROR 31

### Proposition d'enchère (propositionEnchere())
- clt: BID <auction_id> <amount>
- srv: OKAY!
- srv: BID <pseudo_anonymous> <amount> <auction_id>  (broadcast si meilleure offre / Note: pseudo_anonymous est un hash pour l'anonymat jusqu'à la fin de l'enchère)
- srv : BID ERROR si offre trop basse ou enchère terminée

### Consultation des enchères remportées précédemment (consulteEncheresRemportees)
- clt: WHOWIN
- srv: WHOWIN <nb>
- srv: <auction_id> <auction_name> <final_amount> <win_timestamp>  (répété nb fois)

## Fin d'enchère (automatique avec clotEnchere + reveleGagnant)
- srv: WARN <auction_id> <seconds_left>      (ex: 60, 30, 10 secondes avant la fin)
- srv: WIN <pseudo> <amount> <auction_id>    (broadcast – pseudo en clair)
- srv: END <auction_id> NO_BIDS              (si aucune offre)


## Codes d'erreur

ERROR 10: syntaxe invalide
ERROR 11: commande inexistante
ERROR 12: ligne trop longue (> MAX_LINE)
ERROR 20: non authentifié
ERROR 21: déjà authentifié
ERROR 30: nom d’enchère invalide
ERROR 31: enchère inexistante
ERROR 32: enchère déjà existante
ERROR 33: paramètres invalides (prix/durée)
ERROR 34: pas dans l'enchère
ERROR 35: déjà dans l'enchère
ERROR 38: offre trop basse (< current_bid + increment)
ERROR 39: enchère terminée
ERROR 40: pseudo invalide
ERROR 41: pseudo déjà pris
ERROR 42: authentification échouée
ERROR 43: clé publique invalide (si utilisée)
ERROR 45: trop de requêtes (rate limit)
ERROR 47: version non supportée
ERROR 48: erreur interne