#!/usr/bin/env python3
import socket
import selectors
import sys
import re
import RSA
import hashlib # for hashing passwords later. probably use sha256.
import time

MAX_LINE: int = 256
PING_INTERVAL: float = 15.0
MAX_MISSED_PINGS: int = 5

class User:
    def __init__(self, sock: socket.socket, username: str, password) -> None:
        self.sock: socket.socket = sock
        self.addr = sock.getpeername()
        self.pseudo: str = username
        self.password: int = password
        self.authenticated: bool = False
        self.AESkey: int = 0 #TODO
        self.last_activity: float = time.time()
        self.missed_pings: int = 0

users: list[User] = []
sel: selectors.DefaultSelector = selectors.DefaultSelector()
buf: dict[socket.socket, str] = {}  # Buffers pour chaque socket
all_auctions: dict[int, list[tuple[socket.socket, int]]] = {} # {auction_id: [(socket, bid_in_cents), ...], ...}
auction_id: int = 0 # increment by 1 for each auction started
auction_timers: dict[int, float] = {} # {auction_id: time_remaining, ...}
time_at_last_check: float = time.time()

def send_line(sock: socket.socket, msg: str, *args) -> None:
    """Envoie une ligne au client"""
    line: str = (msg % args if args else msg) + '\n'
    try:
        sock.sendall(line.encode())
    except (BrokenPipeError, OSError):
        pass

def accept_wrapper(lsock) -> None:
    """Accepte une nouvelle connexion"""
    conn, addr = lsock.accept()
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, data = True)
    buf[conn] = ''
    print(f"Nouvelle connexion {addr}")
    send_line(conn, "BIDS 1.1.1 , HELP for help")  # Message de bienvenue

def disconnect(sock: socket.socket) -> None:
    """Déconnecte un client"""
    try:
        addr = sock.getpeername()
        print(f"Disconnecting {addr}.")
    except OSError:
        print("Disconnecting from unknown socket.")
    
    # Retire l'utilisateur de la liste
    global users
    users = [u for u in users if u.sock != sock]
    
    try:
        sel.unregister(sock)
    except Exception:
        pass
    try:
        sock.close()
    except Exception:
        pass
    buf.pop(sock, None)

def broadcast(msg: str, *args, exclude: socket.socket | None = None) -> None:
    """Envoie un message à tous les utilisateurs connectés"""
    for u in users:
        if u.sock is not exclude:
            send_line(u.sock, msg, *args)

def find_user(sock: socket.socket) -> User | None:
    """Trouve l'utilisateur correspondant à une socket"""
    for u in users:
        if u.sock == sock:
            return u
    return None

