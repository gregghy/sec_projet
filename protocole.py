#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#MAX_PLAYERS = 4
#MAX_BOATS   = 3
#MAX_LINE    = 256
#
#def send_line(sock, msg, *args):
#    """
#    Envoie une ligne terminée par '\n' au socket.
#    Le formatage se fait à la manière de printf.
#    """
#    line = (msg % args if args else msg) + '\n'
#    sock.sendall(line.encode())
#
#def read_line(sock):
#    """
#    Lit un caractère à la fois jusqu'à '\n' ou fin de flux.
#    Retourne la chaîne lue (sans le '\n') ou None si déconnexion.
#    """
#    data = bytearray()
#    while True:
#        b = sock.recv(1)
#        if not b:
#            return None
#        if b == b'\n' or len(data) >= MAX_LINE:
#            break
#        data += b
#    return data.decode()
#