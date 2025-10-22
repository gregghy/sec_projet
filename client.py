#!/usr/bin/env python3
import socket
import sys
import select
import RSA
import hashlib # for hashing passwords later. probably use sha256.

MAX_PSEUDO = 16
MAX_LINE = 256

def connect_to(host: str, port: str) -> socket.socket | None:
    try:
        addrinfo = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, socktype, proto, canonname, sockaddr in addrinfo:
            try:
                fd: socket.socket = socket.socket(family, socktype, proto)
                fd.connect(sockaddr)
                return fd
            except socket.error:
                if fd:
                    fd.close()
                continue
        raise socket.error("Unable to connect.")
    except socket.gaierror as e:
        print(f"getaddrinfo error: {e}", file = sys.stderr)
        return None

def send_line(fd: socket.socket, fmt, *args) -> None:
    buf: str = fmt % args + '\n'
    fd.send(buf.encode())

def read_line(fd: socket.socket) -> str | None:
    buf: bytes = b''
    while True:
        data: bytes = fd.recv(1)
        if not data:
            return None
        if data == b'\n':
            return buf.decode().rstrip('\n')
        buf += data

def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <host> <port>", file = sys.stderr)
        return 1
    
    # Connexion au serveur
    fd: socket.socket | None = connect_to(sys.argv[1], sys.argv[2])
    if not fd:
        return 1
    
    print(f"Connected to {sys.argv[1]}:{sys.argv[2]}")
    
    # Lecture du message de bienvenue
    welcome: str | None = read_line(fd)
    if welcome:
        print(welcome)

    # Demande du pseudo
    pseudo: str = input("Enter a username: ").strip()
    if len(pseudo) >= MAX_PSEUDO:
        pseudo = pseudo[:MAX_PSEUDO-1]
    
    # Envoi de l'authentification
    send_line(fd, "HELLO %s", pseudo)

    
    # Boucle principale
    while True:
        readable, _, _ = select.select([sys.stdin, fd], [], [])
        
        # Entrée utilisateur
        if sys.stdin in readable:
            try:
                line: str = input()
                if line:
                    send_line(fd, "%s", line)
            except EOFError:
                break
        
        # Message du serveur
        if fd in readable:
            msg: str | None = read_line(fd)
            if msg is None:
                print("503: Server unavailable.")
                break
            print(msg)
    
    fd.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