def handle_command(sock: socket.socket, line: str) -> None:
    """vérifie les enchères disponibles et traite une commande reçue d'un client"""
    global time_at_last_check
    now: float = time.time()
    dt: float = now - time_at_last_check
    time_at_last_check = now
    # contrary to how it might appear given the name, the float imprecision implementation will not be a major problem until over 40000 years, because python uses double-precision (64 bits) for its "float" type
    # https://stackoverflow.com/questions/52064050/what-is-the-precision-in-decimal-points-of-python-floats
    
    # vérifies les enchères en cours
    to_ignore: set[int] = set()
    for id in auction_timers.keys():
        auction_timers[id] -= dt

        if auction_timers[id] <= 0:
            #to_ignore.add(auction_id) # if it's already in to_ignore anyway, because every element in a set is unique, nothing happens here
            to_ignore.add(id) # if it's already in to_ignore anyway, because every element in a set is unique, nothing happens here

    u: User | None = find_user(sock)

    if u:
        u.last_activity = now
        u.missed_pings = 0

    # PING <ts> : keep-alive (autorisé même si non authentifié)
    if line.startswith('PING'):
        parts = line.split()
        if len(parts) != 2:
            send_line(sock, "ERROR 10 invalid syntax")
            return
        ts = parts[1]
        if u:
            u.last_activity = now
            u.missed_pings = 0
        send_line(sock, "PONG %s", ts)
        return
    
    # HELLO <pseudo> <password> : authentification
    if line.startswith('HELLO '):
        parts: list[str] = line[6:].split()
        if len(parts) < 1:
            return send_line(sock, "ERROR 40 Invalid username.")
        
        pseudo: str = parts[0]
        password = hashlib.sha256(bytes(parts[1], encoding = "utf-8")) if len(parts) > 1 else None #TODO
        
        if password is None:
            send_line(sock, "Please enter a password.")
            return
        else:
            for usr in users:
                if usr.pseudo == pseudo:
                    if usr.password != password:
                        send_line(sock, "Incorrect password.")
                        return

        # Vérification du format du pseudo
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,16}', pseudo):
            return send_line(sock, "ERROR 40 Invalid username. Must be between 1 and 16 alphanumeric characters. Only allowed special character is the underscore (_).")
        
        # Vérification si pseudo déjà pris
        if any(u.pseudo == pseudo for u in users):
            return send_line(sock, "ERROR 41 Username taken.")
        
        # Crée ou met à jour l'utilisateur
        if not u:
            u = User(sock, pseudo, password)
            users.append(u)
        
        u.pseudo = pseudo
        u.authenticated = True
        
        send_line(sock, "HELLO %s", pseudo)
        broadcast("HELLO %s", pseudo, exclude = sock)
        print(f"User {pseudo} authentified.")
        return
    
    # Vérification de l'authentification pour les commandes suivantes
    if not u or not u.authenticated:
        return send_line(sock, "ERROR 20 Auth failed.")
    
    # Help
    if line == 'HELP':
        send_line(sock, "HELP available commands:")
        send_line(sock, "  SPEAK <msg>: send a message")
        send_line(sock, "  LSMEM: list connected users")
        send_line(sock, "  CREAT: put up an auction")
        send_line(sock, "  LSAUC: list all running auctions")
        send_line(sock, "  ENTER: enter an auction")
        send_line(sock, "  BID: make a bid for a given auction")
        send_line(sock, "  PING <ts>: keep-alive, server replies PONG <ts>")
        send_line(sock, "  LEAVE: disconnect")
        return
    
    # SPEAK <msg> : message de chat
    if line.startswith('SPEAK '):
        msg = line[6:]
        broadcast("SPEAK %s %s", u.pseudo, msg)
        print(f"Message from {u.pseudo}: {msg}")
        return
    
    # LSMEM : liste des utilisateurs connectés
    if line == 'LSMEM':
        send_line(sock, "LSMEM %d", len(users))
        for user in users:
            send_line(sock, "%s", user.pseudo)
        print(f"LSMEM requested by {u.pseudo}")
        return

    global auction_id # not strictly necessary, but my typechecker is complaining about the lack of it

    if line == 'CREAT': #TODO
        min_auction: int = 0 #TODO implement setting a minimum auction

        auction_id += 1
        all_auctions[auction_id].append((sock, min_auction))
        auction_timers[auction_id] = 120.0 # 2 minutes per auction
        send_line(sock, "TODO création enchère")
        return
    
    if line == 'LSAUC': #TODO
        send_line(sock, "TODO liste enchères")
        return

    if line == 'ENTER': #TODO
        send_line(sock, "TODO entrer dans enchère")
        return
    
    if line == 'BID': #TODO
        send_line(sock, "TODO faire une offre")
        return
    
    
    # LEAVE : déconnexion
    if line == 'LEAVE':
        send_line(sock, "OKAY!")
        broadcast("LEAVE %s", u.pseudo, exclude = sock)
        print(f"Utilisateur {u.pseudo} déconnecté")
        disconnect(sock)
        return
    
    # Commande inconnue
    send_line(sock, "ERROR 11 commande inexistante")

def handle_socket(sock) -> None:
    """Traite les données reçues d'une socket"""
    try:
        data = sock.recv(4096).decode()
    except (ConnectionResetError, ConnectionAbortedError, OSError):
        disconnect(sock)
        return
    
    if not data:
        disconnect(sock)
        return
    
    buf[sock] = buf.get(sock, "") + data
    
    # Traite toutes les lignes complètes dans le buffer
    while sock in buf and '\n' in buf[sock]:
        line, buf[sock] = buf[sock].split('\n', 1)
        line: str = line.strip()
        if line:
            handle_command(sock, line)

def check_keepalive() -> None:
    """Déconnecte les clients après 5 PING manqués."""
    now = time.time()
    for u in list(users):
        elapsed = now - getattr(u, "last_activity", now)
        missed = int(elapsed // PING_INTERVAL)
        if missed > u.missed_pings:
            u.missed_pings = missed
            if u.missed_pings >= MAX_MISSED_PINGS:
                send_line(u.sock, "ERROR 30 timeout")
                print(f"Timeout: disconnecting {u.pseudo} ({u.addr})")
                disconnect(u.sock)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <port>")
        sys.exit(1)
    
    port: int = int(sys.argv[1])
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as lsock:
        lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lsock.bind(('', port))
        lsock.listen()
        lsock.setblocking(False)
        sel.register(lsock, selectors.EVENT_READ, data=None)
        
        print(f"Serveur démarré sur le port {port}")
        
        try:
            while True:
                events = sel.select(timeout = 1.0)
                for key, _ in events:
                    if key.data is None:
                        accept_wrapper(key.fileobj)
                    else:
                        handle_socket(key.fileobj)
                check_keepalive()
        except KeyboardInterrupt:
            print("\nArrêt du serveur")