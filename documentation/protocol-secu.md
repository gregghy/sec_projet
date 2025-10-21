# Protocole d'enchères (v1.1)

## Format général
- UTF‑8, une commande par ligne, terminée par "\n"
- Champs séparés par un espace
- Longueur max d’une ligne: MAX_LINE
- Pseudos et noms d’enchère: `[a-zA-Z0-9_-]{1,16}`
- Montant: entier positif en centimes (≥1)
- Durée: entier en secondes (≥1)

## États
- CONNECTED: first connection, receive login request
- AUTHENTICATED: login request satisfied
- LISTING X: selling X through an auction 
- OFFERING TO X: making an offer for X 

## Connexion
srv: BIDS 1.1
clt: HELLO <pseudo> <password>          # Temporaire, sera hashé en v2
srv: HELLO <pseudo> | ERROR <code>

## Gestion des enchères
clt: CREATE <auction_id> <min_price> <increment> <duration>
srv: OKAY! <auction_id>
src: START <auction_id> <bid> <increment> <duration>
srv: BROADC <pseudo> <auction_id> <min_price> <increment> <duration_sec>  # broadcast

clt: LSAUC                              # Liste toutes les enchères actives
srv: LSAUC <nb>
srv: <auction> <current_bid> <time_left> <nb_bidders>  # répété nb fois

clt: ENTER <auction_id>
srv: OKAY!
srv: BROADC <auction_id> <current_bid> <time_left>  # État actuel

clt: OFFER <auction_id> <amount>           # Contexte explicite
srv: OKAY!
srv: BROADC <pseudo> <amount> <auction_id>    # broadcast si nouvelle meilleure offre

## Fin d'enchère automatique
srv: BROADC <auction> <seconds_left>      # 60s, 30s, 10s avant la fin
srv: BROADC <pseudo> <realname> <amount> <auction_id>    # Un gagnant
srv: END <auction_id>                     # Aucune offre

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
