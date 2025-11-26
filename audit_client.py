#!/usr/bin/env python3
import socket
import sys
import time

def spam_server(host, port):
    while True:
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, int(port)))
            s.setblocking(False)

            # Authentification
            pseudo = "audit_client"
            print(f"Connexion en tant que {pseudo}...")
            
            try:
                s.sendall(f"HELLO {pseudo} password123\n".encode())
            except BlockingIOError:
                pass
                
            time.sleep(0.5)

            print("Spamming SPEAK ERROR...")
            i = 0
            while True:
                # vider le buffer pour éviter que le serveur ne bloque/déconnecte
                try:
                    while True:
                        data = s.recv(4096)
                        if not data: break
                except BlockingIOError:
                    pass
                except Exception:
                    pass

                # Envoyer le spam
                if i % 2 == 0:
                    msg = f"CREAT {i} {i} {i} 5\n"
                else:
                    msg = f"BID {i-1}\n"


                try:
                    s.sendall(msg.encode())
                    i += 1
                    if i % 1000 == 0:
                        print(f"Spammed {i} messages")
                except BlockingIOError:
                    # Buffer plein, on attend un peu
                    time.sleep(0.01)
                    continue 

        except KeyboardInterrupt:
            print("Stop!")
            if s: s.close()
            return
        except Exception as e:
            print(f"Erreur: {e}. Reconnexion dans 1s...")
            if s: s.close()
            time.sleep(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <host> <port>")
        sys.exit(1)
    
    spam_server(sys.argv[1], sys.argv[2])