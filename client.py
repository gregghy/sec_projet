#!/usr/bin/env python3
import socket
import sys
import select
import RSA
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes # AES
import time
import signal
from os import urandom

if sys.platform == "linux":
    # Ignore Ctrl+C (SIGINT) and Ctrl+Z (SIGTSTP)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTSTP, signal.SIG_IGN)

if sys.platform == "win32":
    signal.signal(signal.CTRL_BREAK_EVENT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.signal(signal.CTRL_C_EVENT, signal.SIG_IGN)

MAX_PSEUDO: int = 16
MAX_LINE: int = 256

RSA_KEY_SIZE: int = 256

AES_KEY_SIZE: int = 32
AES_IV_SIZE: int = 16
AES_BLOCK_SIZE: int = 64


AES_KEY: bytes = urandom(AES_KEY_SIZE)
AES_IV: bytes = urandom(AES_IV_SIZE)

AES: Cipher = Cipher(
    algorithm = algorithms.AES(AES_KEY),
    mode = modes.CBC(AES_IV),
    backend = default_backend()
)
encryptor = AES.encryptor()
decryptor = AES.decryptor()
padder = padding.PKCS7(AES_BLOCK_SIZE).padder()
unpadder = padding.PKCS7(AES_BLOCK_SIZE).unpadder()

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

def send_line(fd: socket.socket, fmt: str, *args) -> None:
    buf: str = fmt % args
    if buf[:-1] != '\n':
        buf = buf + '\n'
    fd.send(buf.encode())

def send_line_aes(fd: socket.socket, fmt: str, *args) -> None:
    buf: str = fmt % args + '\n'
    padded = padder.update(bytes(buf, encoding = "utf-8")) + padder.finalize()
    enc: bytes = encryptor.update(padded) + encryptor.finalize()
    return send_line(fd, "%s", enc)

def read_line(fd: socket.socket) -> str | None:
    buf: bytes = b''
    while True:
        data: bytes = fd.recv(1)
        
        if not data:
            return None
        if data == b'\n':
            return buf.decode().rstrip('\n')
        
        buf += data

def read_line_aes(fd: socket.socket) -> str | None:
    dec: bytes = b''
    while True:
        data: bytes = fd.recv(1)
        padded = decryptor.update(data) + decryptor.finalize()
        decrypted = unpadder.update(padded) + unpadder.finalize()

        if not data:
            return None
        if data == b'\n':
            return dec.decode().rstrip('\n')
        
        dec += decrypted

def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <host> <port>", file = sys.stderr)
        return 1
    
    # Connexion au serveur
    fd: socket.socket | None = connect_to(sys.argv[1], sys.argv[2])
    if not fd:
        return 1
    
    rsakeys: RSA.RSA = RSA.RSA(RSA_KEY_SIZE)
    
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
    # Envoi d'un PING initial pour vérifier la connexion
    try:
        ts0 = str(int(time.time()))
        send_line(fd, "PING %s", ts0)
    except OSError:
        print("503: Failed to send initial PING.")
        fd.close()
        return 1

    
    # Boucle principale
    last_ping: float = time.time()
    PING_INTERVAL: float = 30.0  # secondes
    while True:
        # timeout dynamique pour envoyer des PING périodiques
        now = time.time()
        timeout = max(0.0, last_ping + PING_INTERVAL - now)
        readable, _, _ = select.select([sys.stdin, fd], [], [], timeout)
        
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

            if msg.startswith("RSAKEY"):
                serv_RSA_str: list[str] = msg[len("RSAKEY "):].split()
                serv_RSA: tuple[int, int] = (int(serv_RSA_str[0]), int(serv_RSA_str[1]))
                send_line(
                    fd, 
                    "%s",
                    "AESKEY "
                    + str(rsakeys.getPublicKey()[0]) + " "
                    + str(rsakeys.getPublicKey()[1]) + " "
                    + str(
                        rsakeys.enc(
                            serv_RSA,
                            str(AES_KEY) + " "
                            + str(AES_IV)
                        )
                    )
                )

            print(msg)

        # Envoi périodique du keep-alive PING <ts>
        now = time.time()
        if now - last_ping >= PING_INTERVAL:
            ts = str(int(now))
            try:
                send_line(fd, "PING %s", ts)
                last_ping = now
            except OSError:
                print("503: Failed to send PING.")
                break
    
    fd.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
