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
# Dictionnaire des enchères qui sont en cours
class Auction:
    def __init__(self, id: int, name: str, min_price: int, increment: int, duration: int, creator: User):
        self.id = id
        self.name = name
        self.min_price = min_price
        self.increment = increment
        self.duration = duration
        self.creator = creator
        self.current_bid: int = 0
        self.leader: User | None = None
        self.participants: set[User] = set()
        self.start_time: float = time.time()

    def get_time_left(self) -> int:
        elapsed = time.time() - self.start_time
        return max(0, int(self.duration - elapsed))

auctions: dict[int, Auction] = {}
auction_id: int = 0 # increment by 1 for each auction started

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
    
    u: User | None = find_user(sock)

    if u:
        u.last_activity = time.time()
        u.missed_pings = 0

    # PING <ts> : keep-alive (autorisé même si non authentifié)
    if line.startswith('PING'):
        parts = line.split()
        if len(parts) != 2:
            send_line(sock, "ERROR 10 invalid syntax")
            return
        ts = parts[1]
        if u:
            u.last_activity = time.time()
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
        #return send_line(sock, "ERROR 20 Auth failed.")
        send_line(sock, "ERROR 20 Auth failed.")
        return exit(0)
    
    # Help
    if line == 'HELP':
        send_line(sock, "HELP available commands:")
        send_line(sock, "  SPEAK <msg>: send a message")
        send_line(sock, "  LSMEM: list connected users")
        send_line(sock, "  CREAT <auction_name> <min_price> <increment> <duration_sec>: put up an auction")
        send_line(sock, "  LSAUC: list all running auctions")
        send_line(sock, "  ENTER <auction_id>: enter an auction")
        send_line(sock, "  BID <auction_id> <amount>: make a bid for a given auction")
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

    global auction_id

    # CREAT <auction_name> <min_price> <increment> <duration_sec>
    if line.startswith('CREAT '):
        parts = line.split()
        if len(parts) != 5:
             send_line(sock, "ERROR 10 invalid syntax")
             return

        name = parts[1]
        try:
            min_price = int(parts[2])
            increment = int(parts[3])
            duration = int(parts[4])
        except ValueError:
            send_line(sock, "ERROR 33 invalid parameters (must be integers)")
            return

        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,16}', name):
            send_line(sock, "ERROR 30 invalid auction name")
            return
        
        if min_price < 1 or increment < 1 or duration < 1:
             send_line(sock, "ERROR 33 invalid parameters (must be positive)")
             return

        auction_id += 1
        new_auction = Auction(auction_id, name, min_price, increment, duration, u)
        auctions[auction_id] = new_auction
        
        send_line(sock, "OKAY! %d", auction_id)
        broadcast("CREAT %d %s %d %d %d", auction_id, name, min_price, increment, duration)
        print(f"Auction {auction_id} created by {u.pseudo}")
        return
    
    if line == 'LSAUC':
        active_auctions = [a for a in auctions.values() if a.get_time_left() > 0]
        send_line(sock, "LSAUC %d", len(active_auctions))
        for a in active_auctions:
            send_line(sock, "%d %s %d %d %d %d", a.id, a.name, a.min_price, a.current_bid, a.get_time_left(), len(a.participants))
        return

    if line == 'ENTER': #TODO
        send_line(sock, "TODO entrer dans enchère")
        return
    
    if line.startswith('BID '):
        parts = line.split()
        if len(parts) != 3:
            send_line(sock, "ERROR 10 invalid syntax")
            return
        try:
            auc_id = int(parts[1])
            amount = int(parts[2])
        except ValueError:
            send_line(sock, "ERROR 33 invalid parameters (must be integers)")
            return

        auction = auctions.get(auc_id)
        if not auction:
            send_line(sock, "ERROR 31 auction not found")
            return
        if auction.get_time_left() <= 0:
            send_line(sock, "ERROR 39 auction ended")
            return

        min_required = auction.min_price if auction.current_bid == 0 else auction.current_bid + auction.increment
        if amount < min_required:
            send_line(sock, "ERROR 38 bid too low")
            return

        auction.current_bid = amount
        auction.leader = u
        auction.participants.add(u)

        send_line(sock, "OKAY!")
        pseudo_anon = hashlib.sha256(u.pseudo.encode()).hexdigest()[:8]
        broadcast("BID %s %d %d", pseudo_anon, amount, auc_id)
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

# Détecte les enchères finies
def check_auctions() -> None:
    """Vérifie les enchères terminées."""
    to_remove = []
    for a in auctions.values():
        if a.get_time_left() <= 0:
            to_remove.append(a.id)
            if a.leader:
                broadcast("WIN %s %d %d", a.leader.pseudo, a.current_bid, a.id)
            else:
                broadcast("END %d NO_BIDS", a.id)
            print(f"Auction {a.id} ended.")
            
    for id in to_remove:
        del auctions[id]

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
                check_auctions()
        except KeyboardInterrupt:
            print("\nArrêt du serveur")
