#!/usr/bin/env python3
import socket
import selectors
import sys
import re
import hashlib # for hashing passwords later. probably use sha256.
import time

MAX_LINE: int = 256

class User:
    def __init__(self, sock: socket.socket, username: str = "") -> None:
        self.sock: socket.socket = sock
        self.addr = sock.getpeername()
        self.pseudo: str = username
        self.authenticated: bool = False

users: list[User] = []
sel: selectors.DefaultSelector = selectors.DefaultSelector()
buf: dict[socket.socket, str] = {}  # Buffers pour chaque socket

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
    sel.register(conn, selectors.EVENT_READ, data=True)
    buf[conn] = ''
    print(f"Nouvelle connexion {addr}")
    send_line(conn, "BIDS 1.0")  # Message de bienvenue

def disconnect(sock: socket.socket) -> None:
    """Déconnecte un client"""
    try:
        addr = sock.getpeername()
        print(f"Déconnexion {addr}")
    except OSError:
        print("Déconnexion socket inconnu")
    
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

def broadcast(msg: str, *args, exclude = None) -> None:
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
    """Traite une commande reçue d'un client"""
    u: User | None = find_user(sock)
    
    # HELLO <pseudo> [<password>] : authentification
    if line.startswith('HELLO '):
        parts: list[str] = line[6:].split()
        if len(parts) < 1:
            return send_line(sock, "ERROR 40 pseudo invalide")
        
        pseudo = parts[0]
        password = parts[1] if len(parts) > 1 else None
        
        # Vérification du format du pseudo
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,16}', pseudo):
            return send_line(sock, "ERROR 40 pseudo invalide")
        
        # Vérification si pseudo déjà pris
        if any(u.pseudo == pseudo for u in users):
            return send_line(sock, "ERROR 41 pseudo déjà pris")
        
        # Crée ou met à jour l'utilisateur
        if not u:
            u = User(sock)
            users.append(u)
        
        u.pseudo = pseudo
        u.authenticated = True
        
        send_line(sock, "HELLO %s", pseudo)
        broadcast("HELLO %s", pseudo, exclude=sock)
        print(f"Utilisateur {pseudo} authentifié")
        return
    
    # Vérification de l'authentification pour les commandes suivantes
    if not u or not u.authenticated:
        return send_line(sock, "ERROR 20 non authentifié")
    
    # SPEAK <msg> : message de chat
    if line.startswith('SPEAK '):
        msg = line[6:]
        broadcast("SPEAK %s %s", u.pseudo, msg)
        print(f"Message de {u.pseudo} : {msg}")
        return
    
    # LSMEM : liste des utilisateurs connectés
    if line == 'LSMEM':
        send_line(sock, "LSMEM %d", len(users))
        for user in users:
            send_line(sock, "%s", user.pseudo)
        print(f"LSMEM demandé par {u.pseudo}")
        return
    
    # LEAVE : déconnexion
    if line == 'LEAVE':
        send_line(sock, "OKAY!")
        broadcast("LEAVE %s", u.pseudo, exclude=sock)
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
                for key, _ in sel.select():
                    if key.data is None:
                        accept_wrapper(key.fileobj)
                    else:
                        handle_socket(key.fileobj)
        except KeyboardInterrupt:
            print("\nArrêt du serveur")