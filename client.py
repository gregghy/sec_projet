#!/usr/bin/env python3
import socket
import sys
import select

MAX_PSEUDO = 16
MAX_LINE = 256

def connect_to(host, port):
    try:
        addrinfo = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, socktype, proto, canonname, sockaddr in addrinfo:
            try:
                fd = socket.socket(family, socktype, proto)
                fd.connect(sockaddr)
                return fd
            except socket.error:
                if fd:
                    fd.close()
                continue
        raise socket.error("Unable to connect")
    except socket.gaierror as e:
        print(f"getaddrinfo error: {e}", file=sys.stderr)
        return None

def send_line(fd, fmt, *args):
    buf = fmt % args + '\n'
    fd.send(buf.encode())

def read_line(fd):
    buf = b''
    while True:
        data = fd.recv(1)
        if not data:
            return None
        if data == b'\n':
            return buf.decode().rstrip('\n')
        buf += data

def main():
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <host> <port>", file=sys.stderr)
        return 1
    
    # Connexion au serveur
    fd = connect_to(sys.argv[1], sys.argv[2])
    if not fd:
        return 1
    
    print(f"Connecté à {sys.argv[1]}:{sys.argv[2]}")
    
    # Lecture du message de bienvenue
    welcome = read_line(fd)
    if welcome:
        print(welcome)

    # Demande du pseudo
    pseudo = input("Entrez un pseudo : ").strip()
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
                line = input()
                if line:
                    send_line(fd, "%s", line)
            except EOFError:
                break
        
        # Message du serveur
        if fd in readable:
            msg = read_line(fd)
            if msg is None:
                print("Serveur déconnecté")
                break
            print(msg)
    
    fd.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())