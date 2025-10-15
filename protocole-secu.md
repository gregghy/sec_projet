# Protocole d'enchères (v1.1)

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
srv: BIDS 1.1.1

### Inscription - création de Client: ajouteClient
clt: SIGN <pseudo> <pwd_hash> <pubkey>
srv: OKAY! | ERROR 41

### Auth - vérif MDP avec authentification():
clt: HELLO <pseudo>
srv: CHALL <nonce_int> # faire un challenge nonce en int en hexadécimal (pas encore d'idée de quoi choisir comme nonce)
clt: AUTH <hmac_int>
srv: HELLO <pseudo> | ERROR 42

### Déconnexion
clt: BYE
srv: OKAY!

## Gestion des enchères

### Création (ajouteEnchere)
clt: CREAT <auction_name> <min_price> <increment> <duration>
srv: OKAY! <auction_id>
srv: CREAT <auction_id> <auction_name> <min_price> <increment> <duration_sec>  # broadcast

### Liste des enchères (listeEncheresEnCours)
clt: LSAUC                      # Liste toutes les enchères actives
srv: LSAUC <nb>
srv: <auction_id> <auction_name> <current_bid> <time_left> <nb_bidders>  # répété <nb> fois

### Entrée dans une enchère
clt: ENTER <auction_id>
 srv: OKAY!
srv: STATE <auction_id> <auction_name> <current_bid> <leader_anonymous> <time_left>
srv: ENTER <pseudo> <auction_id>  # broadcast

### Proposition d'enchère propositionEnchere()
clt: OFFRE <auction_id> <amount>
srv: OKAY!
srv: BID <pseudo_anonymous> <amount> <auction_id>  # broadcast si meilleure offre / Note: pseudo_anonymous est un hash pour l'anonymat jusqu'à la fin de l'enchère

### Consultation des enchères remportées avec consulteEncheresRemportees()
clt: WHOWIN
srv: WHOWIN <nb>
srv: <auction_id> <auction_name> <final_amount> <win_timestamp>  # répété <nb> fois

## Fin d'enchère automatique avec clotEnchere + reveleGagnant
srv: WARN <auction> <seconds_left>      # 60s, 30s, 10s avant la fin
srv: WIN <pseudo> <amount> <auction>    # pseudo broadcast à tous en clair
srv: END <auction> NO_BIDS              # Aucune offre

## Codes d'erreur
ERROR 30 : nom d'enchère invalide
ERROR 31 : enchère inexistante
ERROR 32 : enchère déjà existante
ERROR 33 : paramètres invalides (prix/durée)
ERROR 34 : pas dans l'enchère
ERROR 35 : déjà dans l'enchère
ERROR 38 : offre trop basse (< current_bid + increment)
ERROR 39 : enchère terminée
ERROR 40 : pseudo invalide
ERROR 41 : pseudo déjà pris
ERROR 42 : enchère n'a pas pu être authentifiée
