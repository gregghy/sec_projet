# Protocole BSHIP cours systèmes et réseaux 2024–2025

## Fonctionnalités

- choisir son pseudo --- **obligatoire** au début
- créer un partie
- rejoindre un partie
- quitter un partie
- annoncer les arrivées et départs d'un partie
- lister les pseudos des membres du partie
- envoyer des messages à un partie
- placement des bateaux
- jouer un coup (tirer)
- indiquer si un tir touche ou non
- indiquer si un bateau a été coulé
- indiquer si un joueur a perdu
- indiquer si un joueur a gagné
- indiquer si un joueur a été touché

-----

## Protocole

### Connexion et pseudo

### Rejoindre une partie

```
clt: HELLO <pseudo>
srv: HELLO <pseudo>
```

### quitter la partie

```
clt: LEAVE
srv: OKAY!                             // au client
srv: LEAVE <pseudo>       // aux membres du partie

```

### lister les membres de la partie

```
clt: LSMEM
srv: LSMEM <pseudo>       // nom de membres

```
### créer une partie

```
clt: START          // Démarrer la partie avec les joueurs présents on peux les voir avec LSMEM
srv: OKAY!
srv: "Exemple : SHIPS A1:A2"

```

### Placement des bateaux

Le client envoie **une seule ligne** : (pas forcement a voir encore)

```

clt: SHIPS <coord1>:<coord2>:...   // coordonnée bateau 1 format : "A1:A2:A3"
srv: OKAY!   
etc ...
```

Quand tous les joueurs ont placé leurs bateaux :

### lancer la partie qu'on est prêt

À chaque début de tour :

```
srv: TURNP <pseudo> // Indique à tous les joueurs à qui est le tour
````
## Commandes de jeu

### Jouer un coup (tirer)

```
clt: PLAYS <coord>                // Exemple : PLAYS B5
srv: OKAY!                        // au client qui tire
srv: PLAYS <pseudo> <coord>       // envoyé à chaque cible (tous les adversaires encore en jeu)
```

Chaque cible répond ensuite :

```
clt: TOUCH <0|1>                  // 1 = touché, 0 = raté
```

Le serveur transmet le résultat au tireur :

```
srv: TOUCH <pseudo> <0|1>         // pseudo = pseudo de la cible, 1 = touché, 0 = raté
```

Si un bateau coule, le serveur en informe tous les joueurs :

```
srv: COULE <pseudo>      // pseudo = pseudo de la cible, bateau = nom du bateau
```

Quand toutes les cibles ont répondu, le serveur passe au joueur suivant :

```
srv: TURNP <pseudo>               // Indique à tous les joueurs à qui est le tour
```

### Fin de partie

```
clt: PERDU
srv: OKAY!
srv: PERDU <pseudo>
srv: GAGNE <pseudo>   // si dernier joueur restant

```

## envoyer un message dans un partie
### pour l'instant on garde le chat
```
clt: SPEAK <message>
srv: SPEAK <pseudo> <message>
```

# Formats

## pseudo et nom de partie

`[a-zA-Z0-9_-]{1,16}`

### Erreurs

```
## ERROR 0 génériques
    ERROR 00 : erreur côté serveur (générique)
ERROR 1X : erreur de protocole
    ERROR 10 : arguments invalides
    ERROR 11 : commande inexistante
ERROR 2X : erreur de connexion
    ERROR 20 : pseudo invalide
    ERROR 21 : pseudo déjà pris
ERROR 3X : erreur de partie
    ERROR 30 : nom de partie invalide
    ERROR 31 : partie inexistante
    ERROR 32 : partie existante
    ERROR 33 : erreur nombre de joueurs
    ERROR 34 : pas dans la partie
    ERROR 35 : déjà dans la partie
    ERROR 36 : partie pleine
    ERROR 37 : trop de bateaux
ERROR 4X : erreur de jeu
    ERROR 40 : coordonnées invalides
    ERROR 41 : forme invalide
    ERROR 42 : nombre incorrect de bateaux
    ERROR 43 : pas à son tour
    ERROR 44 : déjà tiré sur cette case
```

