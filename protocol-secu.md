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

## Connexion
srv: BIDS 1.1
clt: HELLO <pseudo> <password>          # Temporaire, sera hashé en v2
srv: HELLO <pseudo> | ERROR <code>

## Gestion des enchères
clt: CREAT <auction> <min_price> <increment> <duration>
srv: OKAY! <auction_id>
srv: CREAT <pseudo> <auction> <min_price> <increment> <duration_sec>  # broadcast

clt: LSAUC                              # Liste toutes les enchères actives
srv: LSAUC <nb>
srv: <auction> <current_bid> <time_left> <nb_bidders>  # répété <nb> fois

clt: ENTER <auction>
srv: OKAY!
srv: STATE <auction> <current_bid> <leader> <time_left>  # État actuel
srv: ENTER <pseudo> <auction>           # broadcast

clt: OFFRE <auction> <amount>           # Contexte explicite
srv: OKAY!
srv: BID <pseudo> <amount> <auction>    # broadcast si nouvelle meilleure offre

## Fin d'enchère automatique
srv: WARN <auction> <seconds_left>      # 60s, 30s, 10s avant la fin
srv: WIN <pseudo> <amount> <auction>    # Un gagnant
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
