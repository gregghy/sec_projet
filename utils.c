#include "protocole.h"
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int send_line(int fd, const char *fmt, ...) {
    char buf[MAX_LINE];
    va_list ap;
    va_start(ap, fmt);
      // vsnprintf formate la chaine selon fmt et args
    int n = vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    if (n < 0) 
        return -1;
    if (n >= (int)sizeof(buf)) // sizeof mis en int pour la comparaison avec n
        n = sizeof(buf) - 1;
    buf[n++] = '\n';// ajoute retour à la ligne
    return (write(fd, buf, n) == n) ? 0 : -1;
}

int read_line(int fd, char *buf, size_t len) {
    size_t i = 0;
    while (i + 1 < len) { 
        char c;
        ssize_t r = read(fd, &c, 1);
        // si read erreur ou vide on le return 
        if (r <= 0) 
            return (int)r; 
        if (c == '\n') 
            break;
        buf[i++] = c;
    }
    buf[i] = '\0';
    // returne le nombre de caractères lus
    return (int)i; 
}